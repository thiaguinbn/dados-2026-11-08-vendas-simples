import matplotlib.pyplot as plt
import pandas as pd

# 1. Ler o arquivo e calcular o valor de cada venda.
vendas = pd.read_csv("vendas.csv")
vendas["faturamento"] = vendas["quantidade"] * vendas["preco_unitario"]

print("Primeiras linhas:")
print(vendas.head())
print(f"\nFaturamento total: R$ {vendas['faturamento'].sum():.2f}")
print(f"Unidades vendidas: {vendas['quantidade'].sum()}")

# 2. Somar a quantidade e o faturamento de cada produto.
resumo = vendas.groupby("produto")[["quantidade", "faturamento"]].sum()
resumo = resumo.sort_values("faturamento", ascending=False)
print("\nResumo por produto:")
print(resumo)
print(f"\nProduto com maior faturamento: {resumo.index[0]}")

# 3. Criar e salvar um gráfico de barras.
resumo["faturamento"].plot(kind="bar", color="#3568a8", rot=0)
plt.title("Faturamento por produto — dados fictícios")
plt.xlabel("Produto")
plt.ylabel("Faturamento (R$)")
plt.tight_layout()
plt.savefig("grafico_vendas.png", dpi=150)
plt.close()
print("Gráfico salvo em grafico_vendas.png")
