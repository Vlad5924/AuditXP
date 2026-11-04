"""ORM-модели AuditXP (физическая модель данных ЛР7)."""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    DDL,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    event,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, JsonType, utcnow
from app.domain.enums import ImportStatus, ReportStatus, RiskLevel, RiskStatus
from app.domain.risk_matrix import level_for_score, materiality


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    permissions: Mapped[list] = mapped_column(JsonType, default=list)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    role_id: Mapped[int] = mapped_column(
        ForeignKey("roles.id", ondelete="RESTRICT"))
    login: Mapped[str] = mapped_column(String(50), unique=True)
    full_name: Mapped[str] = mapped_column(String(150))
    email: Mapped[str] = mapped_column(String(150), unique=True)
    password_hash: Mapped[str] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False)
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0)
    reset_token_hash: Mapped[str | None] = mapped_column(String(64))
    reset_token_expires: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime)

    role: Mapped[Role] = relationship(lazy="joined")

    @property
    def role_name(self) -> str:
        return self.role.name if self.role else ""


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    manager_name: Mapped[str | None] = mapped_column(String(150))


class ImportBatch(Base):
    """Запись журнала импорта (один запуск ETL)."""

    __tablename__ = "import_batches"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    source: Mapped[str] = mapped_column(String(30), default="erp")
    period_from: Mapped[date | None] = mapped_column(Date)
    period_to: Mapped[date | None] = mapped_column(Date)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(30),
                                        default=ImportStatus.RUNNING)
    rows_total: Mapped[int] = mapped_column(Integer, default=0)
    rows_loaded: Mapped[int] = mapped_column(Integer, default=0)
    rows_quarantined: Mapped[int] = mapped_column(Integer, default=0)
    duplicates: Mapped[int] = mapped_column(Integer, default=0)
    skipped_existing: Mapped[int] = mapped_column(Integer, default=0)
    message: Mapped[str | None] = mapped_column(Text)

    user: Mapped["User | None"] = relationship(lazy="joined")


class ErpTransaction(Base):
    __tablename__ = "erp_transactions"
    __table_args__ = (
        Index("ix_txn_dept_date", "department_id", "transaction_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    doc_number: Mapped[str] = mapped_column(String(50), unique=True)
    department_id: Mapped[int] = mapped_column(
        ForeignKey("departments.id"))
    transaction_date: Mapped[datetime] = mapped_column(DateTime,
                                                       index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    counterparty_info: Mapped[str] = mapped_column(String(255))
    account_debit: Mapped[str | None] = mapped_column(String(10))
    account_credit: Mapped[str | None] = mapped_column(String(10))
    batch_id: Mapped[int | None] = mapped_column(
        ForeignKey("import_batches.id"))
    imported_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    department: Mapped[Department] = relationship(lazy="joined")


class QuarantineRecord(Base):
    """Отбракованная при очистке запись ERP (FR-2.2)."""

    __tablename__ = "quarantine_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    batch_id: Mapped[int] = mapped_column(
        ForeignKey("import_batches.id", ondelete="CASCADE"), index=True)
    doc_number: Mapped[str | None] = mapped_column(String(50))
    reason: Mapped[str] = mapped_column(String(255))
    payload: Mapped[dict] = mapped_column(JsonType, default=dict)


class AuditReport(Base):
    __tablename__ = "audit_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    period_from: Mapped[date] = mapped_column(Date)
    period_to: Mapped[date] = mapped_column(Date)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(30),
                                        default=ReportStatus.DRAFT)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime)
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime)
    review_comment: Mapped[str | None] = mapped_column(Text)
    signature: Mapped[str | None] = mapped_column(String(64))
    summary: Mapped[dict] = mapped_column(JsonType, default=dict)

    author: Mapped[User] = relationship(foreign_keys=[user_id],
                                        lazy="joined")
    approver: Mapped["User | None"] = relationship(
        foreign_keys=[approved_by], lazy="joined")


class Risk(Base):
    __tablename__ = "risks"
    __table_args__ = (
        CheckConstraint("probability >= 0 AND probability <= 1",
                        name="ck_risks_probability"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    report_id: Mapped[int | None] = mapped_column(
        ForeignKey("audit_reports.id", ondelete="SET NULL"))
    transaction_id: Mapped[int] = mapped_column(
        ForeignKey("erp_transactions.id", ondelete="CASCADE"),
        unique=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    risk_type: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text, default="")
    method: Mapped[str] = mapped_column(String(50))
    anomaly_score: Mapped[Decimal] = mapped_column(Numeric(4, 3))
    probability: Mapped[Decimal] = mapped_column(Numeric(3, 2))
    impact: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    materiality: Mapped[int] = mapped_column(Integer, default=1)
    level: Mapped[str] = mapped_column(String(20), default=RiskLevel.LOW,
                                       index=True)
    status: Mapped[str] = mapped_column(String(30),
                                        default=RiskStatus.IDENTIFIED,
                                        index=True)
    comment: Mapped[str | None] = mapped_column(Text)
    mitigation_plan: Mapped[str | None] = mapped_column(Text)
    mitigation_owner: Mapped[str | None] = mapped_column(String(150))
    mitigation_due: Mapped[date | None] = mapped_column(Date)
    effectiveness_confirmed: Mapped[bool] = mapped_column(Boolean,
                                                          default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow,
                                                 onupdate=utcnow)
    escalated_at: Mapped[datetime | None] = mapped_column(DateTime)

    transaction: Mapped[ErpTransaction] = relationship(lazy="joined")

    @property
    def code(self) -> str:
        return f"RK-{1000 + (self.id or 0)}"

    def calculate_level(self) -> RiskLevel:
        """Пересчитывает существенность и уровень риска (BR-5)."""
        self.materiality = materiality(float(self.probability),
                                       float(self.impact))
        self.level = level_for_score(self.materiality)
        return RiskLevel(self.level)


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True)
    message: Mapped[str] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AuditLog(Base):
    """Журнал аудита, доступный только для добавления (AUD-02)."""

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    table_name: Mapped[str] = mapped_column(String(50))
    action: Mapped[str] = mapped_column(String(50))
    record_id: Mapped[int | None] = mapped_column(Integer)
    details: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow,
                                                 index=True)

    user: Mapped["User | None"] = relationship(lazy="joined")


_SQLITE_GUARDS = (
    "CREATE TRIGGER trg_audit_log_no_update BEFORE UPDATE ON audit_log "
    "BEGIN SELECT RAISE(ABORT, 'audit_log is append-only'); END",
    "CREATE TRIGGER trg_audit_log_no_delete BEFORE DELETE ON audit_log "
    "BEGIN SELECT RAISE(ABORT, 'audit_log is append-only'); END",
)
_PG_GUARDS = (
    "CREATE OR REPLACE FUNCTION audit_log_protect() RETURNS trigger AS $$ "
    "BEGIN RAISE EXCEPTION 'audit_log is append-only (AUD-02)'; END; $$ "
    "LANGUAGE plpgsql",
    "CREATE TRIGGER trg_audit_log_protect BEFORE UPDATE OR DELETE "
    "ON audit_log FOR EACH ROW EXECUTE FUNCTION audit_log_protect()",
)
for _sql in _SQLITE_GUARDS:
    event.listen(AuditLog.__table__, "after_create",
                 DDL(_sql).execute_if(dialect="sqlite"))
for _sql in _PG_GUARDS:
    event.listen(AuditLog.__table__, "after_create",
                 DDL(_sql).execute_if(dialect="postgresql"))
