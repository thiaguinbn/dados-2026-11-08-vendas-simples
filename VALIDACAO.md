# Validação executada

Ambiente: Python 3.12.14, pandas 2.2.3, NumPy 2.3.5 e Matplotlib 3.10.8. Execução local em 08/11/2026. Não foi configurada execução de CI no GitHub.

```text
python -m unittest discover -v
Ran 13 tests
OK
```

As verificações cobrem devolução parcial e total, cancelamentos, duplicados exatos, conflito de versões, dados inválidos, entrada vazia, esquema ausente, reprodução da base com semente fixa, receita por cálculo manual, taxa ponderada por unidades, conciliação das agregações e meses sem vendas.

O pipeline também foi executado com `python pipeline.py`. Resultado: 3.650 linhas de entrada, 3.352 pedidos entregues válidos, R$ 684.200,47 em mercadorias após devoluções. Os totais mensais e por produto são reconciliados nos testes SQL.

O gráfico foi inspecionado visualmente. Os resultados e hashes desta execução estão em `reports/`. A validação local não equivale a uma garantia sobre outros ambientes ou dados externos; o projeto foi validado com a base sintética e as regras descritas no dicionário.
