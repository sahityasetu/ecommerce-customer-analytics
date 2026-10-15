-- RFM segmentation as of the day after the analysis window.
WITH base AS (
    SELECT customer_id,
           date_diff('day', max(invoice_date), DATE '2011-12-01') AS recency_days,
           count(DISTINCT Invoice)                                AS frequency,
           sum(revenue)                                           AS monetary
    FROM sales WHERE customer_id IS NOT NULL
    GROUP BY 1
),
scored AS (
    SELECT *,
           -- customer_id breaks ties so the scores are the same on every run
           ntile(5) OVER (ORDER BY recency_days DESC, customer_id)    AS r,   -- most recent buyers get 5
           ntile(5) OVER (ORDER BY frequency, monetary, customer_id)  AS f,
           ntile(5) OVER (ORDER BY monetary, customer_id)             AS m
    FROM base
)
SELECT *,
       CASE
           WHEN r >= 4 AND f >= 4                 THEN 'Champions'
           WHEN r >= 3 AND f >= 3                 THEN 'Loyal'
           WHEN r >= 4 AND f <= 2                 THEN 'New / Promising'
           WHEN r = 3  AND f <= 2                 THEN 'Needs Attention'
           WHEN r <= 2 AND f >= 4                 THEN 'At Risk (high value)'
           WHEN r <= 2 AND f = 3                  THEN 'At Risk'
           ELSE 'Hibernating'
       END AS segment
FROM scored;
