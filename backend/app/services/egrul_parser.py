"""Парсинг ответа ЕГРЮЛ API в структурированные данные."""
from dataclasses import dataclass
from decimal import Decimal

from num2words import num2words


@dataclass
class AddressData:
    index: str
    region: str
    street: str
    building: str


@dataclass
class DirectorData:
    full_name: str
    role_label: str


@dataclass
class FounderData:
    name: str
    nominal_value: Decimal
    share_percent: str


@dataclass
class OrganizationData:
    inn: str
    ogrn: str
    kpp: str
    full_name: str
    short_name: str
    registration_date: str
    authorized_capital: str
    address: AddressData
    director: DirectorData | None
    founders: list[FounderData]
    okved_main: str
    okved_list: list[str]


_ROLE_MAP: dict[str, str] = {
    "ликвидатор": "Ликвидатор общества",
    "генеральный": "Генеральный директор общества",
    "генеральный директор": "Генеральный директор общества",
    "директор": "Генеральный директор общества",
}


def _get_attrs(node: dict) -> dict:
    return node.get("@attributes", {}) if isinstance(node, dict) else {}


def _parse_address(sv_yu_l: dict) -> AddressData:
    addr_node = sv_yu_l.get("СвАдресЮЛ", {})
    fias = addr_node.get("СвАдрЮЛФИАС", {})
    rf = addr_node.get("АдресРФ", {})

    index = _get_attrs(fias).get("Индекс") or _get_attrs(rf).get("Индекс", "")
    region = fias.get("НаимРегион") or ""

    street_node = fias.get("ЭлУлДорСети", {})
    street_attrs = _get_attrs(street_node)
    street_type = street_attrs.get("Тип", "")
    street_name = street_attrs.get("Наим", "")
    street = f"{street_type} {street_name}".strip() if street_name else ""

    buildings_raw = fias.get("Здание", [])
    if isinstance(buildings_raw, dict):
        buildings_raw = [buildings_raw]
    parts = [
        f"{_get_attrs(b).get('Тип', '')} {_get_attrs(b).get('Номер', '')}".strip()
        for b in buildings_raw
        if _get_attrs(b).get("Номер")
    ]
    building = ", ".join(parts)

    return AddressData(index=index, region=region, street=street, building=building)


def _parse_director(sv_yu_l: dict) -> DirectorData | None:
    node = sv_yu_l.get("СведДолжнФЛ")
    if not node:
        return None

    должн_attrs = _get_attrs(node.get("СвДолжн", {}))
    raw_role = должн_attrs.get("НаимДолжн", "").lower()
    role_label = _ROLE_MAP.get(raw_role, должн_attrs.get("НаимДолжн", ""))

    fl_attrs = _get_attrs(node.get("СвФЛ", {}))
    parts = [
        fl_attrs.get("Фамилия", ""),
        fl_attrs.get("Имя", ""),
        fl_attrs.get("Отчество", ""),
    ]
    full_name = " ".join(p for p in parts if p)

    return DirectorData(full_name=full_name, role_label=role_label)


def _parse_capital(sv_yu_l: dict) -> str:
    cap_node = sv_yu_l.get("СвУстКап", {})
    raw = _get_attrs(cap_node).get("СумКап", "0")
    try:
        amount = Decimal(raw)
    except Exception:
        return raw

    amount_int = int(amount)
    words = num2words(amount_int, lang="ru")
    return f"{amount_int:,} ({words}) рублей.".replace(",", " ")


def _parse_founders(sv_yu_l: dict) -> list[FounderData]:
    учредит = sv_yu_l.get("СвУчредит", {})
    founders: list[FounderData] = []

    # Физические лица
    fl_raw = учредит.get("УчрФЛ", [])
    if isinstance(fl_raw, dict):
        fl_raw = [fl_raw]
    for fl in fl_raw:
        fl_attrs = _get_attrs(fl.get("СвФЛ", {}))
        parts = [
            fl_attrs.get("Фамилия", ""),
            fl_attrs.get("Имя", ""),
            fl_attrs.get("Отчество", ""),
        ]
        name = " ".join(p for p in parts if p)
        founders.append(_extract_founder(name, fl))

    # Юридические лица
    ul_raw = учредит.get("УчрЮЛ", [])
    if isinstance(ul_raw, dict):
        ul_raw = [ul_raw]
    for ul in ul_raw:
        ul_attrs = _get_attrs(ul.get("СвОрг", {}))
        name = ul_attrs.get("НаимЮЛПолн", ul_attrs.get("НаимЮЛСокр", ""))
        founders.append(_extract_founder(name, ul))

    return founders


def _extract_founder(name: str, node: dict) -> FounderData:
    доля = node.get("ДоляУстКап", {})
    доля_attrs = _get_attrs(доля)
    nominal_raw = доля_attrs.get("НоминСтоим", "0")
    try:
        nominal = Decimal(nominal_raw)
    except Exception:
        nominal = Decimal(0)

    размер = доля.get("РазмерДоли", {})
    percent = размер.get("Процент", "0") if isinstance(размер, dict) else "0"

    return FounderData(name=name, nominal_value=nominal, share_percent=str(percent))


def _parse_okved(sv_yu_l: dict) -> tuple[str, list[str]]:
    okved_node = sv_yu_l.get("СвОКВЭД", {})

    main_node = okved_node.get("СвОКВЭДОсн", {})
    main_attrs = _get_attrs(main_node)
    main_code = main_attrs.get("КодОКВЭД", "")
    main_name = main_attrs.get("НаимОКВЭД", "")
    okved_main = f"{main_code} - {main_name}" if main_code else ""

    extra_raw = okved_node.get("СвОКВЭДДоп", [])
    if isinstance(extra_raw, dict):
        extra_raw = [extra_raw]

    all_okved: list[str] = []
    if okved_main:
        all_okved.append(okved_main)
    for act in extra_raw:
        attrs = _get_attrs(act)
        code = attrs.get("КодОКВЭД", "")
        name = attrs.get("НаимОКВЭД", "")
        if code:
            all_okved.append(f"{code} - {name}")

    return okved_main, all_okved


def parse_egrul_response(data: dict) -> OrganizationData:
    sv_yu_l = data.get("СвЮЛ", {})
    attrs = _get_attrs(sv_yu_l)

    inn = attrs.get("ИНН", "")
    ogrn = attrs.get("ОГРН", "")
    kpp = attrs.get("КПП", "")
    reg_date = attrs.get("ДатаОГРН", "")

    наим = sv_yu_l.get("СвНаимЮЛ", {})
    full_name = _get_attrs(наим).get("НаимЮЛПолн", "")
    short_name = _get_attrs(наим.get("СвНаимЮЛСокр", {})).get("НаимСокр", full_name)

    address = _parse_address(sv_yu_l)
    director = _parse_director(sv_yu_l)
    capital = _parse_capital(sv_yu_l)
    founders = _parse_founders(sv_yu_l)
    okved_main, okved_list = _parse_okved(sv_yu_l)

    return OrganizationData(
        inn=inn,
        ogrn=ogrn,
        kpp=kpp,
        full_name=full_name,
        short_name=short_name,
        registration_date=reg_date,
        authorized_capital=capital,
        address=address,
        director=director,
        founders=founders,
        okved_main=okved_main,
        okved_list=okved_list,
    )
