-- ABC (Pareto) analysis on product revenue.
-- A = products needed to reach the first 80% of revenue, B = next 15%, C = last 5%.
-- A product is classed by the cumulative share BEFORE it is added, so the product
-- that crosses a threshold belongs to the better class.
WITH prod AS (
    SELECT p.product_id, p.name, p.category,
           SUM(oi.quantity * oi.unit_price * (1 - oi.discount)) AS revenue
    FROM order_items oi
    JOIN products p ON p.product_id = oi.product_id
    GROUP BY p.product_id
),
ranked AS (
    SELECT *,
           SUM(revenue) OVER (ORDER BY revenue DESC, product_id
                              ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cum_rev,
           SUM(revenue) OVER () AS total_rev
    FROM prod
)
SELECT product_id, name, category,
       ROUND(revenue, 2)                        AS revenue,
       ROUND(100.0 * cum_rev / total_rev, 2)    AS cum_share_pct,
       CASE WHEN 100.0 * (cum_rev - revenue) / total_rev < 80 THEN 'A'
            WHEN 100.0 * (cum_rev - revenue) / total_rev < 95 THEN 'B'
            ELSE 'C' END                        AS abc_class
FROM ranked
ORDER BY revenue DESC;
