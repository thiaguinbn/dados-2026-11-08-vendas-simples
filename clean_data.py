"""Validação, quarentena e auditoria reconciliável dos pedidos de 2025."""

import numpy as np
import pandas as pd

from generate_data import CATALOG

REQUIRED = ["order_id", "order_date", "sku", "product", "category", "quantity",
            "returned_quantity", "unit_cents", "status"]


def clean_orders(raw):
    """Retorna entregues válidos, auditoria e rejeitados com motivo.

    Categorias da auditoria são exclusivas: duplicados exatos, IDs conflitantes,
    inválidos, cancelados válidos e entregues válidos, nesta ordem.
    """
    missing = set(REQUIRED) - set(raw.columns)
    if missing:
        raise ValueError(f"Colunas ausentes: {', '.join(sorted(missing))}")
    frame = raw[REQUIRED].copy()
    quarantine = []
    audit = {"input_rows": int(len(frame))}

    def reject(mask, reason):
        nonlocal frame
        rejected = frame.loc[mask].copy()
        rejected["reason"] = reason
        quarantine.append(rejected)
        frame = frame.loc[~mask].copy()
        return int(mask.sum())

    audit["exact_duplicates_removed"] = reject(frame.duplicated(), "exact_duplicate")
    audit["conflicting_rows_rejected"] = reject(
        frame["order_id"].duplicated(keep=False), "conflicting_order_id")

    numeric = ["quantity", "returned_quantity", "unit_cents"]
    parsed = frame[numeric].apply(pd.to_numeric, errors="coerce").astype("float64")
    numeric_ok = (np.isfinite(parsed).all(axis=1)
                  & parsed.eq(np.floor(parsed)).all(axis=1)
                  & parsed["quantity"].between(1, 1000)
                  & parsed["unit_cents"].between(1, 100_000_000)
                  & parsed["returned_quantity"].ge(0)
                  & parsed["returned_quantity"].le(parsed["quantity"]))
    dates = pd.to_datetime(frame["order_date"], format="%Y-%m-%d", errors="coerce")
    catalog_ok = frame["sku"].isin(CATALOG)
    names = {sku: value[0] for sku, value in CATALOG.items()}
    categories = {sku: value[1] for sku, value in CATALOG.items()}
    catalog_ok &= frame["product"].eq(frame["sku"].map(names))
    catalog_ok &= frame["category"].eq(frame["sku"].map(categories))
    valid = (numeric_ok & dates.between("2025-01-01", "2025-12-31")
             & frame["order_id"].fillna("").astype(str).str.fullmatch(r"O\d{5}")
             & catalog_ok & frame["status"].isin(["delivered", "cancelled"])
             & ~(frame["status"].eq("cancelled") & parsed["returned_quantity"].ne(0)))
    audit["invalid_rows_rejected"] = reject(~valid, "invalid_business_rule")
    frame[numeric] = parsed.loc[frame.index].astype("int64")
    audit["cancelled_orders_excluded"] = int(frame["status"].eq("cancelled").sum())
    frame = frame.loc[frame["status"].eq("delivered")].copy()
    frame["gross_cents"] = frame["quantity"] * frame["unit_cents"]
    frame["refund_cents"] = frame["returned_quantity"] * frame["unit_cents"]
    frame["net_cents"] = frame["gross_cents"] - frame["refund_cents"]
    audit["valid_delivered_orders"] = int(len(frame))
    assert audit["input_rows"] == sum(value for key, value in audit.items() if key != "input_rows")
    return (frame.sort_values("order_id").reset_index(drop=True), audit,
            pd.concat(quarantine, ignore_index=True))
