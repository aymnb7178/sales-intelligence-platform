"""Monthly revenue forecasting with an honest holdout backtest.

Models (all take a monthly revenue ``pd.Series`` with a monthly PeriodIndex):

* ``naive``                  repeat the last observed month (baseline)
* ``seasonal_naive``         repeat the value from the same month one year earlier
* ``seasonal_naive_drift``   seasonal naive scaled by the last-12m / prior-12m ratio
* ``trend_seasonal_lr``      scikit-learn LinearRegression on a time index plus
                             month-of-year dummies (linear trend + additive seasonality)

The backtest trains on everything except the last ``holdout`` months and reports
MAPE on those months. It is a single holdout, so treat the numbers as indicative.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression


def mape(actual: np.ndarray, predicted: np.ndarray) -> float:
    """Mean absolute percentage error in percent. Zero actuals are ignored."""
    a = np.asarray(actual, dtype=float)
    p = np.asarray(predicted, dtype=float)
    mask = a != 0
    if not mask.any():
        raise ValueError("MAPE is undefined when every actual value is zero")
    return float(np.mean(np.abs((a[mask] - p[mask]) / a[mask])) * 100.0)


def monthly_series(monthly: pd.DataFrame) -> pd.Series:
    """Turn the ``monthly_revenue`` query result into a PeriodIndex series."""
    s = monthly.set_index(pd.PeriodIndex(monthly["month"], freq="M"))["revenue"].astype(float).sort_index()
    # months without any order are real zeros; keep the index contiguous
    return s.reindex(pd.period_range(s.index[0], s.index[-1], freq="M"), fill_value=0.0)


def _future_months(train: pd.Series, horizon: int) -> list[pd.Period]:
    last = train.index[-1]
    return [last + k for k in range(1, horizon + 1)]


def naive(train: pd.Series, horizon: int) -> np.ndarray:
    return np.repeat(train.iloc[-1], horizon).astype(float)


def seasonal_naive(train: pd.Series, horizon: int) -> np.ndarray:
    last_year = train.iloc[-12:].to_numpy()
    return np.array([last_year[(h) % 12] for h in range(horizon)], dtype=float)


def seasonal_naive_drift(train: pd.Series, horizon: int) -> np.ndarray:
    recent = train.iloc[-12:].sum()
    prior = train.iloc[-24:-12].sum()
    return seasonal_naive(train, horizon) * (recent / prior)


def _design(t: np.ndarray, month_of_year: np.ndarray) -> np.ndarray:
    dummies = [(month_of_year == m).astype(float) for m in range(2, 13)]
    return np.column_stack([t.astype(float)] + dummies)


def trend_seasonal_lr(train: pd.Series, horizon: int) -> np.ndarray:
    n = len(train)
    x_train = _design(np.arange(n), train.index.month.to_numpy())
    model = LinearRegression().fit(x_train, train.to_numpy())
    fut = _future_months(train, horizon)
    x_fut = _design(np.arange(n, n + horizon), np.array([p.month for p in fut]))
    return model.predict(x_fut)


# name -> (function, minimum training length)
MODELS: dict[str, tuple[Callable[[pd.Series, int], np.ndarray], int]] = {
    "naive": (naive, 1),
    "seasonal_naive": (seasonal_naive, 12),
    "seasonal_naive_drift": (seasonal_naive_drift, 24),
    "trend_seasonal_lr": (trend_seasonal_lr, 13),
}


@dataclass
class BacktestResult:
    """Outcome of a holdout backtest."""

    holdout: int
    metrics: dict[str, float]
    predictions: pd.DataFrame
    best_model: str
    baseline_model: str = "naive"

    @property
    def improvement_vs_naive_pct(self) -> float:
        """Relative MAPE reduction of the best model versus the naive baseline."""
        base = self.metrics[self.baseline_model]
        return 100.0 * (base - self.metrics[self.best_model]) / base


def backtest(series: pd.Series, holdout: int = 6) -> BacktestResult:
    """Fit every eligible model on ``series[:-holdout]`` and score it on the rest."""
    if holdout < 1 or holdout >= len(series):
        raise ValueError("holdout must be between 1 and len(series) - 1")
    train, test = series.iloc[:-holdout], series.iloc[-holdout:]
    preds = pd.DataFrame({"actual": test.to_numpy()}, index=test.index)
    metrics: dict[str, float] = {}
    for name, (fn, min_len) in MODELS.items():
        if len(train) < min_len:
            continue
        preds[name] = fn(train, holdout)
        metrics[name] = mape(test.to_numpy(), preds[name].to_numpy())
    best = min(metrics, key=metrics.get)
    return BacktestResult(holdout, metrics, preds, best)


def forecast_future(series: pd.Series, model: str, horizon: int = 6) -> pd.DataFrame:
    """Refit ``model`` on the full series and predict the next ``horizon`` months."""
    fn, min_len = MODELS[model]
    if len(series) < min_len:
        raise ValueError(f"{model} needs at least {min_len} months of history")
    values = fn(series, horizon)
    idx = _future_months(series, horizon)
    return pd.DataFrame({"month": [str(p) for p in idx], "forecast": np.round(values, 2), "model": model})
