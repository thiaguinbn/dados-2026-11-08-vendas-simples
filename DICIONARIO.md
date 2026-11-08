# Dicionário e regras dos dados

Fonte: gerador local `generate_data.py`; **100% sintética**, sem registros de pessoas ou empresas reais. A distribuição foi escolhida apenas para exercitar o pipeline. Período: 2025.

## Entrada — `data/raw/orders.csv`

| Campo | Tipo esperado | Regra |
| --- | --- | --- |
| `order_id` | texto | `O` seguido de cinco dígitos; um pedido por linha |
| `order_date` | data ISO | Entre 2025-01-01 e 2025-12-31 |
| `sku` | texto | Código P01 a P06 do catálogo |
| `product` | texto | Nome consistente com o SKU |
| `category` | texto | Categoria consistente com o SKU |
| `quantity` | inteiro | Entre 1 e 1.000 |
| `returned_quantity` | inteiro | Entre zero e a quantidade vendida; cancelados exigem zero |
| `unit_cents` | inteiro | Preço unitário após desconto, entre 1 e 100.000.000 centavos |
| `status` | texto | `delivered` ou `cancelled` |

`unit_cents` já contém o desconto. O gerador aplica desconto de 0%, 5%, 10% ou 15%, com arredondamento half-up em centavos por unidade. `quantity` é a quantidade original, antes das devoluções. Não há frete, impostos, custos, múltiplos itens, identificadores de clientes ou data de reembolso.

## Catálogo

| SKU | Produto | Categoria | Preço de lista |
| --- | --- | --- | ---: |
| P01 | Teclado | Periféricos | R$ 159,90 |
| P02 | Mouse | Periféricos | R$ 89,90 |
| P03 | Headset | Áudio | R$ 229,90 |
| P04 | Caixa de som | Áudio | R$ 179,90 |
| P05 | Webcam | Vídeo | R$ 199,90 |
| P06 | Suporte de notebook | Acessórios | R$ 119,90 |

## Campos derivados

| Campo | Definição |
| --- | --- |
| `gross_cents` | `quantity * unit_cents`, após desconto e antes de devolução |
| `refund_cents` | `returned_quantity * unit_cents` |
| `net_cents` | `gross_cents - refund_cents` |
| `unit_return_pct` | `100 * SUM(returned_quantity) / SUM(quantity)` |
| `revenue_refund_pct` | `100 * SUM(refund_cents) / SUM(gross_cents)` |
| `gross_ticket_cents` | `SUM(gross_cents) / COUNT(pedidos entregues válidos)` |

Nomes `gross`/`net` são convenções internas de mercadorias; não representam faturamento bruto tributário nem receita líquida contábil.

## Ordem das decisões de limpeza

1. Exigir todas as colunas de entrada e selecionar apenas essas colunas.
2. Remover linhas integralmente duplicadas.
3. Rejeitar todas as versões de um `order_id` ainda repetido.
4. Rejeitar linhas que violem qualquer regra de esquema ou negócio.
5. Excluir cancelados válidos dos indicadores.
6. Calcular valores apenas nos pedidos entregues válidos.

Os três tipos de rejeição são preservados em `data/processed/quarantine.csv`, com `reason`. Cancelados válidos são contados na auditoria, sem serem considerados erro de dados. O validador rejeita a linha inválida integralmente; não tenta adivinhar valores ausentes.
