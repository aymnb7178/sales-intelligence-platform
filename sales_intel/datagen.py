"""SYNTHETIC retail data generator.

Everything produced here is randomly generated from a seeded RNG. There are no
real customers, products, orders or prices. Names are placeholders such as
``Electronics Item 03`` and customer codes such as ``C00042``.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from .config import GenConfig

log = logging.getLogger(__name__)

# category -> (min list price, max list price, mean cost/price ratio)
CATEGORIES: dict[str, tuple[float, float, float]] = {
    "Electronics": (120.0, 450.0, 0.80),
    "Accessories": (10.0, 60.0, 0.55),
    "Home": (30.0, 180.0, 0.65),
    "Beauty": (8.0, 70.0, 0.45),
    "Sports": (25.0, 200.0, 0.62),
    "Grocery": (3.0, 25.0, 0.78),
}
REGIONS = ["Central", "West", "East", "North", "South"]
ACQ_CHANNELS = ["organic", "paid_ads", "referral"]
ORDER_CHANNELS = ["web", "mobile_app", "store"]
# Month-of-year demand multipliers (Jan..Dec); Nov/Dec have a promo peak.
SEASONALITY = [0.90, 0.85, 0.95, 1.00, 1.00, 0.95, 0.90, 0.95, 1.00, 1.05, 1.35, 1.25]
PROMO_MONTHS = (11,)


def _make_products(cfg: GenConfig, rng: np.random.Generator) -> pd.DataFrame:
    rows = []
    pid = 1
    for cat, (lo, hi, ratio) in CATEGORIES.items():
        for i in range(cfg.products_per_category):
            price = round(float(np.exp(rng.uniform(np.log(lo), np.log(hi)))), 2)
            cost = round(price * float(np.clip(rng.normal(ratio, 0.05), 0.3, 0.95)), 2)
            rows.append((pid, f"{cat} Item {i + 1:02d}", cat, cost, price))
            pid += 1
    return pd.DataFrame(rows, columns=["product_id", "name", "category", "unit_cost", "unit_price"])


def generate(cfg: GenConfig | None = None) -> dict[str, pd.DataFrame]:
    """Generate the four synthetic tables.

    Returns a dict with keys ``customers``, ``products``, ``orders`` and
    ``order_items``. The same config always yields identical data.
    """
    cfg = cfg or GenConfig()
    rng = np.random.default_rng(cfg.seed)
    months = pd.period_range(cfg.start, cfg.end, freq="M")
    n_months = len(months)
    n_cust = cfg.n_customers

    products = _make_products(cfg, rng)
    n_prod = len(products)

    # --- customer behaviour: staggered sign-ups, per-customer rate, finite lifetime
    growth = np.linspace(1.0, 2.2, n_months)
    signup_m = rng.choice(n_months, size=n_cust, p=growth / growth.sum())
    rate = rng.gamma(1.6, 0.22, size=n_cust)  # mean ~0.35 orders / month
    lifetime = rng.exponential(18.0, size=n_cust) + 1.0  # months
    age = np.arange(n_months)[None, :] - signup_m[:, None]
    alive = (age >= 0) & (age <= lifetime[:, None])
    season = np.array(SEASONALITY)[months.month.to_numpy() - 1]
    counts = rng.poisson(rate[:, None] * season[None, :] * alive)
    first = np.arange(n_cust)
    counts[first, signup_m] = np.maximum(counts[first, signup_m], 1)  # sign-up = first order

    # --- orders
    ci, mi = np.nonzero(counts)
    reps = counts[ci, mi]
    cust_idx = np.repeat(ci, reps)
    m_idx = np.repeat(mi, reps)
    n_orders = len(m_idx)
    days_in = months.days_in_month.to_numpy()[m_idx]
    day = np.floor(rng.random(n_orders) * days_in).astype(int) + 1
    dates = pd.to_datetime(
        pd.DataFrame(
            {"year": months.year.to_numpy()[m_idx], "month": months.month.to_numpy()[m_idx], "day": day}
        )
    )
    channel = rng.choice(ORDER_CHANNELS, size=n_orders, p=[0.45, 0.35, 0.20])
    orders = pd.DataFrame({"customer_id": cust_idx + 1, "order_date": dates, "channel": channel})
    orders = orders.sort_values(["order_date", "customer_id"], kind="stable").reset_index(drop=True)
    orders.insert(0, "order_id", np.arange(1, n_orders + 1))

    customers = pd.DataFrame(
        {
            "customer_id": np.arange(1, n_cust + 1),
            "customer_code": [f"C{i:05d}" for i in range(1, n_cust + 1)],
            "region": rng.choice(REGIONS, size=n_cust),
            "acquisition_channel": rng.choice(ACQ_CHANNELS, size=n_cust, p=[0.5, 0.35, 0.15]),
        }
    )
    first_order = orders.groupby("customer_id")["order_date"].min()
    customers["signup_date"] = customers["customer_id"].map(first_order)

    # --- order items
    n_items = np.minimum(1 + rng.poisson(1.1, size=n_orders), 5)
    total = int(n_items.sum())
    pop = rng.pareto(1.5, n_prod) + 0.2
    prod_idx = rng.choice(n_prod, size=total, p=pop / pop.sum())
    qty = np.minimum(1 + rng.poisson(0.4, size=total), 5)
    item_month = np.repeat(orders["order_date"].dt.month.to_numpy(), n_items)
    levels = np.array([0.0, 0.05, 0.10, 0.20])
    d_norm = rng.choice(levels, size=total, p=[0.70, 0.15, 0.10, 0.05])
    d_promo = rng.choice(levels, size=total, p=[0.30, 0.20, 0.30, 0.20])
    discount = np.where(np.isin(item_month, PROMO_MONTHS), d_promo, d_norm)
    order_items = pd.DataFrame(
        {
            "item_id": np.arange(1, total + 1),
            "order_id": np.repeat(orders["order_id"].to_numpy(), n_items),
            "product_id": products["product_id"].to_numpy()[prod_idx],
            "quantity": qty,
            "unit_price": products["unit_price"].to_numpy()[prod_idx],
            "discount": discount,
        }
    )

    # SQLite stores dates as ISO text
    orders["order_date"] = orders["order_date"].dt.strftime("%Y-%m-%d")
    customers["signup_date"] = customers["signup_date"].dt.strftime("%Y-%m-%d")
    log.info("Generated %d customers, %d products, %d orders, %d items", n_cust, n_prod, n_orders, total)
    return {"customers": customers, "products": products, "orders": orders, "order_items": order_items}
