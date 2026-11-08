"""Base de pedidos inteiramente sintética; nenhuma informação de clientes reais."""

import argparse
import random
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

CATALOG = {
    "P01": ("Teclado", "Periféricos", 15990, 0.035),
    "P02": ("Mouse", "Periféricos", 8990, 0.025),
    "P03": ("Headset", "Áudio", 22990, 0.120),
    "P04": ("Caixa de som", "Áudio", 17990, 0.055),
    "P05": ("Webcam", "Vídeo", 19990, 0.045),
    "P06": ("Suporte de notebook", "Acessórios", 11990, 0.020),
}


def generate(seed=42, orders=3600):
    """Um pedido = um SKU; arredondamento de desconto por unidade, half-up."""
    if orders < 100:
        raise ValueError("Use pelo menos 100 pedidos para gerar as anomalias.")
    rng = random.Random(seed)
    rows = []
    for i in range(orders):
        sku = rng.choices(list(CATALOG), weights=[20, 28, 18, 10, 10, 14])[0]
        name, category, price, return_probability = CATALOG[sku]
        quantity = rng.choices([1, 2, 3, 4], weights=[65, 23, 9, 3])[0]
        status = "cancelled" if rng.random() < 0.07 else "delivered"
        returned = (sum(rng.random() < return_probability for _ in range(quantity))
                    if status == "delivered" else 0)
        discount_bps = rng.choice([0, 0, 0, 500, 1000, 1500])
        unit_cents = (price * (10000 - discount_bps) + 5000) // 10000
        rows.append({
            "order_id": f"O{i + 1:05d}",
            "order_date": (date(2025, 1, 1) + timedelta(days=rng.randrange(365))).isoformat(),
            "sku": sku, "product": name, "category": category,
            "quantity": quantity, "returned_quantity": returned,
            "unit_cents": unit_cents, "status": status,
        })
    # Erros intencionais para demonstrar a auditoria. IDs de erros são distintos.
    for i, (field, value) in enumerate([
        ("quantity", -1), ("returned_quantity", 99), ("unit_cents", "inválido"),
        ("order_date", "2025-02-30"), ("sku", "DESCONHECIDO"),
        ("status", "pending"), ("quantity", 1.5), ("order_id", ""),
        ("order_date", "2026-01-01"), ("unit_cents", float("inf")),
        ("product", "Produto incorreto"), ("unit_cents", 0),
    ]):
        bad = dict(rows[20 + i], order_id=f"BAD{i:02d}")
        bad[field] = value
        rows.append(bad)
    # Dois IDs conflitantes: ambas as versões serão rejeitadas.
    for i in [50, 51]:
        rows.append(dict(rows[i], unit_cents=rows[i]["unit_cents"] + 1))
    rows.extend(dict(row) for row in rows[:36])
    return pd.DataFrame(rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("data/raw/orders.csv"))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--orders", type=int, default=3600)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    frame = generate(args.seed, args.orders)
    frame.to_csv(args.output, index=False)
    print(f"{len(frame)} linhas sintéticas salvas em {args.output}")
