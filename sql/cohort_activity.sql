-- Cohort activity: for each acquisition cohort (month of first order) and each
-- month offset, how many distinct customers placed at least one order.
WITH first_order AS (
    SELECT customer_id, strftime('%Y-%m', MIN(order_date)) AS cohort_month
    FROM orders
    GROUP BY customer_id
),
activity AS (
    SELECT DISTINCT customer_id, strftime('%Y-%m', order_date) AS activity_month
    FROM orders
)
SELECT f.cohort_month,
       (CAST(substr(a.activity_month, 1, 4) AS INTEGER) - CAST(substr(f.cohort_month, 1, 4) AS INTEGER)) * 12
       + CAST(substr(a.activity_month, 6, 2) AS INTEGER) - CAST(substr(f.cohort_month, 6, 2) AS INTEGER)
           AS month_index,
       COUNT(DISTINCT a.customer_id) AS active_customers
FROM first_order f
JOIN activity a ON a.customer_id = f.customer_id
GROUP BY f.cohort_month, month_index
ORDER BY f.cohort_month, month_index;
