"""Матрица рисков 5x5 «вероятность x ущерб» (правило BR-5)."""
from app.domain.enums import RiskLevel

PROBABILITY_LABELS = ("Очень низкая", "Низкая", "Средняя", "Высокая",
                      "Очень высокая")
DAMAGE_LABELS = ("Незначительный", "Небольшой", "Средний", "Большой",
                 "Катастрофический")
DAMAGE_BOUNDS = (10_000, 100_000, 500_000, 1_000_000)
ZONES = {RiskLevel.LOW: "green", RiskLevel.MEDIUM: "yellow",
         RiskLevel.HIGH: "orange", RiskLevel.CRITICAL: "red"}


def probability_class(probability: float) -> int:
    """Переводит вероятность 0..1 в балл 1..5."""
    p = min(max(float(probability), 0.0), 1.0)
    return min(5, int(p * 5) + 1)


def damage_class(impact: float) -> int:
    """Переводит ущерб в BYN в балл 1..5."""
    value = abs(float(impact))
    return 1 + sum(value >= bound for bound in DAMAGE_BOUNDS)


def materiality(probability: float, impact: float) -> int:
    """Существенность риска = балл вероятности x балл ущерба (1..25)."""
    return probability_class(probability) * damage_class(impact)


def level_for_score(score: int) -> RiskLevel:
    if score >= 15:
        return RiskLevel.CRITICAL
    if score >= 10:
        return RiskLevel.HIGH
    if score >= 5:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW
