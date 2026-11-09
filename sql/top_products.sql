-- Top products by revenue (parameter :limit).
SELECT p.product_id,
       p.name,
       p.category,
       SUM(oi.quantity)                                                        AS units,
       ROUND(SUM(oi.quantity * oi.unit_price * (1 - oi.discount)), 2)          AS revenue,
       ROUND(SUM(oi.quantity * oi.unit_price * (1 - oi.discount)
                 - oi.quantity * p.unit_cost), 2)                              AS profit
FROM order_items oi
JOIN products p ON p.product_id = oi.product_id
GROUP BY p.product_id
ORDER BY revenue DESC
LIMIT :limit;
