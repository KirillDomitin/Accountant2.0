import re

from pydantic import BaseModel, field_validator


class InnLookupRequest(BaseModel):
    inn: str

    @field_validator("inn")
    @classmethod
    def validate_inn(cls, v: str) -> str:
        v = v.strip()
        if not re.fullmatch(r"\d{10}|\d{12}", v):
            raise ValueError("ИНН должен содержать 10 (ЮЛ) или 12 (ИП) цифр")
        return v
