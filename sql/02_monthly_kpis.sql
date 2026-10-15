-- Monthly business KPIs with year-over-year growth.
WITH m AS (
    SELECT date_trunc('month', invoice_date)          AS month,
           sum(revenue)                               AS revenue,
           count(DISTINCT Invoice)                    AS orders,
           count(DISTINCT customer_id)                AS active_customers
    FROM sales
    GROUP BY 1
)
SELECT month,
       round(revenue, 0)                                              AS revenue,
       orders,
       active_customers,
       round(revenue / orders, 2)                                     AS avg_order_value,
       round(100 * (revenue / lag(revenue, 12) OVER (ORDER BY month) - 1), 1) AS revenue_yoy_pct
FROM m
ORDER BY month;
