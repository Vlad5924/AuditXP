"""Схемы запросов и ответов REST API (SI-01)."""
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.db.models import AuditReport, Risk, User
from app.domain.risk_matrix import ZONES
from app.domain.state_machine import ACTION_TITLES, available_actions


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


class LoginIn(BaseModel):
    login: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=128)


class EmailIn(BaseModel):
    email: EmailStr


class ResetIn(BaseModel):
    token: str
    new_password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    login: str
    full_name: str
    email: str
    role_name: str
    is_active: bool
    is_locked: bool
    failed_attempts: int
    last_login_at: datetime | None


class UserCreate(BaseModel):
    login: str = Field(min_length=3, max_length=50,
                       pattern=r"^[a-zA-Z0-9._-]+$")
    full_name: str = Field(min_length=3, max_length=150)
    email: EmailStr
    password: str
    role: str


class UserUpdate(BaseModel):
    full_name: str | None = None
    email: EmailStr | None = None
    role: str | None = None


class PeriodIn(BaseModel):
    date_from: date
    date_to: date


class ImportIn(PeriodIn):
    departments: list[str] | None = None


class DetectIn(PeriodIn):
    strategy: str = Field(default="ml", pattern="^(ml|stat)$")


class TransitionIn(BaseModel):
    action: str
    comment: str | None = Field(default=None, max_length=2000)
    mitigation_plan: str | None = Field(default=None, max_length=2000)
    mitigation_owner: str | None = None
    mitigation_due: date | None = None
    effectiveness_confirmed: bool = False


class ReportCreate(PeriodIn):
    title: str = Field(min_length=3, max_length=200)


class ReturnIn(BaseModel):
    comment: str = Field(default="", max_length=2000)


def risk_out(risk: Risk) -> dict:
    t = risk.transaction
    return {
        "id": risk.id, "code": risk.code, "risk_type": risk.risk_type,
        "description": risk.description, "method": risk.method,
        "anomaly_score": float(risk.anomaly_score),
        "probability": float(risk.probability),
        "impact": float(risk.impact), "materiality": risk.materiality,
        "level": risk.level, "zone": ZONES.get(risk.level, "green"),
        "status": risk.status, "comment": risk.comment,
        "mitigation_plan": risk.mitigation_plan,
        "mitigation_owner": risk.mitigation_owner,
        "mitigation_due": risk.mitigation_due,
        "effectiveness_confirmed": risk.effectiveness_confirmed,
        "created_at": risk.created_at, "updated_at": risk.updated_at,
        "escalated_at": risk.escalated_at, "report_id": risk.report_id,
        "actions": [{"action": a, "title": ACTION_TITLES[a]}
                    for a in available_actions(risk.status)],
        "transaction": {
            "id": t.id, "doc_number": t.doc_number,
            "transaction_date": t.transaction_date,
            "amount": float(t.amount),
            "counterparty_info": t.counterparty_info,
            "department": t.department.name,
            "account_debit": t.account_debit,
            "account_credit": t.account_credit},
    }


def report_out(report: AuditReport, full: bool = False) -> dict:
    data = {
        "id": report.id, "title": report.title,
        "period_from": report.period_from, "period_to": report.period_to,
        "status": report.status, "created_at": report.created_at,
        "submitted_at": report.submitted_at,
        "approved_at": report.approved_at,
        "author": report.author.full_name,
        "approver": report.approver.full_name if report.approver else None,
        "review_comment": report.review_comment,
        "signature": report.signature,
        "summary": {k: v for k, v in (report.summary or {}).items()
                    if full or k != "heatmap"},
    }
    return data


def user_out(user: User) -> dict:
    return UserOut.model_validate(user).model_dump()


TokenOut.model_rebuild()
