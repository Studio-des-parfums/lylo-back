from sqlalchemy import Boolean, Column, Date, DateTime, Integer, String, JSON
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
    input_mode = Column(String(20), nullable=True)
    participant_color = Column(String(30), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
