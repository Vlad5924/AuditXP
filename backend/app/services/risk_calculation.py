"""Сервис расчета рисков (контекст паттерна «Стратегия», ЛР8)."""
import asyncio
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import BusinessError
from app.db.models import Risk, User
from app.domain.enums import RiskLevel, RoleName
from app.domain.risk_matrix import (
    DAMAGE_LABELS,
    PROBABILITY_LABELS,
    ZONES,
    damage_class,
    level_for_score,
    probability_class,
)
from app.ml.features import build_features, classify
from app.ml.strategies import IScoringStrategy
from app.repository.audit_repository import AuditRepository
from app.repository.risk_repository import IRiskRepository
from app.services.notification_service import NotificationService


@dataclass
class DetectionResult:
    transactions: int
    risks_created: int
    skipped_existing: int
    critical: int
    method: str
    risk_ids: list[int] = field(default_factory=list)


class RiskCalculationService:
    """Скоринг транзакций, расчет вероятности, ущерба и уровня риска."""

    THRESHOLD = 0.85

    def __init__(self, session: AsyncSession, strategy: IScoringStrategy,
                 risk_repo: IRiskRepository,
                 notifier: NotificationService | None = None) -> None:
        self.session = session
        self.strategy = strategy
        self.risk_repo = risk_repo
        self.notifier = notifier or NotificationService(session)
        self.audit = AuditRepository(session)
        self.settings = get_settings()

    async def score_transactions(self, date_from: date, date_to: date,
                                 user: User) -> DetectionResult:
        txns = await self.risk_repo.get_transactions(date_from, date_to)
        if txns.empty:
            raise BusinessError("Данные за период отсутствуют")
        scores = await asyncio.to_thread(self.strategy.score, txns)
        features = await asyncio.to_thread(build_features, txns)
        flagged = [i for i, s in enumerate(scores) if s >= self.THRESHOLD]
        ids = txns["id"].iloc[flagged].tolist()
        existing = await self.risk_repo.existing_transaction_ids(ids)
        risks: list[Risk] = []
        for i in flagged:
            txn = txns.iloc[i]
            if int(txn["id"]) in existing:
                continue
            feats = features.iloc[i]
            risk_type, description = classify(feats)
            risk = Risk(transaction_id=int(txn["id"]), user_id=user.id,
                        risk_type=risk_type, description=description,
                        method=self.strategy.name,
                        anomaly_score=Decimal(f"{scores[i]:.3f}"))
            risk.probability = self.calculate_probability(
                float(scores[i]), int(feats["dup_count"]))
            risk.impact = self.calculate_damage(txn)
            risk.calculate_level()
            risks.append(risk)
        await self.risk_repo.save_all(risks)
        critical = [r for r in risks if r.level == RiskLevel.CRITICAL]
        await self._alert(risks, critical, date_from, date_to)
        self.audit.add(user_id=user.id, table_name="risks", action="DETECT",
                       details=f"{self.strategy.name}, период {date_from} "
                               f"– {date_to}, создано {len(risks)}")
        await self.session.commit()
        return DetectionResult(
            transactions=len(txns), risks_created=len(risks),
            skipped_existing=len(existing), critical=len(critical),
            method=self.strategy.name, risk_ids=[r.id for r in risks])

    def calculate_probability(self, score: float, repeats: int = 0) -> Decimal:
        """Вероятность реализации риска по оценке аномальности и
        частоте повторения отклонения (FR-3.2)."""
        base = (score - self.THRESHOLD) / (1 - self.THRESHOLD)
        value = 0.15 + 0.7 * min(max(base, 0.0), 1.0)
        value += 0.05 * min(max(repeats, 0), 3)
        return Decimal(f"{min(value, 0.99):.2f}")

    @staticmethod
    def calculate_damage(txn) -> Decimal:
        """Потенциальный ущерб равен сумме операции по модулю."""
        return Decimal(f"{abs(float(txn['amount'])):.2f}")

    async def _alert(self, risks, critical, date_from, date_to) -> None:
        large = [r for r in risks
                 if float(r.impact) > self.settings.fraud_alert_amount]
        if not risks:
            return
        await self.notifier.notify_role(
            RoleName.CHIEF,
            f"Скоринг за {date_from:%d.%m.%Y}–{date_to:%d.%m.%Y}. Выявлено "
            f"рисков {len(risks)}, критических {len(critical)}, операций "
            f"свыше {self.settings.fraud_alert_amount:,.0f} BYN "
            f"{len(large)}".replace(",", " "),
            subject="AuditXP – результаты скоринга" if critical else None)

    @staticmethod
    def build_heatmap(risks: list[Risk], top: int = 5) -> dict:
        """Тепловая карта 5x5 «вероятность x ущерб» (FR-4.1)."""
        cells = [[{"count": 0, "impact": 0.0, "score": (p + 1) * (d + 1),
                   "zone": ZONES[level_for_score((p + 1) * (d + 1))]}
                  for d in range(5)] for p in range(5)]
        for risk in risks:
            p = probability_class(float(risk.probability)) - 1
            d = damage_class(float(risk.impact)) - 1
            cells[p][d]["count"] += 1
            cells[p][d]["impact"] += float(risk.impact)
        ranked = sorted(risks, key=lambda r: (r.materiality,
                                              float(r.impact)),
                        reverse=True)[:top]
        return {"probability_labels": list(PROBABILITY_LABELS),
                "damage_labels": list(DAMAGE_LABELS), "cells": cells,
                "total": len(risks), "escalation_score": 15,
                "top": [{"id": r.id, "code": r.code,
                         "risk_type": r.risk_type,
                         "materiality": r.materiality, "level": r.level,
                         "impact": float(r.impact)} for r in ranked]}
