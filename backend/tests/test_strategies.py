"""Модульные тесты стратегий скоринга (FR-3.1, BR-15)."""
import numpy as np
import pandas as pd

from app.ml.strategies import MLAnomalyDetector, StatisticalScoringStrategy


def sample(n=1000, outliers=10, seed=1):
    rng = np.random.default_rng(seed)
    amount = rng.lognormal(np.log(9000), 0.5, n)
    amount[:outliers] *= 50
    return pd.DataFrame({
        "amount": amount,
        "department_id": rng.integers(1, 4, n),
        "transaction_date": pd.Timestamp("2026-09-01 09:00")
        + pd.to_timedelta(rng.integers(0, 29 * 24 * 60 // 2, n) * 2,
                          unit="m"),
        "counterparty_info": rng.choice(list("ABCDEFGH"), n)})


def test_isolation_forest_finds_injected_outliers():
    """UT-21. Isolation Forest выделяет внедренные выбросы."""
    scores = MLAnomalyDetector().score(sample())
    assert (scores[:10] >= 0.85).sum() >= 9


def test_flagged_share_matches_contamination():
    """UT-22. Доля аномалий соответствует contamination 0,05."""
    scores = MLAnomalyDetector().score(sample())
    assert 0.04 <= (scores >= 0.85).mean() <= 0.06


def test_scores_bounded_and_reproducible():
    """UT-23. Оценки лежат в [0; 1] и воспроизводимы."""
    data = sample()
    first, second = MLAnomalyDetector().score(data), \
        MLAnomalyDetector().score(data)
    assert np.all((first >= 0) & (first <= 1))
    assert np.allclose(first, second)


def test_zscore_three_sigma_rule():
    """UT-24. Отклонение более 3 сигма считается аномалией (BR-15)."""
    rng = np.random.default_rng(3)
    amount = np.append(rng.normal(1000, 100, 300), [1450, 1150])
    data = pd.DataFrame({
        "amount": amount, "department_id": 1,
        "transaction_date": pd.date_range("2026-09-01", periods=302,
                                          freq="h"),
        "counterparty_info": "A"})
    scores = StatisticalScoringStrategy().score(data)
    assert scores[300] >= 0.85 and scores[301] < 0.85


def test_small_sample_not_scored():
    """UT-25. Выборка менее 20 операций не оценивается моделью."""
    assert MLAnomalyDetector().score(sample(n=10, outliers=0)).sum() == 0
