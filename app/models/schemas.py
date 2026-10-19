from datetime import date as date_type
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.core.languages import SupportedLanguage


class StartSessionRequest(BaseModel):
    language: SupportedLanguage = "fr"
    voice_gender: Literal["female", "male"] = "female"
    question_count: int = Field(default=1, ge=1, le=12)
    mode: Literal["guided", "discovery"] = "guided"
    input_mode: Literal["voice", "click"] = "voice"
    brand: Literal["lylo", "ester"] = "lylo"
    email: str | None = None
    owner_email: str | None = None
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
    field: Literal["first_name", "last_name", "email", "phone", "gender", "age", "has_disliked_notes", "disliked_notes", "has_allergies", "allergies", "perfume_name"]
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
    language: SupportedLanguage = "fr"
    brand: Literal["lylo", "ester"] = "lylo"
    gender: str
    age: str
    has_disliked_notes: Literal["oui", "non"] = "non"
    disliked_notes: str | None = None
    has_allergies: Literal["oui", "non"] = "non"
    allergies: str | None = None
    answers: list[BatchAnswerItem]
    formula_type: Literal["frais", "mix", "puissant"] | None = None
    perfume_name: str | None = None


class SendFormulaMailRequest(BaseModel):
    email: str
    language: SupportedLanguage = "fr"
    formula: dict


class SendFormulaByReferenceRequest(BaseModel):
    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None


class SaveFormulaRequest(BaseModel):
    formula: dict
    customer_name: str | None = None
    customer_email: str | None = None
    participant_id: int | None = None
    language: SupportedLanguage = "fr"


class StartMoodboardsRequest(BaseModel):
    formulas: list[dict]
    language: SupportedLanguage = "fr"


class ReplaceNoteStatelessRequest(BaseModel):
    formula: dict
    note_type: Literal["top", "heart", "base"]
    old_note: str
    new_note: str
    language: SupportedLanguage = "fr"
    # Référence déjà sauvegardée en base pour cette formule (si l'utilisateur a déjà
    # choisi une carte) — permet de répercuter la note modifiée sur l'enregistrement
    # existant plutôt que de le laisser périmé.
    reference: str | None = None


class SimilarPerfumesRequest(BaseModel):
    formula: dict
    language: SupportedLanguage = "fr"


class MultiParticipant(BaseModel):
    color: str
    gender: str
    age: str
    has_disliked_notes: Literal["oui", "non"] = "non"
    disliked_notes: str | None = None
    has_allergies: Literal["oui", "non"] = "non"
    allergies: str | None = None
    pregnant: bool = False
    answers: list[BatchAnswerItem]
    formula_type: Literal["frais", "mix", "puissant"] | None = None
    perfume_name: str | None = None


class MultiGenerateRequest(BaseModel):
    language: SupportedLanguage = "fr"
    brand: Literal["lylo", "ester"] = "lylo"
    participants: list[MultiParticipant]


class MultiFormulaSelection(BaseModel):
    color: str
    formula: dict
    customer_name: str | None = None
    customer_email: str | None = None
    participant_id: int | None = None


class SaveMultiFormulaRequest(BaseModel):
    language: SupportedLanguage = "fr"
    input_mode: str = "quiz"
    selections: list[MultiFormulaSelection]


class PrintMultiFormulaRequest(BaseModel):
    location: str
    formulas: list[dict]


# --- Analytics Schemas ---

class CountPeriodItem(BaseModel):
    period: str
    count: int


class FormulaCountResponse(BaseModel):
    total: int
    group_by: str
    date_from: date_type | None = None
    date_to: date_type | None = None
    data: list[CountPeriodItem]


class TopNoteItem(BaseModel):
    note: str
    category: str | None = None
    count: int
    percentage: float


class TopNotesResponse(BaseModel):
    total_formulas: int
    category: str
    limit: int
    data: list[TopNoteItem]


class ProfileStatItem(BaseModel):
    profile: str
    count: int
    percentage: float


class ProfilesResponse(BaseModel):
    total: int
    data: list[ProfileStatItem]


class LanguageStatItem(BaseModel):
    language: str
    count: int
    percentage: float


class LanguagesResponse(BaseModel):
    total: int
    data: list[LanguageStatItem]


class ModeStatItem(BaseModel):
    mode: str
    count: int
    percentage: float


class ModesResponse(BaseModel):
    total: int
    data: list[ModeStatItem]


class FormulaTypeStatItem(BaseModel):
    formula_type: str
    count: int
    percentage: float


class FormulaTypesResponse(BaseModel):
    total: int
    data: list[FormulaTypeStatItem]


class AnalyticsSummaryResponse(BaseModel):
    total_formulas: int
    profiles: list[ProfileStatItem]
    modes: list[ModeStatItem]
    top_notes: list[TopNoteItem]
    formula_types: list[FormulaTypeStatItem]
    languages: list[LanguageStatItem] | None = None

