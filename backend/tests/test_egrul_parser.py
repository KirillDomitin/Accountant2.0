"""Тесты парсера ЕГРЮЛ (чистые функции, без IO)."""
from decimal import Decimal

import pytest

from app.services.egrul_parser import parse_egrul_response
from tests.conftest import make_raw_egrul


def test_parse_basic_fields():
    raw = make_raw_egrul(inn="7701234567", ogrn="1027700000001", kpp="770101001")
    org = parse_egrul_response(raw)

    assert org.inn == "7701234567"
    assert org.ogrn == "1027700000001"
    assert org.kpp == "770101001"


def test_parse_names():
    raw = make_raw_egrul(
        full_name="ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ «ТЕСТ»",
        short_name="ООО «ТЕСТ»",
    )
    org = parse_egrul_response(raw)

    assert org.full_name == "ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ «ТЕСТ»"
    assert org.short_name == "ООО «ТЕСТ»"


def test_parse_registration_date():
    raw = make_raw_egrul(reg_date="15.03.2015")
    org = parse_egrul_response(raw)

    assert org.registration_date == "15.03.2015"


def test_parse_address():
    raw = make_raw_egrul(index="125009", region="г Москва", street="ул Тверская", building="1")
    org = parse_egrul_response(raw)

    assert org.address.index == "125009"
    assert org.address.region == "г Москва"
    assert "Тверская" in org.address.street
    assert org.address.building != ""


def test_parse_director():
    raw = make_raw_egrul(
        director_name="ИВАНОВ ИВАН ИВАНОВИЧ",
        director_role="Генеральный директор",
    )
    org = parse_egrul_response(raw)

    assert org.director is not None
    assert "ИВАНОВ" in org.director.full_name
    assert org.director.role_label == "Генеральный директор общества"


def test_parse_director_none_when_absent():
    raw = make_raw_egrul()
    # Убираем узел руководителя
    del raw["СвЮЛ"]["СведДолжнФЛ"]
    org = parse_egrul_response(raw)

    assert org.director is None


def test_parse_director_liquidator_role():
    raw = make_raw_egrul(director_role="Ликвидатор")
    org = parse_egrul_response(raw)

    assert org.director.role_label == "Ликвидатор общества"


def test_parse_authorized_capital_format():
    raw = make_raw_egrul(capital="10000")
    org = parse_egrul_response(raw)

    # Должен содержать число и прописью
    assert "10 000" in org.authorized_capital
    assert "рублей" in org.authorized_capital


def test_parse_founders_individual():
    raw = make_raw_egrul(
        founder_name="ПЕТРОВ ПЁТР ПЕТРОВИЧ",
        founder_nominal="10000",
        founder_percent="100",
    )
    org = parse_egrul_response(raw)

    assert len(org.founders) == 1
    assert "ПЕТРОВ" in org.founders[0].name
    assert org.founders[0].nominal_value == Decimal("10000")
    assert org.founders[0].share_percent == "100"


def test_parse_okved():
    raw = make_raw_egrul(
        okved_main_code="62.01",
        okved_main_name="Разработка компьютерного программного обеспечения",
    )
    org = parse_egrul_response(raw)

    assert "62.01" in org.okved_main
    assert len(org.okved_list) >= 1
    assert any("62.01" in item for item in org.okved_list)


def test_parse_okved_with_extra():
    raw = make_raw_egrul(okved_main_code="62.01", okved_main_name="Разработка ПО")
    raw["СвЮЛ"]["СвОКВЭД"]["СвОКВЭДДоп"] = [
        {"@attributes": {"КодОКВЭД": "63.11", "НаимОКВЭД": "Обработка данных"}},
        {"@attributes": {"КодОКВЭД": "70.22", "НаимОКВЭД": "Консультирование"}},
    ]
    org = parse_egrul_response(raw)

    assert len(org.okved_list) == 3
    assert any("63.11" in item for item in org.okved_list)
    assert any("70.22" in item for item in org.okved_list)


def test_parse_empty_response_returns_defaults():
    org = parse_egrul_response({})

    assert org.inn == ""
    assert org.full_name == ""
    assert org.director is None
    assert org.founders == []
    assert org.okved_list == []
