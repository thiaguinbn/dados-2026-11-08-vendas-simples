-- Valores monetários em centavos. Apenas pedidos entregues e válidos.
-- name: summary
SELECT COUNT(*) AS orders,
       COALESCE(SUM(quantity), 0) AS units_sold,
       COALESCE(SUM(returned_quantity), 0) AS units_returned,
       COALESCE(SUM(returned_quantity > 0), 0) AS orders_with_returns,
       COALESCE(SUM(gross_cents), 0) AS gross_cents,
       COALESCE(SUM(refund_cents), 0) AS refund_cents,
       COALESCE(SUM(net_cents), 0) AS net_cents,
       100.0 * SUM(returned_quantity) / NULLIF(SUM(quantity), 0) AS unit_return_pct,
       100.0 * SUM(refund_cents) / NULLIF(SUM(gross_cents), 0) AS revenue_refund_pct,
       1.0 * SUM(gross_cents) / NULLIF(COUNT(*), 0) AS gross_ticket_cents
FROM orders;

-- name: products
SELECT sku, product, category, COUNT(*) AS orders,
       SUM(quantity) AS units_sold,
       SUM(returned_quantity) AS units_returned,
       SUM(gross_cents) AS gross_cents,
       SUM(refund_cents) AS refund_cents,
       SUM(net_cents) AS net_cents,
       100.0 * SUM(returned_quantity) / NULLIF(SUM(quantity), 0) AS unit_return_pct,
       100.0 * SUM(refund_cents) / NULLIF(SUM(gross_cents), 0) AS revenue_refund_pct
FROM orders
GROUP BY sku, product, category
ORDER BY net_cents DESC, sku;

-- name: monthly
WITH RECURSIVE months(month) AS (
    SELECT '2025-01'
    UNION ALL
    SELECT strftime('%Y-%m', date(month || '-01', '+1 month'))
    FROM months WHERE month < '2025-12'
)
SELECT month, COUNT(o.order_id) AS orders,
       COALESCE(SUM(o.gross_cents), 0) AS gross_cents,
       COALESCE(SUM(o.refund_cents), 0) AS refund_cents,
       COALESCE(SUM(o.net_cents), 0) AS net_cents
FROM months
LEFT JOIN orders o ON substr(o.order_date, 1, 7) = month
GROUP BY month ORDER BY month;
