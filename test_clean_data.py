"""Testes das regras que poderiam distorcer os indicadores."""

import unittest

import pandas as pd

from clean_data import REQUIRED, clean_orders
from generate_data import generate


def order(**changes):
    row = dict(order_id="O00001", order_date="2025-01-01", sku="P01",
               product="Teclado", category="Periféricos", quantity=3,
               returned_quantity=1, unit_cents=1999, status="delivered")
    row.update(changes)
    return row


class CleaningTests(unittest.TestCase):
    def clean(self, *rows):
        return clean_orders(pd.DataFrame(rows, columns=REQUIRED))

    def test_partial_refund_uses_integer_cents(self):
        frame, _, _ = self.clean(order())
        self.assertEqual(frame.iloc[0]["net_cents"], 3998)
        self.assertEqual(frame.iloc[0]["refund_cents"], 1999)

    def test_full_refund_has_zero_revenue(self):
        frame, _, _ = self.clean(order(returned_quantity=3))
        self.assertEqual(frame.iloc[0]["net_cents"], 0)

    def test_exact_duplicate_does_not_double_revenue(self):
        frame, audit, _ = self.clean(order(), order())
        self.assertEqual(len(frame), 1)
        self.assertEqual(audit["exact_duplicates_removed"], 1)

    def test_conflicting_id_rejects_both_versions(self):
        frame, audit, rejected = self.clean(order(), order(unit_cents=2000))
        self.assertTrue(frame.empty)
        self.assertEqual(audit["conflicting_rows_rejected"], 2)
        self.assertEqual(set(rejected["reason"]), {"conflicting_order_id"})

    def test_invalid_values_are_quarantined(self):
        cases = [dict(quantity=-1), dict(quantity=1.5), dict(returned_quantity=4),
                 dict(returned_quantity=-1), dict(unit_cents=0), dict(unit_cents="x"),
                 dict(unit_cents=float("inf")), dict(order_date="2025-02-30"),
                 dict(order_date="2026-01-01"), dict(sku="X"), dict(product="x"),
                 dict(category="x"), dict(status="pending"), dict(order_id=None)]
        for changes in cases:
            with self.subTest(changes=changes):
                frame, audit, _ = self.clean(order(**changes))
                self.assertTrue(frame.empty)
                self.assertEqual(audit["invalid_rows_rejected"], 1)

    def test_cancellation_is_not_revenue(self):
        frame, audit, _ = self.clean(order(status="cancelled", returned_quantity=0))
        self.assertTrue(frame.empty)
        self.assertEqual(audit["cancelled_orders_excluded"], 1)

    def test_missing_schema_is_explicit(self):
        with self.assertRaisesRegex(ValueError, "Colunas ausentes"):
            clean_orders(pd.DataFrame({"order_id": ["O00001"]}))

    def test_empty_input_preserves_audit(self):
        frame, audit, _ = self.clean()
        self.assertTrue(frame.empty)
        self.assertEqual(sum(audit.values()), 0)

    def test_generator_is_reproducible_and_audit_reconciles(self):
        raw = generate()
        pd.testing.assert_frame_equal(raw, generate())
        frame, audit, _ = clean_orders(raw)
        self.assertEqual(audit["input_rows"], 3650)
        self.assertEqual(audit["exact_duplicates_removed"], 36)
        self.assertEqual(audit["conflicting_rows_rejected"], 4)
        self.assertEqual(audit["invalid_rows_rejected"], 12)
        self.assertTrue(frame["order_id"].is_unique)


if __name__ == "__main__":
    unittest.main()
