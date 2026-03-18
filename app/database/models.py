from sqlalchemy import Column, Date, Integer, String
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
