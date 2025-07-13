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

# Criar coluna combinada de modificação + truncagem
df["Categoria"] = df["Modificação_Base"] + "_" + df["Is_Truncated"].astype(str)

# Mapeamento para nomes amigáveis
mod_map = {
    "text_with_formulas_replaced": "Fórmulas Substituídas",
    "text_lightly_modified": "Modificação Leve",
    "text_semantically_modified": "Modificação Semântica",
    "text_natural_language": "Linguagem Natural",
}


# Criar rótulos completos
def criar_rotulo(row):
    base = mod_map.get(row["Modificação_Base"], row["Modificação_Base"])
    return f"{base}\n{'Truncada' if row['Is_Truncated'] else 'Completa'}"


df["Categoria_Rotulo"] = df.apply(criar_rotulo, axis=1)


# Função para expandir as posições de hits
def expandir_posicoes_hits(row):
    """
    Expande as posições dos hits para criar dados individuais de cada teste
    """
    import ast

    try:
        positions = ast.literal_eval(row["All_Positions"])
        if isinstance(positions, list):
            # Para cada posição encontrada, criar uma entrada
            expanded_data = []
            for i, pos in enumerate(positions):
                expanded_data.append(
                    {
                        "Algoritmo": row["Algoritmo"],
                        "Categoria": row["Categoria"],
                        "Categoria_Rotulo": row["Categoria_Rotulo"],
                        "Teste_ID": i + 1,
                        "Posicao_Hit": pos,
                        "Found": 1,
                    }
                )

            # Para os testes que não tiveram hit, adicionar posição 0
            total_tests = int(row["Total_Cases"])
            hits_found = len(positions)
            for i in range(hits_found, total_tests):
                expanded_data.append(
                    {
                        "Algoritmo": row["Algoritmo"],
                        "Categoria": row["Categoria"],
                        "Categoria_Rotulo": row["Categoria_Rotulo"],
                        "Teste_ID": i + 1,
                        "Posicao_Hit": 0,  # 0 = não encontrado
                        "Found": 0,
                    }
                )

            return expanded_data
        else:
            # Caso seja um valor único
            expanded_data = []
            expanded_data.append(
                {
                    "Algoritmo": row["Algoritmo"],
                    "Categoria": row["Categoria"],
                    "Categoria_Rotulo": row["Categoria_Rotulo"],
                    "Teste_ID": 1,
                    "Posicao_Hit": positions if positions <= 10 else 0,
                    "Found": 1 if positions <= 10 else 0,
                }
            )

            # Adicionar os testes restantes como não encontrados
            total_tests = int(row["Total_Cases"])
            for i in range(1, total_tests):
                expanded_data.append(
                    {
                        "Algoritmo": row["Algoritmo"],
                        "Categoria": row["Categoria"],
                        "Categoria_Rotulo": row["Categoria_Rotulo"],
                        "Teste_ID": i + 1,
                        "Posicao_Hit": 0,
                        "Found": 0,
                    }
                )

            return expanded_data
    except:
        # Em caso de erro, assumir que todos os testes falharam
        expanded_data = []
        total_tests = int(row["Total_Cases"])
        for i in range(total_tests):
            expanded_data.append(
                {
                    "Algoritmo": row["Algoritmo"],
                    "Categoria": row["Categoria"],
                    "Categoria_Rotulo": row["Categoria_Rotulo"],
                    "Teste_ID": i + 1,
                    "Posicao_Hit": 0,
                    "Found": 0,
                }
            )
        return expanded_data


# Expandir todos os dados
expanded_data = []
for _, row in df.iterrows():
    expanded_data.extend(expandir_posicoes_hits(row))

# Converter para DataFrame
df_expanded = pd.DataFrame(expanded_data)

# Obter lista de algoritmos únicos
algoritmos_unicos = df_expanded["Algoritmo"].unique()

# Cores para diferentes tipos de modificação
cores_categoria = {
    "Fórmulas Substituídas\nCompleta": "#1f77b4",
    "Fórmulas Substituídas\nTruncada": "#aec7e8",
    "Modificação Leve\nCompleta": "#ff7f0e",
    "Modificação Leve\nTruncada": "#ffbb78",
    "Modificação Semântica\nCompleta": "#2ca02c",
    "Modificação Semântica\nTruncada": "#98df8a",
    "Linguagem Natural\nCompleta": "#d62728",
    "Linguagem Natural\nTruncada": "#ff9896",
}

# Gerar um scatter plot para cada algoritmo
for algoritmo in algoritmos_unicos:
    plt.figure(figsize=(16, 10))

    # Filtrar dados para o algoritmo atual
    df_alg = df_expanded[df_expanded["Algoritmo"] == algoritmo].copy()

    # Criar ID sequencial para este algoritmo
    df_alg = df_alg.reset_index(drop=True)
    df_alg["Teste_Sequencial"] = range(len(df_alg))

    # Separar hits encontrados e não encontrados
    df_hits = df_alg[df_alg["Posicao_Hit"] > 0].copy()
    df_misses = df_alg[df_alg["Posicao_Hit"] == 0].copy()

    # Plotar hits encontrados (posição > 0)
    for categoria in df_hits["Categoria_Rotulo"].unique():
        df_cat = df_hits[df_hits["Categoria_Rotulo"] == categoria]
        plt.scatter(
            df_cat["Teste_Sequencial"],
            df_cat["Posicao_Hit"],
            c=cores_categoria.get(categoria, "#333333"),
            label=f"{categoria} (Hit)",
            alpha=0.8,
            s=60,
            edgecolors="black",
            linewidth=0.5,
        )

    # Plotar misses (posição = 0) na parte inferior
    for categoria in df_misses["Categoria_Rotulo"].unique():
        df_cat = df_misses[df_misses["Categoria_Rotulo"] == categoria]
        plt.scatter(
            df_cat["Teste_Sequencial"],
            df_cat["Posicao_Hit"],
            c=cores_categoria.get(categoria, "#333333"),
            label=f"{categoria} (Miss)",
            alpha=0.4,
            s=40,
            marker="x",
            linewidth=2,
        )

    # Configurações do gráfico
    plt.xlabel("ID do Teste Individual")
    plt.ylabel("Posição do Hit")
    plt.title(f"Distribuição das Posições dos Hits - Algoritmo: {algoritmo}")

    # Inverter eixo Y (10 no topo, 0 na base)
    plt.ylim(-0.5, 10.5)
    plt.gca().invert_yaxis()

    # Configurar ticks do eixo Y
    plt.yticks(range(0, 11))

    # Grid
    plt.grid(True, alpha=0.3)

    # Adicionar linha horizontal para separar hits de misses
    plt.axhline(y=0.5, color="red", linestyle="--", alpha=0.5, linewidth=1)

    # Legenda
    plt.legend(bbox_to_anchor=(1.05, 1), loc="upper left", fontsize="small")

    # Salvar gráfico
    filename = f"scatter_plot_{algoritmo.replace(' ', '_').replace('/', '_')}.png"
    plt.tight_layout()
    plt.savefig(filename, dpi=300, bbox_inches="tight")
    plt.show()

    print(f"Gráfico salvo: {filename}")

print("Todos os scatter plots foram gerados!")
