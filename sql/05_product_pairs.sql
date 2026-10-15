-- Market basket analysis: product pairs bought in the same order, ranked by lift.
-- support = share of orders with both items; lift > 1 means they sell together more than by chance.
WITH baskets AS (
    SELECT DISTINCT Invoice, StockCode FROM sales
),
n_orders AS (SELECT count(DISTINCT Invoice) AS n FROM baskets),
item AS (
    SELECT StockCode, count(*) AS orders FROM baskets GROUP BY 1 HAVING count(*) >= 300
),
pairs AS (
    SELECT a.StockCode AS item_a, b.StockCode AS item_b, count(*) AS together
    FROM baskets a
    JOIN baskets b ON a.Invoice = b.Invoice AND a.StockCode < b.StockCode
    WHERE a.StockCode IN (SELECT StockCode FROM item) AND b.StockCode IN (SELECT StockCode FROM item)
    GROUP BY 1, 2
    HAVING count(*) >= 150
),
names AS (
    SELECT StockCode, mode(description) AS description FROM sales GROUP BY 1
)
SELECT na.description AS product_a, nb.description AS product_b, p.together AS orders_together,
       round(p.together / ia.orders, 3)                                 AS confidence_a_to_b,
       round(p.together * n.n / (ia.orders * ib.orders), 1)             AS lift
FROM pairs p
JOIN item ia ON ia.StockCode = p.item_a
JOIN item ib ON ib.StockCode = p.item_b
JOIN names na ON na.StockCode = p.item_a
JOIN names nb ON nb.StockCode = p.item_b
CROSS JOIN n_orders n
ORDER BY lift DESC
LIMIT 15;
