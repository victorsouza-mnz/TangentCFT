#!/usr/bin/env python3
"""
Script simples para selecionar aleatoriamente 20 questões que contenham pelo menos 1 fórmula
e salvar em JSON - conforme solicitado.
"""

import os
import sys
import json
import random
import re
from datetime import datetime

# Adicionar o diretório raiz ao path (precisa subir 2 níveis: assert -> app -> root)
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(root_dir)

from services.elasticsearch_service import ElasticsearchService


def buscar_formulas_por_ids(elastic_service, formula_ids):
    """
    Busca fórmulas no índice de fórmulas pelos IDs.

    Args:
        elastic_service: Instância do ElasticsearchService
        formula_ids: Lista de IDs das fórmulas

    Returns:
        Dict mapeando formula_id -> {"slt_text": ..., "opt_text": ...}
    """
    if not formula_ids:
        return {}

    # Query para buscar múltiplas fórmulas pelos IDs
    query = {
        "query": {"terms": {"formula_id": formula_ids}},
        "size": len(formula_ids),
        "_source": ["formula_id", "slt_text", "opt_text"],
    }

    try:
        response = elastic_service.es.search(
            index=elastic_service.formulas_index_name, body=query
        )

        # Criar mapeamento formula_id -> {"slt_text": ..., "opt_text": ...}
        formula_map = {}
        for hit in response["hits"]["hits"]:
            source = hit["_source"]
            formula_map[source["formula_id"]] = {
                "slt_text": source.get("slt_text", ""),
                "opt_text": source.get("opt_text", ""),
            }

        return formula_map

    except Exception as e:
        print(f"⚠️ Erro ao buscar fórmulas: {str(e)}")
        return {}


def extrair_ids_formulas(texto):
    """
    Extrai os IDs das fórmulas do texto HTML.

    Args:
        texto: Texto HTML com spans de fórmulas

    Returns:
        Lista de IDs das fórmulas encontradas
    """
    # Regex para encontrar <span class="math-container" id="XXXXX">
    pattern = r'<span class="math-container" id="(\d+)">'
    matches = re.findall(pattern, texto)
    return matches


def substituir_formulas_no_texto(texto, formula_map, usar_opt=False):
    """
    Substitui os spans de fórmulas pelo conteúdo slt_text ou opt_text.

    Args:
        texto: Texto HTML original
        formula_map: Mapeamento formula_id -> {"slt_text": ..., "opt_text": ...}
        usar_opt: Se True, usa opt_text; se False, usa slt_text

    Returns:
        Texto com fórmulas substituídas
    """

    def substituir_span(match):
        formula_id = match.group(1)
        formula_data = formula_map.get(formula_id, {})

        if usar_opt:
            formula_text = formula_data.get(
                "opt_text", f"[FORMULA_ID_{formula_id}_OPT_NOT_FOUND]"
            )
        else:
            formula_text = formula_data.get(
                "slt_text", f"[FORMULA_ID_{formula_id}_SLT_NOT_FOUND]"
            )

        return formula_text

    # Regex para encontrar e substituir todo o span
    pattern = r'<span class="math-container" id="(\d+)">.*?</span>'
    texto_processado = re.sub(pattern, substituir_span, texto)

    return texto_processado


