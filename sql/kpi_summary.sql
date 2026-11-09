-- Headline totals.
SELECT ROUND(SUM(oi.quantity * oi.unit_price * (1 - oi.discount)), 2) AS revenue,
       ROUND(SUM(oi.quantity * p.unit_cost), 2)                       AS cogs,
       COUNT(DISTINCT o.order_id)                                     AS orders,
       COUNT(DISTINCT o.customer_id)                                  AS customers,
       SUM(oi.quantity)                                               AS units,
       MIN(o.order_date)                                              AS first_order_date,
       MAX(o.order_date)                                              AS last_order_date
FROM orders o
JOIN order_items oi ON oi.order_id = o.order_id
JOIN products p ON p.product_id = oi.product_id;
