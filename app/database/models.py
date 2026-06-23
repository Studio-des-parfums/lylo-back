from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, String, JSON, Table, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.connection import Base


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(100))
    last_name = Column(String(100))
    email = Column(String(255), unique=True, index=True)
    phone = Column(String(50))
    days_available = Column(String(50), default="0")
    sessions_available = Column(String(50), default="0")
    max_date = Column(Date, nullable=True)


class TeamMember(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(100))
    last_name = Column(String(100))
    email = Column(String(255), unique=True, index=True)
    phone = Column(String(50))


class Participant(Base):
    __tablename__ = "participants"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    email = Column(String(255), unique=True, index=True, nullable=True)
    phone = Column(String(50), nullable=True)
    gender = Column(String(30), nullable=True)
    age = Column(String(30), nullable=True)
    has_allergies = Column(String(10), nullable=True)
    allergies = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Printer(Base):
    __tablename__ = "printers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100))
    location = Column(String(100))
    ip = Column(String(50))
    port = Column(Integer, default=9100)
    protocol = Column(String(20), default="printnode")  # printnode | cups | raw
    cups_name = Column(String(100), nullable=True)
    printnode_id = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)


question_group_links = Table(
    "question_group_links",
    Base.metadata,
    Column("question_id", Integer, ForeignKey("questions.id", ondelete="CASCADE"), primary_key=True),
    Column("group_id", Integer, ForeignKey("question_groups.id", ondelete="CASCADE"), primary_key=True),
    UniqueConstraint("question_id", "group_id", name="uq_question_group_links_question_group"),
)


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    text = Column(Text, nullable=False)
    language = Column(String(10), nullable=False)  # fr, en
    is_active = Column(Boolean, default=True)

    choices = relationship("QuestionChoice", back_populates="question", cascade="all, delete-orphan")
    groups = relationship("QuestionGroup", secondary=question_group_links, back_populates="questions")


class QuestionGroup(Base):
    __tablename__ = "question_groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    is_active = Column(Boolean, default=True)

    questions = relationship("Question", secondary=question_group_links, back_populates="groups")


class QuestionChoice(Base):
    __tablename__ = "question_choices"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False, index=True)
    text = Column(String(255), nullable=False)
    image_url = Column(String(500), nullable=True)
    language = Column(String(10), nullable=False)  # fr, en

    question = relationship("Question", back_populates="choices")


class Ingredient(Base):
    __tablename__ = "ingredients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    type = Column(String(20), nullable=False)       # top, heart, base
    category = Column(String(100), nullable=True)   # adult, enfant, etc.
    language = Column(String(10), nullable=False)   # fr, en
    description = Column(Text, nullable=True)
    intensity = Column(String(20), nullable=True)   # legere, moyenne, forte
    allergens = Column(JSON, nullable=True)         # null = LLM raisonne seul
    is_active = Column(Boolean, default=True)


class GeneratedFormula(Base):
    __tablename__ = "generated_formulas"

    id = Column(Integer, primary_key=True, index=True)
    reference = Column(String(20), unique=True, index=True, nullable=False)
    session_id = Column(String(100), index=True, nullable=False)
    profile = Column(String(100))
    formula_type = Column(String(20))
    top_notes = Column(JSON)
    heart_notes = Column(JSON)
    base_notes = Column(JSON)
    sizes = Column(JSON)
    customer_name = Column(String(200), nullable=True)
    customer_email = Column(String(255), nullable=True)
    language = Column(String(10), nullable=True)
    moodboard_notes_key = Column(String(64), nullable=True, index=True)
    moodboard_image_url = Column(String(500), nullable=True)
    input_mode = Column(String(20), nullable=True)
    participant_color = Column(String(30), nullable=True)
    participant_id = Column(Integer, ForeignKey("participants.id"), nullable=True, index=True)
    owner_type = Column(String(20), nullable=True)
    owner_team_id = Column(Integer, ForeignKey("teams.id"), nullable=True, index=True)
    owner_customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    participant = relationship("Participant")
    owner_team = relationship("TeamMember")
    owner_customer = relationship("Customer")


class FormulaMoodboard(Base):
    __tablename__ = "formula_moodboards"

    id = Column(Integer, primary_key=True, index=True)
    notes_key = Column(String(64), unique=True, index=True, nullable=False)
    top_notes = Column(JSON, nullable=False)
    heart_notes = Column(JSON, nullable=False)
    base_notes = Column(JSON, nullable=False)
    image_url = Column(String(500), nullable=False)
    cloudinary_public_id = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