def main():
    """Função principal - seleciona 20 questões com fórmulas e salva em JSON."""

    print("🔍 Conectando ao Elasticsearch...")
    elastic_service = ElasticsearchService()

    # Verificar se os índices existem
    if not elastic_service.posts_index_exists():
        print("❌ Erro: Índice 'posts' não encontrado!")
        print(
            "Certifique-se de que o Elasticsearch está rodando e os dados foram indexados."
        )
        return

    if not elastic_service.formulas_index_exists():
        print("❌ Erro: Índice 'formulas' não encontrado!")
        print(
            "Certifique-se de que o Elasticsearch está rodando e as fórmulas foram indexadas."
        )
        return

    print("📊 Buscando questões com pelo menos 1 fórmula...")

    # Query para buscar questões com fórmulas
    query = {
        "query": {"range": {"formulas_count": {"gte": 1}}},  # Pelo menos 1 fórmula
        "size": 1000,  # Buscar 1000 para ter boa variedade
        "_source": [
            "post_id",
            "text",
            "text_without_html",
            "text_latex_search",
            "formulas_count",
            "formulas_latex",
        ],
    }

    try:
        response = elastic_service.es.search(
            index=elastic_service.posts_index_name, body=query
        )

        questoes_encontradas = [hit["_source"] for hit in response["hits"]["hits"]]
        print(f"✅ Encontradas {len(questoes_encontradas)} questões com fórmulas")

        if len(questoes_encontradas) == 0:
            print("❌ Nenhuma questão com fórmulas foi encontrada!")
            return

        # Selecionar 20 aleatoriamente
        quantidade_selecionar = min(100, len(questoes_encontradas))
        questoes_selecionadas = random.sample(
            questoes_encontradas, quantidade_selecionar
        )

        print(f"🎯 Selecionadas {quantidade_selecionar} questões aleatoriamente")
        print("🔄 Processando fórmulas...")

        # Coletar todos os IDs de fórmulas das questões selecionadas
        todos_ids_formulas = set()
        for questao in questoes_selecionadas:
            texto = questao.get("text", "")
            ids_formulas = extrair_ids_formulas(texto)
            todos_ids_formulas.update(ids_formulas)

        print(f"📝 Encontrados {len(todos_ids_formulas)} IDs únicos de fórmulas")

        # Buscar as fórmulas no Elasticsearch (agora busca tanto slt_text quanto opt_text)
        formula_map = buscar_formulas_por_ids(elastic_service, list(todos_ids_formulas))
        print(f"✅ Recuperadas {len(formula_map)} fórmulas do índice")

        # Processar cada questão substituindo as fórmulas (SLT e OPT)
        for questao in questoes_selecionadas:
            texto_original = questao.get("text", "")

            # Substituir com SLT
            texto_com_slt = substituir_formulas_no_texto(
                texto_original, formula_map, usar_opt=False
            )
            questao["text_with_formulas_replaced"] = texto_com_slt

            # Substituir com OPT
            texto_com_opt = substituir_formulas_no_texto(
                texto_original, formula_map, usar_opt=True
            )
            questao["text_with_opt_formulas_replaced"] = texto_com_opt

        # Preparar dados para salvar
        dados_json = {
            "metadata": {
                "total_questoes_selecionadas": len(questoes_selecionadas),
                "criterio": "Questões com pelo menos 1 fórmula",
                "metodo_selecao": "Aleatório",
                "data_geracao": datetime.now().isoformat(),
                "fonte": "Elasticsearch",
                "formulas_processadas": len(formula_map),
                "formulas_nao_encontradas": len(todos_ids_formulas) - len(formula_map),
                "campos_gerados": [
                    "text_with_formulas_replaced (usando slt_text)",
                    "text_with_opt_formulas_replaced (usando opt_text)",
                ],
            },
            "questoes": questoes_selecionadas,
        }

        # Salvar em JSON
        nome_arquivo = "questoes_formulas_selecionadas.json"
        caminho_arquivo = os.path.join(root_dir, nome_arquivo)

        with open(caminho_arquivo, "w", encoding="utf-8") as f:
            json.dump(dados_json, f, ensure_ascii=False, indent=2)

        print(f"💾 Arquivo salvo: {caminho_arquivo}")

        # Mostrar estatísticas rápidas
        print("\n📈 ESTATÍSTICAS:")
        print(f"• Total de questões: {len(questoes_selecionadas)}")
        print(f"• Fórmulas únicas encontradas: {len(todos_ids_formulas)}")
        print(f"• Fórmulas recuperadas do índice: {len(formula_map)}")
        print(
            f"• Fórmulas não encontradas: {len(todos_ids_formulas) - len(formula_map)}"
        )

        # Contar fórmulas por questão
        contagem_formulas = {}
        for questao in questoes_selecionadas:
            count = questao.get("formulas_count", 0)
            contagem_formulas[count] = contagem_formulas.get(count, 0) + 1

        print("• Distribuição de fórmulas:")
        for count in sorted(contagem_formulas.keys()):
            print(f"  - {count} fórmulas: {contagem_formulas[count]} questões")

        print(
            f"\n✅ Concluído! 20 questões com fórmulas processadas salvas em '{nome_arquivo}'"
        )
        print("📄 Campos gerados:")
        print("   - text_with_formulas_replaced (usando slt_text)")
        print("   - text_with_opt_formulas_replaced (usando opt_text)")

    except Exception as e:
        print(f"❌ Erro ao buscar questões: {str(e)}")


if __name__ == "__main__":
    main()
