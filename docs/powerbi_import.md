# Importing the CSV export into Power BI

> No `.pbix` file is included in this repository. This page only describes how you could
> build one from the CSV files. The measures below are suggestions written as text and
> have **not** been executed in Power BI Desktop. All data is **synthetic**.

## 1. Generate the files

```bash
python -m sales_intel all        # or: python -m sales_intel export
```

Files are written to `output/powerbi_csv/`:

| File | Grain | Role |
|---|---|---|
| `fact_order_items.csv` | one row per order line | fact (revenue, cost, profit) |
| `dim_customers.csv` | one row per customer | dimension |
| `dim_products.csv` | one row per product | dimension |
| `dim_date.csv` | one row per calendar day | dimension |
| `rfm_segments.csv` | one row per customer | customer attributes (R/F/M scores, segment) |
| `cohort_retention.csv` | cohort x month offset | stand-alone table |
| `monthly_revenue.csv` | one row per month | stand-alone table (SQL growth columns) |
| `forecast.csv`, `backtest_metrics.csv` | forecast months / models | stand-alone tables |
| `abc_analysis.csv` | one row per product | product attributes (ABC class) |

## 2. Import steps

1. Power BI Desktop > Get data > Text/CSV, load each file (UTF-8).
2. Set `fact_order_items[order_date]` and `dim_date[date]` to type **Date**.
3. Mark `dim_date` as the date table (Table tools > Mark as date table, column `date`).

## 3. Suggested relationships

| From (many) | To (one) | Cardinality |
|---|---|---|
| `fact_order_items[order_date]` | `dim_date[date]` | many-to-one, single |
| `fact_order_items[customer_id]` | `dim_customers[customer_id]` | many-to-one, single |
| `fact_order_items[product_id]` | `dim_products[product_id]` | many-to-one, single |
| `rfm_segments[customer_id]` | `dim_customers[customer_id]` | one-to-one |
| `abc_analysis[product_id]` | `dim_products[product_id]` | one-to-one |

## 4. Suggested DAX measures

```dax
Revenue = SUM ( fact_order_items[revenue] )

Cost = SUM ( fact_order_items[cost] )

Profit = [Revenue] - [Cost]

Gross Margin % = DIVIDE ( [Profit], [Revenue] )

Orders = DISTINCTCOUNT ( fact_order_items[order_id] )

Customers = DISTINCTCOUNT ( fact_order_items[customer_id] )

Avg Order Value = DIVIDE ( [Revenue], [Orders] )

Revenue PY = CALCULATE ( [Revenue], SAMEPERIODLASTYEAR ( dim_date[date] ) )

Revenue YoY % = DIVIDE ( [Revenue] - [Revenue PY], [Revenue PY] )

Revenue MoM % =
VAR Prev = CALCULATE ( [Revenue], DATEADD ( dim_date[date], -1, MONTH ) )
RETURN DIVIDE ( [Revenue] - Prev, Prev )

Revenue YTD = TOTALYTD ( [Revenue], dim_date[date] )

Repeat Customers =
COUNTROWS (
    FILTER (
        VALUES ( fact_order_items[customer_id] ),
        CALCULATE ( DISTINCTCOUNT ( fact_order_items[order_id] ) ) >= 2
    )
)

Repeat Customer Rate % = DIVIDE ( [Repeat Customers], [Customers] )
```

## 5. Suggested report pages

- **Overview:** KPI cards (Revenue, Profit, Gross Margin %, Orders, Avg Order Value), line chart of Revenue by `dim_date[year_month]`.
- **Products:** bar chart of Revenue by `dim_products[name]` (Top N filter), margin by `category`, ABC class slicer.
- **Customers:** RFM segment counts and revenue share, region slicer.
- **Retention:** matrix visual with `cohort_month` rows, `month_index` columns, `retention_pct` values.
- **Forecast:** line chart from `monthly_revenue` plus `forecast`; table of `backtest_metrics`.
