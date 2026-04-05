"""Генерация .docx документа из данных организации."""
import io
from pathlib import Path

from docxtpl import DocxTemplate

from app.services.egrul_parser import OrganizationData

TEMPLATE_PATH = Path(__file__).parent.parent.parent / "templates" / "template_explanatory_note.docx"


def _build_context(org: OrganizationData) -> dict:
    # Адрес: индекс, регион, улица, здание
    addr = org.address
    address_parts = [p for p in [addr.index, addr.region, addr.street, addr.building] if p]
    legal_address = ", ".join(address_parts)

    # Руководитель
    if org.director:
        ceos = [f"{org.director.role_label}: {org.director.full_name}".title()]
        if org.director.role_label == "Генеральный директор общества":
            ceos.append(f"Главный бухгалтер общества: {org.director.full_name}".title())
    else:
        ceos = []



    # Учредители: "ФИО / Наим — X% (номинал руб.)"
    participants_lines = []
    for f in org.founders:
        line = f"{f.name} — {f.share_percent}% (номинальная стоимость: {f.nominal_value:,} руб.)".replace(",", " ")
        participants_lines.append(line)

    return {
        "full_company_name": org.full_name,
        "short_company_name": org.short_name,
        "legal_address": legal_address,
        "ceos": ceos,
        "charter_capital": org.authorized_capital,
        "participants": participants_lines,
        "registration_date": org.registration_date,
        "activities_list": org.okved_list,
        # поля персонала — пустые, заполняются вручную
        "staff_administration": "",
        "staff_logistics": "",
        "staff_production": "",
    }


def generate_docx(org: OrganizationData) -> io.BytesIO:
    tpl = DocxTemplate(TEMPLATE_PATH)
    context = _build_context(org)
    tpl.render(context)

    buffer = io.BytesIO()
    tpl.save(buffer)
    buffer.seek(0)
    return buffer
