-- Monthly acquisition cohorts: % of each cohort that buys again N months after the first purchase.
WITH first_buy AS (
    SELECT customer_id, min(date_trunc('month', invoice_date)) AS cohort_month
    FROM sales WHERE customer_id IS NOT NULL
    GROUP BY 1
),
activity AS (
    SELECT DISTINCT s.customer_id, f.cohort_month,
           date_diff('month', f.cohort_month, date_trunc('month', s.invoice_date)) AS month_number
    FROM sales s JOIN first_buy f USING (customer_id)
),
sizes AS (
    SELECT cohort_month, count(*) AS cohort_size FROM first_buy GROUP BY 1
)
SELECT a.cohort_month, s.cohort_size, a.month_number,
       count(*)                                       AS active,
       round(100.0 * count(*) / s.cohort_size, 1)     AS retention_pct
FROM activity a JOIN sizes s USING (cohort_month)
-- Dec 2009 includes customers who were already buying before the data starts, so it is not a true new cohort.
WHERE a.cohort_month > DATE '2009-12-01'
GROUP BY 1, 2, 3
ORDER BY 1, 3;
