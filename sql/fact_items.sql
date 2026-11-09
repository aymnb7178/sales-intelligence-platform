-- Denormalised fact table (one row per order line) for BI import.
SELECT oi.item_id,
       oi.order_id,
       o.order_date,
       o.customer_id,
       oi.product_id,
       o.channel,
       oi.quantity,
       oi.unit_price,
       oi.discount,
       ROUND(oi.quantity * oi.unit_price * (1 - oi.discount), 2)                       AS revenue,
       ROUND(oi.quantity * p.unit_cost, 2)                                             AS cost,
       ROUND(oi.quantity * oi.unit_price * (1 - oi.discount) - oi.quantity * p.unit_cost, 2) AS profit
FROM order_items oi
JOIN orders o   ON o.order_id = oi.order_id
JOIN products p ON p.product_id = oi.product_id
ORDER BY oi.item_id;
