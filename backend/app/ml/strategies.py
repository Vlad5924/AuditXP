"""Стратегии скоринга транзакций (паттерн «Стратегия», ЛР8)."""
from abc import ABC, abstractmethod

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from app.ml.features import FEATURES, build_features


class IScoringStrategy(ABC):
    """Интерфейс стратегии, возвращающей оценки аномальности 0..1."""

    name: str = "base"

    @abstractmethod
    def score(self, txns: pd.DataFrame) -> np.ndarray:
        """Вычисляет оценку аномальности для каждой транзакции."""


class MLAnomalyDetector(IScoringStrategy):
    """Выявление аномалий алгоритмом Isolation Forest (FR-3.1)."""

    name = "Isolation Forest"

    def __init__(self, contamination: float = 0.05,
                 threshold: float = 0.85, n_estimators: int = 200,
                 random_state: int = 42) -> None:
        self.contamination = contamination
        self.threshold = threshold
        self.n_estimators = n_estimators
        self.random_state = random_state

    def score(self, txns: pd.DataFrame) -> np.ndarray:
        if len(txns) < 20:
            return np.zeros(len(txns))
        features = build_features(txns)[FEATURES].to_numpy()
        model = IsolationForest(n_estimators=self.n_estimators,
                                contamination=self.contamination,
                                random_state=self.random_state)
        model.fit(features)
        raw = -model.score_samples(features)
        return self._calibrate(raw, cut=-model.offset_)

    def _calibrate(self, raw: np.ndarray, cut: float) -> np.ndarray:
        """Сопоставляет границу contamination с порогом 0,85."""
        low, high = float(raw.min()), float(raw.max())
        upper = self.threshold + (1 - self.threshold) * (
            (raw - cut) / max(high - cut, 1e-9))
        lower = self.threshold * (raw - low) / max(cut - low, 1e-9)
        scores = np.where(raw > cut, upper, np.minimum(lower, 0.849))
        return np.clip(scores, 0.0, 1.0)


class StatisticalScoringStrategy(IScoringStrategy):
    """Z-оценка суммы в скользящем окне подразделения (BR-15)."""

    name = "Z-оценка"

    def __init__(self, sigma: float = 3.0, window: int = 200,
                 threshold: float = 0.85) -> None:
        self.sigma = sigma
        self.window = window
        self.threshold = threshold

    def score(self, txns: pd.DataFrame) -> np.ndarray:
        if txns.empty:
            return np.zeros(0)
        frame = txns.assign(_amount=txns["amount"].astype(float))
        frame = frame.sort_values("transaction_date")
        z = pd.Series(0.0, index=frame.index)
        for _, group in frame.groupby("department_id"):
            rolling = group["_amount"].rolling(self.window, min_periods=10)
            mean = rolling.mean().shift(1)
            std = rolling.std().shift(1).replace(0, np.nan)
            z.loc[group.index] = ((group["_amount"] - mean) / std).fillna(0)
        scores = np.abs(z.reindex(txns.index).to_numpy())
        return np.clip(scores * self.threshold / self.sigma, 0.0, 1.0)


def make_strategy(name: str) -> IScoringStrategy:
    """Фабрика стратегий по коду из запроса (ml или stat)."""
    if name == "stat":
        return StatisticalScoringStrategy()
    return MLAnomalyDetector()
