from typing import Any, Literal

from pydantic import BaseModel, Field


class StartSessionRequest(BaseModel):
    language: Literal["fr", "en"] = "fr"
    voice_gender: Literal["female", "male"] = "female"
    question_count: int = Field(default=1, ge=1, le=12)
    mode: Literal["guided", "discovery"] = "guided"
    input_mode: Literal["voice", "click"] = "voice"
    email: str | None = None
    avatar: bool = True


class StartSessionResponse(BaseModel):
    session_id: str
    room_name: str
    token: str
    livekit_url: str
    identity: str


class SaveAnswerRequest(BaseModel):
    question_id: int
    question_text: str
    top_2: list[str]
    bottom_2: list[str]


class SaveProfileRequest(BaseModel):
    field: Literal["first_name", "gender", "age", "has_allergies", "allergies"]
    value: str


class GenerateFormulasRequest(BaseModel):
    formula_type: Literal["frais", "mix", "puissant"] | None = None


class SelectFormulaRequest(BaseModel):
    formula_index: int  # 0 ou 1


class ChangeFormulaTypeRequest(BaseModel):
    formula_type: Literal["frais", "mix", "puissant"]


class ReplaceNoteRequest(BaseModel):
    note_type: Literal["top", "heart", "base"]
    old_note: str
    new_note: str


class SendMailRequest(BaseModel):
    to: str


class BatchAnswerItem(BaseModel):
    question_id: int
    question_text: str
    top_2: list[str]
    bottom_2: list[str]


class BatchGenerateRequest(BaseModel):
    language: Literal["fr", "en"] = "fr"
    gender: str
    age: str
    has_allergies: Literal["oui", "non"] = "non"
    allergies: str | None = None
    answers: list[BatchAnswerItem]


class SendFormulaMailRequest(BaseModel):
    email: str
    language: Literal["fr", "en"] = "fr"
    formula: dict


class SaveFormulaRequest(BaseModel):
    formula: dict
    customer_name: str | None = None
    customer_email: str | None = None
    language: Literal["fr", "en"] = "fr"


class MultiParticipant(BaseModel):
    color: str
    gender: str
    age: str
    has_allergies: Literal["oui", "non"] = "non"
    allergies: str | None = None
    pregnant: bool = False
    answers: list[BatchAnswerItem]


class MultiGenerateRequest(BaseModel):
    language: Literal["fr", "en"] = "fr"
    participants: list[MultiParticipant]


class MultiFormulaSelection(BaseModel):
    color: str
    formula: dict
    customer_name: str | None = None
    customer_email: str | None = None


class SaveMultiFormulaRequest(BaseModel):
    language: Literal["fr", "en"] = "fr"
    input_mode: str = "quiz"
    selections: list[MultiFormulaSelection]


class PrintMultiFormulaRequest(BaseModel):
    location: str
    formulas: list[dict]
