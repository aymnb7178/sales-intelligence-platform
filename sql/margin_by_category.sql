-- Revenue, cost of goods and gross margin by product category.
SELECT p.category,
       ROUND(SUM(oi.quantity * oi.unit_price * (1 - oi.discount)), 2) AS revenue,
       ROUND(SUM(oi.quantity * p.unit_cost), 2)                       AS cogs,
       ROUND(SUM(oi.quantity * oi.unit_price * (1 - oi.discount))
             - SUM(oi.quantity * p.unit_cost), 2)                     AS profit,
       ROUND(100.0 * (SUM(oi.quantity * oi.unit_price * (1 - oi.discount))
             - SUM(oi.quantity * p.unit_cost))
             / SUM(oi.quantity * oi.unit_price * (1 - oi.discount)), 2) AS margin_pct
FROM order_items oi
JOIN products p ON p.product_id = oi.product_id
GROUP BY p.category
ORDER BY profit DESC;
