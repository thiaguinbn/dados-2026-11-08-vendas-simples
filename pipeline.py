"""Gera, valida, agrega em SQL e publica resultados locais reproduzíveis."""

import argparse
import hashlib
import json
import re
import sqlite3
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from clean_data import clean_orders
from generate_data import generate

ROOT = Path(__file__).resolve().parent


def query_metrics(orders, database):
    """SQL é a fonte das métricas usadas no relatório e nos gráficos."""
    sql = (ROOT / "metrics.sql").read_text(encoding="utf-8")
    parts = re.split(r"-- name: (\w+)\n", sql)
    with sqlite3.connect(database) as connection:
        orders.to_sql("orders", connection, if_exists="replace", index=False)
        return {parts[i]: pd.read_sql_query(parts[i + 1], connection)
                for i in range(1, len(parts), 2)}


def brl(cents):
    value = f"{cents / 100:,.2f}"
    return "R$ " + value.replace(",", "_").replace(".", ",").replace("_", ".")


def plot_overview(tables, path):
    monthly, products = tables["monthly"], tables["products"]
    fig, axes = plt.subplots(1, 2, figsize=(13, 5), layout="constrained")
    fig.patch.set_facecolor("#f4f6f9")
    for ax in axes:
        ax.set_facecolor("#f4f6f9")
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", color="#dce2eb", zorder=0)
    axes[0].bar(monthly["month"].str[-2:], monthly["net_cents"] / 100000,
                color="#17468b", zorder=3, label="Após devoluções")
    axes[0].bar(monthly["month"].str[-2:], monthly["refund_cents"] / 100000,
                bottom=monthly["net_cents"] / 100000, color="#e8a24a", zorder=3,
                label="Valor devolvido")
    axes[0].set(title="Receita por mês • 2025", xlabel="Mês da venda",
                ylabel="R$ mil • após descontos")
    axes[0].legend(frameon=False, fontsize=9, loc="lower left",
                   bbox_to_anchor=(0, 1.0), ncol=2, borderaxespad=0)
    axes[0].title.set_y(1.09)
    ranking = products.sort_values("unit_return_pct")
    bars = axes[1].barh(ranking["product"], ranking["unit_return_pct"],
                        color="#e8a24a", zorder=3)
    axes[1].grid(False)
    axes[1].set(title="Devoluções por produto", xlabel="Unidades devolvidas / vendidas (%)")
    axes[1].bar_label(bars, fmt="%.1f%%", padding=4, fontsize=9)
    axes[1].set_xlim(0, max(ranking["unit_return_pct"].max() * 1.2, 1))
    fig.suptitle("Vendas sob a lupa  |  DADOS SINTÉTICOS", fontsize=16, fontweight="bold")
    fig.savefig(path, dpi=150, metadata={"Software": "vendas-devolucoes"})
    plt.close(fig)


