-- Raw RFM inputs per customer as of :ref_date (scoring happens in pandas).
SELECT o.customer_id,
       CAST(julianday(:ref_date) - julianday(MAX(o.order_date)) AS INTEGER) AS recency_days,
       COUNT(DISTINCT o.order_id)                                           AS frequency,
       ROUND(SUM(oi.quantity * oi.unit_price * (1 - oi.discount)), 2)       AS monetary
FROM orders o
JOIN order_items oi ON oi.order_id = o.order_id
WHERE o.order_date <= :ref_date
GROUP BY o.customer_id;
