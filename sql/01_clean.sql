-- Clean sales lines: one row per real product sold to a known customer.
-- Rules (row counts are printed by src/run_analysis.py):
--   1. drop exact duplicate rows (34k)
--   2. drop cancellations (Invoice starts with 'C') -> kept separately in `returns`
--   3. drop non-product codes (postage, fees, manual adjustments, test items, gift vouchers)
--   4. drop rows with quantity <= 0 or price <= 0
--   5. customer-level analysis needs Customer_ID; revenue KPIs use all customers
CREATE OR REPLACE TABLE lines AS
SELECT DISTINCT
    Invoice,
    StockCode,
    trim(Description)               AS description,
    Quantity                        AS quantity,
    InvoiceDate                     AS invoice_ts,
    CAST(InvoiceDate AS DATE)       AS invoice_date,
    Price                           AS price,
    CAST(Customer_ID AS INTEGER)    AS customer_id,
    Country                         AS country,
    Quantity * Price                AS revenue
FROM raw
WHERE (regexp_matches(StockCode, '^[0-9]{5}') OR StockCode LIKE 'DCGS%')
  AND Invoice NOT LIKE 'C%'
  AND Quantity > 0
  AND Price > 0;

CREATE OR REPLACE TABLE returns AS
SELECT DISTINCT Invoice, StockCode, -Quantity AS quantity, Price AS price, -Quantity * Price AS revenue,
       CAST(InvoiceDate AS DATE) AS invoice_date, CAST(Customer_ID AS INTEGER) AS customer_id, Country AS country
FROM raw
WHERE Invoice LIKE 'C%' AND (regexp_matches(StockCode, '^[0-9]{5}') OR StockCode LIKE 'DCGS%');

-- Analysis window: two full years (Dec 2009 - Nov 2011). December 2011 has only 9 days.
CREATE OR REPLACE VIEW sales AS
SELECT * FROM lines WHERE invoice_date < DATE '2011-12-01';
