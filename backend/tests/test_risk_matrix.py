"""Модульные тесты матрицы рисков 5x5 (BR-5, FR-4.1)."""
import pytest

from app.domain.enums import RiskLevel
from app.domain.risk_matrix import (
    damage_class,
    level_for_score,
    materiality,
    probability_class,
)


@pytest.mark.parametrize("p, expected", [(0, 1), (0.19, 1), (0.2, 2),
                                         (0.55, 3), (0.85, 5), (1.0, 5)])
def test_probability_class(p, expected):
    """UT-07. Вероятность переводится в балл от 1 до 5."""
    assert probability_class(p) == expected


@pytest.mark.parametrize("impact, expected", [
    (5_000, 1), (10_000, 2), (250_000, 3), (999_999.99, 4),
    (1_850_000, 5)])
def test_damage_class(impact, expected):
    """UT-08. Ущерб в BYN переводится в балл от 1 до 5."""
    assert damage_class(impact) == expected


@pytest.mark.parametrize("score, level", [
    (4, RiskLevel.LOW), (5, RiskLevel.MEDIUM), (10, RiskLevel.HIGH),
    (15, RiskLevel.CRITICAL), (25, RiskLevel.CRITICAL)])
def test_level_for_score(score, level):
    """UT-09. Зоны карты и порог эскалации 15 баллов."""
    assert level_for_score(score) == level


def test_materiality_of_double_posting():
    """UT-10. Дублирование на 1 850 000 BYN с p=0,87 дает 25 баллов."""
    assert materiality(0.87, 1_850_000) == 25
