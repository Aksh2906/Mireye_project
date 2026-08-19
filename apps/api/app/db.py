from sqlalchemy import JSON, DateTime, String, Text, Uuid, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from app.config import get_settings
from app.domain.models import utcnow


class Base(DeclarativeBase):
    pass


class BuyerProfileRow(Base):
    __tablename__ = "buyer_profiles"
    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True)
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utcnow)


class InvestigationRow(Base):
    __tablename__ = "investigations"
    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    input_type: Mapped[str] = mapped_column(String(32))
    raw_input: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utcnow)


settings = get_settings()
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def initialize_database() -> None:
    Base.metadata.create_all(engine)
