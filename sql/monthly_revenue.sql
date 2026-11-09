-- Monthly revenue with month-over-month and year-over-year growth.
-- revenue = quantity * unit_price * (1 - discount)
WITH monthly AS (
    SELECT strftime('%Y-%m', o.order_date)                          AS month,
           ROUND(SUM(oi.quantity * oi.unit_price * (1 - oi.discount)), 2) AS revenue,
           COUNT(DISTINCT o.order_id)                               AS orders,
           COUNT(DISTINCT o.customer_id)                            AS active_customers
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.order_id
    GROUP BY 1
)
SELECT month,
       revenue,
       orders,
       active_customers,
       ROUND(100.0 * (revenue - LAG(revenue, 1)  OVER w) / LAG(revenue, 1)  OVER w, 2) AS mom_growth_pct,
       ROUND(100.0 * (revenue - LAG(revenue, 12) OVER w) / LAG(revenue, 12) OVER w, 2) AS yoy_growth_pct
FROM monthly
WINDOW w AS (ORDER BY month)
ORDER BY month;
