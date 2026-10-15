-- Revenue and return rate by country (top 10 by revenue).
WITH s AS (SELECT country, sum(revenue) AS revenue, count(DISTINCT customer_id) AS customers FROM sales GROUP BY 1),
     r AS (SELECT country, sum(revenue) AS returned FROM returns WHERE invoice_date < DATE '2011-12-01' GROUP BY 1)
SELECT s.country, round(s.revenue, 0) AS revenue, s.customers,
       round(100 * s.revenue / sum(s.revenue) OVER (), 1)        AS revenue_share_pct,
       round(100 * coalesce(r.returned, 0) / s.revenue, 1)        AS return_rate_pct
FROM s LEFT JOIN r USING (country)
ORDER BY s.revenue DESC
LIMIT 10;
