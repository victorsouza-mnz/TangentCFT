import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

# Configurações iniciais
sns.set(style="whitegrid", font_scale=1.1)
plt.rcParams["font.family"] = "DejaVu Sans"
plt.rcParams["axes.titlepad"] = 15
plt.rcParams["axes.labelpad"] = 10

# Carregar os dados
df = pd.read_csv("./app/assert/resultados_experimento.csv")


# Função para calcular hit rate no top K
def calcular_hit_rate_top_k(positions_str, k=10):
    """
    Calcula a taxa de acerto considerando apenas posições <= k
    positions_str: string com lista de posições, ex: "[1, 2, 5, 1, 10]"
    """
    import ast

    try:
        positions = ast.literal_eval(positions_str)
        if isinstance(positions, list):
            # Contar quantas posições são <= k
            hits_top_k = sum(1 for pos in positions if pos <= k)
            return hits_top_k
        else:
            # Se não é uma lista, pode ser um valor único
            return 1 if positions <= k else 0
    except:
        return 0


# Calcular hit rate top 10 para cada linha
df["Found_in_Top_10"] = df["All_Positions"].apply(
    lambda x: calcular_hit_rate_top_k(x, k=10)
)
df["Hit_Rate_Top10_Percent"] = (df["Found_in_Top_10"] / df["Total_Cases"]) * 100

# Mapeamento para nomes amigáveis
mod_map = {
    "text_with_formulas_replaced": "Alterações Pequenas em Fórmulas",
    "text_lightly_modified": "Modificação Textual Leve",
    "text_semantically_modified": "Modificação Textual Severa Preservando Semântica",
    "text_natural_language": "Linguagem Natural",
}

# Definir ordem específica dos algoritmos
algoritmos_ordenados = [
    "Texto Puro",
    "Texto + Desambiguador",
    "Texto + Vetor de Formula",
]

# Lista das estratégias na ordem desejada
estrategias = [
    "text_with_formulas_replaced",
    "text_lightly_modified",
    "text_semantically_modified",
    "text_natural_language",
]

# Criar os 4 gráficos separadamente
for idx, estrategia in enumerate(estrategias):
    # Criar nova figura para cada estratégia
    plt.figure(figsize=(14, 10))

    # Filtrar dados para a estratégia atual
    df_estrategia = df[df["Modificação_Base"] == estrategia].copy()

    # Criar coluna para diferenciar completa vs truncada
    df_estrategia["Tipo"] = df_estrategia["Is_Truncated"].apply(
        lambda x: "Truncada" if x else "Completa"
    )

    # Converter coluna Algoritmo para categórico ordenado
    df_estrategia["Algoritmo"] = pd.Categorical(
        df_estrategia["Algoritmo"], categories=algoritmos_ordenados, ordered=True
    )

    # Agrupar dados
    df_grouped = (
        df_estrategia.groupby(["Algoritmo", "Tipo"])["Hit_Rate_Top10_Percent"]
        .mean()
        .reset_index()
    )

    # Criar o gráfico de barras
    ax = sns.barplot(
        x="Algoritmo",
        y="Hit_Rate_Top10_Percent",
        hue="Tipo",
        data=df_grouped,
        palette=["#1f77b4", "#ff7f0e"],  # Azul para completa, laranja para truncada
        errwidth=1.0,
        capsize=0.05,
        saturation=0.85,
        dodge=True,
    )

    # Configurações do gráfico
    plt.title(
        f"Taxa de Acerto no Top 10 - {mod_map[estrategia]}",
        fontsize=16,
        fontweight="bold",
        pad=20,
    )
    plt.xlabel("Algoritmos", fontsize=14)
    plt.ylabel("Taxa de Acerto no Top 10 (%)", fontsize=14)
    plt.ylim(0, 105)

    # Adicionar linhas de referência
    for y in range(20, 120, 20):
        plt.axhline(y, color="gray", linestyle="--", alpha=0.3, zorder=0)

    # Rotacionar rótulos do eixo X
    plt.xticks(rotation=45, ha="right")

    # Configurar legenda
    plt.legend(
        title="Tipo de Texto",
        loc="upper right",
        frameon=True,
        framealpha=0.9,
        fontsize=12,
        title_fontsize=12,
    )

    # Adicionar valores nas barras
    for container in ax.containers:
        ax.bar_label(container, fmt="%.1f%%", fontsize=11, rotation=0)

    # Ajustar layout
    plt.tight_layout()

    # Salvar cada gráfico com nome específico
    nome_arquivo = estrategia.replace("text_", "").replace("_", "_")
    plt.savefig(f"top10_{nome_arquivo}.png", dpi=300, bbox_inches="tight")
    plt.show()

# Criar também um gráfico adicional mostrando um resumo comparativo
plt.figure(figsize=(16, 10))

# Preparar dados para o gráfico resumo
df_resumo = []
for estrategia in estrategias:
    df_estrategia = df[df["Modificação_Base"] == estrategia].copy()

    # Calcular média para completa e truncada
    completa = df_estrategia[df_estrategia["Is_Truncated"] == False][
        "Hit_Rate_Top10_Percent"
    ].mean()
    truncada = df_estrategia[df_estrategia["Is_Truncated"] == True][
        "Hit_Rate_Top10_Percent"
    ].mean()

    df_resumo.append(
        {
            "Estratégia": mod_map[estrategia],
            "Completa": completa,
            "Truncada": truncada,
            "Diferença": completa - truncada,
        }
    )

df_resumo = pd.DataFrame(df_resumo)

# Criar gráfico de barras lado a lado
x = np.arange(len(df_resumo))
width = 0.35

fig, ax = plt.subplots(figsize=(16, 10))
bars1 = ax.bar(
    x - width / 2,
    df_resumo["Completa"],
    width,
    label="Completa",
    color="#1f77b4",
    alpha=0.8,
)
bars2 = ax.bar(
    x + width / 2,
    df_resumo["Truncada"],
    width,
    label="Truncada",
    color="#ff7f0e",
    alpha=0.8,
)

# Configurações
ax.set_xlabel("Estratégias de Modificação", fontsize=14)
ax.set_ylabel("Taxa de Acerto Média no Top 10 (%)", fontsize=14)
ax.set_title(
    "Resumo Comparativo - Impacto da Truncagem por Estratégia (Top 10)",
    fontsize=16,
    fontweight="bold",
    pad=20,
)
ax.set_xticks(x)
ax.set_xticklabels(df_resumo["Estratégia"], rotation=45, ha="right")
ax.legend(fontsize=12)
ax.set_ylim(0, 105)

# Adicionar linhas de referência
for y in range(20, 120, 20):
    ax.axhline(y, color="gray", linestyle="--", alpha=0.3, zorder=0)


# Adicionar valores nas barras
def autolabel(bars):
    for bar in bars:
        height = bar.get_height()
        ax.annotate(
            f"{height:.1f}%",
            xy=(bar.get_x() + bar.get_width() / 2, height),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=11,
        )


autolabel(bars1)
autolabel(bars2)

plt.tight_layout()
plt.savefig("resumo_comparativo_estrategias_top10.png", dpi=300, bbox_inches="tight")
plt.show()
