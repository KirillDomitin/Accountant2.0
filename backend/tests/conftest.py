"""Общие фикстуры для тестов."""
import pytest


def make_raw_egrul(
    inn: str = "7701234567",
    full_name: str = "ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ «ТЕСТ»",
    short_name: str = "ООО «ТЕСТ»",
    ogrn: str = "1027700000001",
    kpp: str = "770101001",
    reg_date: str = "01.01.2010",
    director_name: str = "ИВАНОВ ИВАН ИВАНОВИЧ",
    director_role: str = "Генеральный директор",
    capital: str = "10000",
    region: str = "г Москва",
    street: str = "ул Тверская",
    building: str = "1",
    index: str = "125009",
    founder_name: str = "ИВАНОВ ИВАН ИВАНОВИЧ",
    founder_nominal: str = "10000",
    founder_percent: str = "100",
    okved_main_code: str = "62.01",
    okved_main_name: str = "Разработка компьютерного программного обеспечения",
) -> dict:
    """Строит минимальный словарь в формате ЕГРЮЛ API."""
    return {
        "СвЮЛ": {
            "@attributes": {
                "ИНН": inn,
                "ОГРН": ogrn,
                "КПП": kpp,
                "ДатаОГРН": reg_date,
            },
            "СвНаимЮЛ": {
                "@attributes": {"НаимЮЛПолн": full_name},
                "СвНаимЮЛСокр": {"@attributes": {"НаимСокр": short_name}},
            },
            "СвАдресЮЛ": {
                "СвАдрЮЛФИАС": {
                    "@attributes": {"Индекс": index},
                    "НаимРегион": region,
                    "ЭлУлДорСети": {"@attributes": {"Тип": "ул", "Наим": street.replace("ул ", "")}},
                    "Здание": {"@attributes": {"Тип": "д", "Номер": building}},
                }
            },
            "СведДолжнФЛ": {
                "СвДолжн": {"@attributes": {"НаимДолжн": director_role}},
                "СвФЛ": {
                    "@attributes": {
                        "Фамилия": director_name.split()[0],
                        "Имя": director_name.split()[1],
                        "Отчество": director_name.split()[2] if len(director_name.split()) > 2 else "",
                    }
                },
            },
            "СвУстКап": {"@attributes": {"СумКап": capital}},
            "СвУчредит": {
                "УчрФЛ": {
                    "СвФЛ": {
                        "@attributes": {
                            "Фамилия": founder_name.split()[0],
                            "Имя": founder_name.split()[1],
                            "Отчество": founder_name.split()[2] if len(founder_name.split()) > 2 else "",
                        }
                    },
                    "ДоляУстКап": {
                        "@attributes": {"НоминСтоим": founder_nominal},
                        "РазмерДоли": {"Процент": founder_percent},
                    },
                }
            },
            "СвОКВЭД": {
                "СвОКВЭДОсн": {
                    "@attributes": {"КодОКВЭД": okved_main_code, "НаимОКВЭД": okved_main_name}
                }
            },
        }
    }
