"""SQL verificado contra resultados conhecidos, incluindo meses sem venda."""

import unittest

import pandas as pd

from clean_data import clean_orders
from pipeline import query_metrics
from test_clean_data import order


class MetricsTests(unittest.TestCase):
    def setUp(self):
        raw = pd.DataFrame([
            order(order_id="O00001", quantity=3, returned_quantity=1, unit_cents=1999),
            order(order_id="O00002", order_date="2025-03-01", quantity=1,
                  returned_quantity=1, unit_cents=5000),
            order(order_id="O00003", quantity=1, returned_quantity=0, unit_cents=10000),
            order(order_id="O00004", status="cancelled", returned_quantity=0),
        ])
        self.cleaned, _, _ = clean_orders(raw)
        self.tables = query_metrics(self.cleaned, ":memory:")

    def test_revenue_matches_manual_calculation(self):
        summary = self.tables["summary"].iloc[0]
        self.assertEqual(summary["orders"], 3)
        self.assertEqual(summary["gross_cents"], 20997)
        self.assertEqual(summary["refund_cents"], 6999)
        self.assertEqual(summary["net_cents"], 13998)

    def test_rate_is_weighted_by_units(self):
        self.assertEqual(self.tables["summary"].iloc[0]["unit_return_pct"], 40.0)

    def test_monthly_and_product_totals_reconcile(self):
        for metric in ["gross_cents", "refund_cents", "net_cents", "orders"]:
            for level in ["monthly", "products"]:
                self.assertEqual(self.tables[level][metric].sum(), self.tables["summary"].iloc[0][metric])

    def test_missing_months_are_zero_not_omitted(self):
        monthly = self.tables["monthly"].set_index("month")
        self.assertEqual(len(monthly), 12)
        self.assertEqual(monthly.loc["2025-02", "net_cents"], 0)


if __name__ == "__main__":
    unittest.main()