def build_report(tables, audit, provenance):
    summary = tables["summary"].iloc[0]
    products = tables["products"]
    top = products.iloc[0]
    highest_return = products.sort_values("unit_return_pct", ascending=False).iloc[0]
    refund_share = 100 * highest_return["refund_cents"] / summary["refund_cents"] if summary["refund_cents"] else 0
    rows = "\n".join(
        f"| {r.product} | {r.orders} | {brl(r.net_cents)} | {r.unit_return_pct:.2f}% | {brl(r.refund_cents)} |"
        for r in products.itertuples())
    audit_rows = "\n".join(f"| `{key}` | {value} |" for key, value in audit.items())
    return f"""# Relatório — vendas e devoluções

> **Estudo com dados inteiramente sintéticos.** Não representa uma empresa, uma pesquisa de mercado ou uma estimativa de comportamento real.

## Pergunta

Quais produtos geram mais receita e quanto as devoluções reduzem esse valor?

## Indicadores calculados

| Indicador | Resultado |
| --- | ---: |
| Pedidos entregues válidos | {int(summary['orders'])} |
| Unidades vendidas | {int(summary['units_sold'])} |
| Unidades devolvidas | {int(summary['units_returned'])} |
| Valor vendido após descontos, antes das devoluções | {brl(summary['gross_cents'])} |
| Valor das devoluções | {brl(summary['refund_cents'])} |
| Receita de mercadorias após devoluções | {brl(summary['net_cents'])} |
| Taxa de devolução por unidade | {summary['unit_return_pct']:.2f}% |
| Parcela do valor vendido devolvida | {summary['revenue_refund_pct']:.2f}% |
| Ticket médio antes de devoluções | {brl(summary['gross_ticket_cents'])} |

![Receita mensal e taxa de devolução por produto](overview.png)

## Produtos

| Produto | Pedidos | Receita após devoluções | Devoluções por unidade | Valor devolvido |
| --- | ---: | ---: | ---: | ---: |
{rows}

## Interpretação

- **{top['product']}** lidera a receita após devoluções nesta simulação, com {brl(top['net_cents'])}.
- **{highest_return['product']}** tem a maior taxa de devolução por unidade ({highest_return['unit_return_pct']:.2f}%) e responde por {refund_share:.2f}% do valor total devolvido.
- Em uma operação real, esse segundo resultado justificaria investigar motivos de devolução, fornecedor e especificações do produto. A base não contém essas informações; portanto, não permite atribuir uma causa.
- As diferenças entre produtos foram deliberadamente inseridas no gerador. Recuperá-las demonstra o funcionamento do pipeline; não é uma descoberta sobre consumidores reais.

## Auditoria de qualidade

| Etapa | Linhas |
| --- | ---: |
{audit_rows}

As categorias após `input_rows` são exclusivas e somam exatamente a entrada. Duplicados exatos são removidos primeiro; IDs com versões diferentes são integralmente rejeitados; regras inválidas são quarentenadas; cancelados válidos não entram na receita.

## Definições e limites

- Cada pedido tem um único produto. Devoluções podem ser parciais.
- Valores são armazenados em centavos inteiros; descontos são arredondados por unidade no gerador antes da agregação.
- `gross_cents` significa valor de mercadorias após desconto e antes de devoluções; `net_cents = gross_cents - refund_cents`. Não é lucro nem receita líquida contábil: impostos, frete, custos e taxas não estão incluídos.
- Taxa por unidade = soma das unidades devolvidas / soma das unidades vendidas. Não é a média simples das taxas dos pedidos nem a fração de pedidos com devolução.
- Os reembolsos são atribuídos ao mês da venda original. Não existe data de reembolso; o gráfico não representa fluxo de caixa.
- Todos os pedidos simulados têm desfecho conhecido. O período é restrito a 2025; o gerador não modela sazonalidade real.
- Sem clientes, aquisição, custos ou estoque, não se pode calcular retenção, CAC, LTV ou margem.

## Reprodução e rastreabilidade

- Semente: `{provenance['seed']}`; pedidos-base: `{provenance['base_orders']}`.
- SHA-256 do CSV bruto: `{provenance['raw_sha256']}`.
- SHA-256 do SQL: `{provenance['sql_sha256']}`.
- Métricas completas: [metrics.json](metrics.json); tabelas: [products.csv](products.csv) e [monthly.csv](monthly.csv); auditoria: [quality.json](quality.json).

Reexecute com `python pipeline.py`. Veja o README para instalar dependências e rodar os testes. O uso de outra semente cria outra simulação e pode mudar os resultados.
"""


def run(seed=42, orders=3600, output_dir=None):
    output = Path(output_dir) if output_dir else ROOT / "reports"
    output.mkdir(parents=True, exist_ok=True)
    raw_path = ROOT / "data/raw/orders.csv"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    generate(seed, orders).to_csv(raw_path, index=False)
    # CSV real é relido: a validação precisa funcionar após serialização.
    cleaned, audit, quarantine = clean_orders(pd.read_csv(raw_path))
    if cleaned.empty:
        raise ValueError("Nenhum pedido entregue válido: análise não executada.")
    processed = ROOT / "data/processed"
    processed.mkdir(parents=True, exist_ok=True)
    cleaned.to_csv(processed / "orders.csv", index=False)
    quarantine.to_csv(processed / "quarantine.csv", index=False)
    tables = query_metrics(cleaned, processed / "sales.sqlite")
    for name in ["products", "monthly"]:
        tables[name].to_csv(output / f"{name}.csv", index=False)
    provenance = {
        "data_kind": "synthetic", "seed": seed, "base_orders": orders,
        "raw_sha256": hashlib.sha256(raw_path.read_bytes()).hexdigest(),
        "sql_sha256": hashlib.sha256((ROOT / "metrics.sql").read_bytes()).hexdigest(),
    }
    summary = json.loads(tables["summary"].to_json(orient="records"))[0]
    (output / "metrics.json").write_text(json.dumps(
        {"provenance": provenance, "summary": summary}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "quality.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    plot_overview(tables, output / "overview.png")
    (output / "RELATORIO.md").write_text(build_report(tables, audit, provenance), encoding="utf-8")
    print(json.dumps({"summary": summary, "quality": audit}, ensure_ascii=False, indent=2))
    print(f"Relatório: {output / 'RELATORIO.md'}")
    return tables, audit


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--orders", type=int, default=3600)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    run(args.seed, args.orders, args.output_dir)
