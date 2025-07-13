#!/usr/bin/env python3
"""
Script para testar a performance das diferentes rotas de busca
usando as queries da base de dados de teste
"""

import json
import requests
import time
from typing import Dict, List, Any, Optional
import argparse
import re


class SearchTester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results = {}

    def load_test_data(self, json_file: str) -> List[Dict]:
        """Carrega os dados de teste do arquivo JSON"""
        with open(json_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def truncate_query_preserving_formulas(
        self, query: str, max_chars: int = 50
    ) -> str:
        """
        Trunca a query para max_chars caracteres, mas preserva fórmulas completas.
        Detecta fórmulas LaTeX (entre $ ou $$) e MathML (entre tags).
        """
        if len(query) <= max_chars:
            return query

        # Padrões para detectar fórmulas
        latex_patterns = [
            r"\$\$.*?\$\$",  # $$formula$$
            r"\$.*?\$",  # $formula$
        ]

        mathml_patterns = [
            r"<math.*?</math>",
            r"<mml:math.*?</mml:math>",
        ]

        all_patterns = latex_patterns + mathml_patterns

        # Encontra todas as fórmulas na query
        formulas = []
        for pattern in all_patterns:
            matches = re.finditer(pattern, query, re.DOTALL | re.IGNORECASE)
            for match in matches:
                formulas.append(
                    {"start": match.start(), "end": match.end(), "text": match.group()}
                )

        # Ordena fórmulas por posição
        formulas.sort(key=lambda x: x["start"])

        # Se não há fórmulas, trunca normalmente
        if not formulas:
            return query[:max_chars]

        # Verifica se o corte em max_chars está no meio de uma fórmula
        cut_position = max_chars

        for formula in formulas:
            # Se o corte está no meio de uma fórmula
            if formula["start"] < cut_position < formula["end"]:
                # Verifica se podemos incluir a fórmula completa
                if formula["end"] <= len(query):
                    # Se incluir a fórmula completa não deixa o texto muito longo (até 2x o limite)
                    if formula["end"] <= max_chars * 2:
                        cut_position = formula["end"]
                    else:
                        # Se a fórmula é muito longa, corta antes dela
                        cut_position = formula["start"]
                break

        # Garante que não cortamos no meio de uma palavra
        truncated = query[:cut_position]

        # Se não termina com espaço ou pontuação, tenta encontrar o último espaço
        if cut_position < len(query) and query[cut_position] not in " \t\n.,;!?":
            last_space = truncated.rfind(" ")
            if last_space > max_chars * 0.7:  # Só volta se não perder muito texto
                truncated = truncated[:last_space]

        return truncated.strip()

    def truncate_to_first_formula_with_context(self, query: str) -> str:
        """
        Nova estratégia de truncamento: mantém apenas as 3 palavras antes da primeira fórmula
        e a primeira fórmula completa.
        """
        # Padrões para detectar fórmulas
        latex_patterns = [
            r"\$\$.*?\$\$",  # $$formula$$
            r"\$.*?\$",  # $formula$
        ]

        mathml_patterns = [
            r"<math.*?</math>",
            r"<mml:math.*?</mml:math>",
        ]

        all_patterns = latex_patterns + mathml_patterns

        # Encontra todas as fórmulas na query
        formulas = []
        for pattern in all_patterns:
            matches = re.finditer(pattern, query, re.DOTALL | re.IGNORECASE)
            for match in matches:
                formulas.append(
                    {"start": match.start(), "end": match.end(), "text": match.group()}
                )

        # Se não há fórmulas, retorna as primeiras 50 caracteres
        if not formulas:
            return query[:50].strip()

        # Ordena fórmulas por posição e pega a primeira
        formulas.sort(key=lambda x: x["start"])
        first_formula = formulas[0]

        # Pega o texto antes da primeira fórmula
        text_before_formula = query[: first_formula["start"]]

        # Divide em palavras e pega as últimas 3
        words_before = text_before_formula.split()
        context_words = words_before[-3:] if len(words_before) >= 3 else words_before

        # Monta o resultado: contexto + primeira fórmula
        if context_words:
            context_text = " ".join(context_words)
            result = f"{context_text} {first_formula['text']}"
        else:
            # Se não há palavras antes, só a fórmula
            result = first_formula["text"]

        return result.strip()

    def test_search_endpoint(
        self, endpoint: str, query: str, expected_post_id: int, top_k: int = 10
    ) -> Dict[str, Any]:
        """Testa um endpoint de busca específico"""
        url = f"{self.base_url}/{endpoint}"
        payload = {"query": query}

        try:
            start_time = time.time()
            response = requests.post(url, json=payload, timeout=1000)
            end_time = time.time()

            if response.status_code == 200:
                result = response.json()

                # Verifica se é a rota especial com múltiplos approaches
                if (
                    endpoint
                    == "search-with-text-without-formula-combined-with-slt-formula-vector"
                ):
                    # Rota com múltiplos approaches
                    approaches_results = {}

                    for approach_name, approach_results in result.get(
                        "results", {}
                    ).items():
                        if isinstance(approach_results, list):
                            # Encontra a posição do post correto (1-indexed)
                            target_position = None
                            for i, post in enumerate(approach_results[:top_k]):
                                if int(post.get("post_id")) == expected_post_id:
                                    target_position = i + 1  # posição 1-indexed
                                    break

                            approaches_results[approach_name] = {
                                "success": True,
                                "response_time": end_time - start_time,
                                "total_results": len(approach_results),
                                "expected_post_id": expected_post_id,
                                "target_position": target_position,
                                "found_in_top_k": target_position is not None,
                                "top_k_results": [
                                    {
                                        "post_id": post.get("post_id"),
                                        "score": post.get("_score", 0),
                                    }
                                    for post in approach_results[:top_k]
                                ],
                            }

                    return {
                        "success": True,
                        "is_multi_approach": True,
                        "approaches": approaches_results,
                        "response_time": end_time - start_time,
                    }
                else:
                    # Rota normal com top_posts
                    top_posts = result.get("top_posts", [])

                    # Encontra a posição do post correto (1-indexed)
                    target_position = None
                    for i, post in enumerate(top_posts[:top_k]):
                        if post.get("post_id") == expected_post_id:
                            target_position = i + 1  # posição 1-indexed
                            break

                    return {
                        "success": True,
                        "is_multi_approach": False,
                        "response_time": end_time - start_time,
                        "total_results": len(top_posts),
                        "expected_post_id": expected_post_id,
                        "target_position": target_position,
                        "found_in_top_k": target_position is not None,
                        "top_k_results": [
                            {
                                "post_id": post.get("post_id"),
                                "score": post.get("score", 0),
                            }
                            for post in top_posts[:top_k]
                        ],
                    }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "response_time": end_time - start_time,
                    "target_position": None,
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "response_time": None,
                "target_position": None,
            }

    def run_tests(self, test_data_file: str, top_k: int = 10) -> Dict[str, Any]:
        """Executa todos os testes"""
        print(f"Carregando dados de teste de: {test_data_file}")
        test_data = self.load_test_data(test_data_file)
        test_data = test_data["questions"]
        print(f"Carregados {len(test_data)} casos de teste")

        # Todos os endpoints disponíveis
        endpoints = [
            # "search-pure-text",
            # "search-text-with-treated-formulas",
            # "search-text-vector",
            "search-with-text-without-formula-combined-with-slt-formula-vector",
        ]

        # Todos os tipos de query disponíveis (agora com variações truncadas)
        base_query_types = [
            "text_with_formulas_replaced",
            "text_lightly_modified",
            "text_semantically_modified",
            "text_natural_language",
        ]

        # Cria versões completas e truncadas de cada tipo
        query_types = []
        for base_type in base_query_types:
            query_types.append(base_type)  # Versão completa
            query_types.append(f"{base_type}_truncated_50")  # Versão truncada

        results = {
            "summary": {
                "total_test_cases": len(test_data),
                "total_combinations": len(endpoints)
                * len(query_types)
                * len(test_data),
                "top_k": top_k,
                "endpoints": endpoints,
                "base_query_types": base_query_types,
                "query_types": query_types,
            },
            "detailed_results": {},
            "performance_summary": {},
        }

        # Testa cada combinação de endpoint + tipo de query
        for endpoint in endpoints:
            print(f"\n{'='*80}")
            print(f"TESTANDO ENDPOINT: /{endpoint}")
            print(f"{'='*80}")

            results["detailed_results"][endpoint] = {}
            results["performance_summary"][endpoint] = {}

            for query_type in query_types:
                print(f"\n--- Tipo de Query: {query_type} ---")

                query_results = []

                # Determina se é uma query truncada e qual é o tipo base
                is_truncated = query_type.endswith("_truncated_50")
                base_query_type = (
                    query_type.replace("_truncated_50", "")
                    if is_truncated
                    else query_type
                )

                for i, test_case in enumerate(test_data):
                    base_query_text = test_case.get(base_query_type, "")
                    expected_post_id = test_case.get("post_id")

                    if not base_query_text or not expected_post_id:
                        print(f"  Caso {i+1}: Dados incompletos, pulando...")
                        continue

                    # Aplica truncamento se necessário
                    if is_truncated:
                        # Estratégia diferente baseada no tipo de query
                        if base_query_type in [
                            "text_with_formulas_replaced",
                            "text_lightly_modified",
                        ]:
                            # Para os dois primeiros tipos: 3 palavras antes + primeira fórmula
                            query_text = self.truncate_to_first_formula_with_context(
                                base_query_text
                            )
                            print(
                                f"  Caso {i+1}: Testando post_id {expected_post_id} (contexto+fórmula: {len(query_text)} chars)"
                            )
                        else:
                            # Para os dois últimos tipos: truncamento preservando fórmulas
                            query_text = self.truncate_query_preserving_formulas(
                                base_query_text, 50
                            )
                            print(
                                f"  Caso {i+1}: Testando post_id {expected_post_id} (truncado: {len(query_text)} chars)"
                            )
                    else:
                        query_text = base_query_text
                        print(
                            f"  Caso {i+1}: Testando post_id {expected_post_id} (completo: {len(query_text)} chars)"
                        )

                    # Faz UMA única query para o endpoint
                    raw_result = self.test_search_endpoint(
                        endpoint, query_text, expected_post_id, top_k
                    )

                    # Se é o endpoint especial com múltiplos approaches
                    if (
                        endpoint
                        == "search-with-text-without-formula-combined-with-slt-formula-vector"
                        and raw_result.get("success")
                        and raw_result.get("is_multi_approach")
                    ):
                        # Salva um resultado para cada approach
                        for approach_name, approach_result in raw_result.get(
                            "approaches", {}
                        ).items():
                            result = approach_result.copy()
                            result["test_case_id"] = i + 1
                            result["query_type"] = query_type
                            result["endpoint"] = (
                                f"{endpoint}#{approach_name}"  # Marca qual approach é
                            )
                            result["approach_name"] = approach_name
                            result["is_truncated"] = is_truncated
                            result["query_length"] = len(query_text)
                            result["original_query_length"] = len(base_query_text)
                            result["query_text"] = (
                                query_text[:100] + "..."
                                if len(query_text) > 100
                                else query_text
                            )

                            query_results.append(result)

                            if result["success"]:
                                if result.get("target_position") is not None:
                                    print(
                                        f"    ✓ {approach_name}: Encontrado na posição {result['target_position']}"
                                    )
                                else:
                                    print(
                                        f"    ✗ {approach_name}: Não encontrado no top-{top_k}"
                                    )
                            else:
                                print(
                                    f"    ✗ {approach_name}: Erro: {result.get('error', 'Erro desconhecido')}"
                                )
                    else:
                        # Endpoint normal - salva um único resultado
                        result = raw_result
                        result["test_case_id"] = i + 1
                        result["query_type"] = query_type
                        result["endpoint"] = endpoint
                        result["is_truncated"] = is_truncated
                        result["query_length"] = len(query_text)
                        result["original_query_length"] = len(base_query_text)
                        result["query_text"] = (
                            query_text[:100] + "..."
                            if len(query_text) > 100
                            else query_text
                        )

                        query_results.append(result)

                        if result["success"]:
                            if result.get("target_position") is not None:
                                print(
                                    f"    ✓ Encontrado na posição {result['target_position']}"
                                )
                            else:
                                print(f"    ✗ Não encontrado no top-{top_k}")
                        else:
                            print(
                                f"    ✗ Erro: {result.get('error', 'Erro desconhecido')}"
                            )

                # Salva os resultados detalhados
                results["detailed_results"][endpoint][query_type] = query_results

                # NOVA LÓGICA: Calcula performance_summary separadamente por approach
                if (
                    endpoint
                    == "search-with-text-without-formula-combined-with-slt-formula-vector"
                ):
                    # Para a rota especial, agrupa por approach
                    approaches_in_results = {}
                    for result in query_results:
                        approach_name = result.get("approach_name")
                        if approach_name:
                            if approach_name not in approaches_in_results:
                                approaches_in_results[approach_name] = []
                            approaches_in_results[approach_name].append(result)

                    # Cria performance_summary para cada approach separadamente
                    approach_summaries = {}
                    for (
                        approach_name,
                        approach_results,
                    ) in approaches_in_results.items():
                        successful_tests = sum(
                            1 for r in approach_results if r["success"]
                        )
                        found_in_top_k = sum(
                            1
                            for r in approach_results
                            if r.get("target_position") is not None
                        )
                        total_response_time = sum(
                            r["response_time"] for r in approach_results if r["success"]
                        )
                        positions = [
                            r["target_position"]
                            for r in approach_results
                            if r.get("target_position") is not None
                        ]

                        success_rate = (
                            (successful_tests / len(approach_results) * 100)
                            if approach_results
                            else 0
                        )
                        hit_rate = (
                            (found_in_top_k / successful_tests * 100)
                            if successful_tests > 0
                            else 0
                        )
                        avg_response_time = (
                            (total_response_time / successful_tests)
                            if successful_tests > 0
                            else 0
                        )
                        avg_position = (
                            sum(positions) / len(positions) if positions else None
                        )

                        approach_summaries[approach_name] = {
                            "total_cases": len(test_data),
                            "successful_requests": successful_tests,
                            "success_rate_percent": round(success_rate, 2),
                            "found_in_top_k": found_in_top_k,
                            "hit_rate_percent": round(hit_rate, 2),
                            "avg_response_time_seconds": round(avg_response_time, 3),
                            "avg_position_when_found": (
                                round(avg_position, 2) if avg_position else None
                            ),
                            "all_positions": positions,
                            "median_position": (
                                self._calculate_median(positions) if positions else None
                            ),
                            "is_truncated": is_truncated,
                            "approach_name": approach_name,
                        }

                        print(
                            f"  Approach {approach_name}: {successful_tests}/{len(approach_results)} sucessos ({success_rate:.1f}%)"
                        )
                        print(
                            f"    Taxa de acerto no top-{top_k}: {found_in_top_k}/{successful_tests} ({hit_rate:.1f}%)"
                        )
                        print(f"    Tempo médio de resposta: {avg_response_time:.3f}s")
                        if avg_position:
                            print(
                                f"    Posição média quando encontrado: {avg_position:.2f}"
                            )

                    # Salva cada approach como uma entrada separada no performance_summary
                    for approach_name, approach_summary in approach_summaries.items():
                        approach_key = f"{endpoint}#{approach_name}"
                        if approach_key not in results["performance_summary"]:
                            results["performance_summary"][approach_key] = {}
                        results["performance_summary"][approach_key][
                            query_type
                        ] = approach_summary

                else:
                    # Para endpoints normais, calcula como antes
                    successful_tests = sum(1 for r in query_results if r["success"])
                    found_in_top_k = sum(
                        1 for r in query_results if r.get("target_position") is not None
                    )
                    total_response_time = sum(
                        r["response_time"] for r in query_results if r["success"]
                    )
                    positions = [
                        r["target_position"]
                        for r in query_results
                        if r.get("target_position") is not None
                    ]

                    success_rate = (
                        (successful_tests / len(test_data) * 100)
                        if len(test_data) > 0
                        else 0
                    )
                    hit_rate = (
                        (found_in_top_k / successful_tests * 100)
                        if successful_tests > 0
                        else 0
                    )
                    avg_response_time = (
                        (total_response_time / successful_tests)
                        if successful_tests > 0
                        else 0
                    )
                    avg_position = (
                        sum(positions) / len(positions) if positions else None
                    )

                    results["performance_summary"][endpoint][query_type] = {
                        "total_cases": len(test_data),
                        "successful_requests": successful_tests,
                        "success_rate_percent": round(success_rate, 2),
                        "found_in_top_k": found_in_top_k,
                        "hit_rate_percent": round(hit_rate, 2),
                        "avg_response_time_seconds": round(avg_response_time, 3),
                        "avg_position_when_found": (
                            round(avg_position, 2) if avg_position else None
                        ),
                        "all_positions": positions,
                        "median_position": (
                            self._calculate_median(positions) if positions else None
                        ),
                        "is_truncated": is_truncated,
                    }

                    print(
                        f"  Resumo: {successful_tests}/{len(test_data)} sucessos ({success_rate:.1f}%)"
                    )
                    print(
                        f"  Taxa de acerto no top-{top_k}: {found_in_top_k}/{successful_tests} ({hit_rate:.1f}%)"
                    )
                    print(f"  Tempo médio de resposta: {avg_response_time:.3f}s")
                    if avg_position:
                        print(f"  Posição média quando encontrado: {avg_position:.2f}")

        return results

    def _calculate_median(self, positions: List[int]) -> float:
        """Calcula a mediana das posições"""
        if not positions:
            return None
        sorted_positions = sorted(positions)
        n = len(sorted_positions)
        if n % 2 == 0:
            return (sorted_positions[n // 2 - 1] + sorted_positions[n // 2]) / 2
        else:
            return sorted_positions[n // 2]

    def print_summary(self, results: Dict[str, Any]):
        """Imprime um resumo dos resultados"""
        print("\n" + "=" * 140)
        print("RESUMO FINAL DOS TESTES")
        print("=" * 140)

        summary = results["summary"]
        print(f"Total de casos de teste: {summary['total_test_cases']}")
        print(f"Total de combinações testadas: {summary['total_combinations']}")
        print(f"Top-K avaliado: {summary['top_k']}")
        print(f"Endpoints testados: {len(summary['endpoints'])}")
        print(f"Tipos de query base: {len(summary['base_query_types'])}")
        print(f"Tipos de query total (com truncadas): {len(summary['query_types'])}")

        # Tabela resumo por endpoint e tipo de query
        print(
            f"\n{'Endpoint':<70} {'Query Type':<45} {'Trunc':<6} {'Taxa Sucesso':<12} {'Taxa Acerto':<12} {'Pos. Média':<10} {'Pos. Mediana':<12} {'Tempo Médio'}"
        )
        print("-" * 190)

        # Agora usa o performance_summary que já está separado por approach
        for endpoint_key in sorted(results["performance_summary"].keys()):
            for query_type in summary["query_types"]:
                if query_type in results["performance_summary"][endpoint_key]:
                    perf = results["performance_summary"][endpoint_key][query_type]
                    success_rate = f"{perf['success_rate_percent']}%"
                    hit_rate = f"{perf['hit_rate_percent']}%"
                    avg_pos = (
                        f"{perf['avg_position_when_found']:.1f}"
                        if perf["avg_position_when_found"]
                        else "N/A"
                    )
                    median_pos = (
                        f"{perf['median_position']:.1f}"
                        if perf["median_position"]
                        else "N/A"
                    )
                    avg_time = f"{perf['avg_response_time_seconds']:.3f}s"
                    truncated_flag = "SIM" if perf["is_truncated"] else "NÃO"

                    print(
                        f"{endpoint_key:<70} {query_type:<45} {truncated_flag:<6} {success_rate:<12} {hit_rate:<12} {avg_pos:<10} {median_pos:<12} {avg_time}"
                    )

        # Análise comparativa entre versões completas e truncadas
        print(f"\n{'='*80}")
        print("ANÁLISE COMPARATIVA: COMPLETA vs TRUNCADA")
        print(f"{'='*80}")

        comparison_data = {}
        for base_type in summary["base_query_types"]:
            comparison_data[base_type] = {}

            for endpoint_key in results["performance_summary"].keys():
                full_type = base_type
                truncated_type = f"{base_type}_truncated_50"

                if (
                    full_type in results["performance_summary"][endpoint_key]
                    and truncated_type in results["performance_summary"][endpoint_key]
                ):

                    full_perf = results["performance_summary"][endpoint_key][full_type]
                    trunc_perf = results["performance_summary"][endpoint_key][
                        truncated_type
                    ]

                    comparison_data[base_type][endpoint_key] = {
                        "full_hit_rate": full_perf["hit_rate_percent"],
                        "truncated_hit_rate": trunc_perf["hit_rate_percent"],
                        "hit_rate_diff": trunc_perf["hit_rate_percent"]
                        - full_perf["hit_rate_percent"],
                        "full_avg_time": full_perf["avg_response_time_seconds"],
                        "truncated_avg_time": trunc_perf["avg_response_time_seconds"],
                        "time_diff": trunc_perf["avg_response_time_seconds"]
                        - full_perf["avg_response_time_seconds"],
                    }

        print(
            f"{'Endpoint':<70} {'Query Type':<35} {'Hit Rate Completa':<15} {'Hit Rate Truncada':<16} {'Diferença Hit':<12} {'Tempo Completo':<13} {'Tempo Truncado':<14} {'Dif. Tempo'}"
        )
        print("-" * 200)

        for base_type in summary["base_query_types"]:
            for endpoint_key in sorted(results["performance_summary"].keys()):
                if (
                    base_type in comparison_data
                    and endpoint_key in comparison_data[base_type]
                ):
                    comp = comparison_data[base_type][endpoint_key]

                    full_hit = f"{comp['full_hit_rate']:.1f}%"
                    trunc_hit = f"{comp['truncated_hit_rate']:.1f}%"
                    hit_diff = f"{comp['hit_rate_diff']:+.1f}%"
                    full_time = f"{comp['full_avg_time']:.3f}s"
                    trunc_time = f"{comp['truncated_avg_time']:.3f}s"
                    time_diff = f"{comp['time_diff']:+.3f}s"

                    print(
                        f"{endpoint_key:<70} {base_type:<35} {full_hit:<15} {trunc_hit:<16} {hit_diff:<12} {full_time:<13} {trunc_time:<14} {time_diff}"
                    )

    def save_results(self, results: Dict[str, Any], output_file: str):
        """Salva os resultados em um arquivo JSON"""
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\nResultados detalhados salvos em: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Testa a performance das rotas de busca"
    )
    parser.add_argument(
        "--data",
        default="app/assert/questoes_formulas_selecionadas.json",
        help="Arquivo JSON com os dados de teste",
    )
    parser.add_argument(
        "--base-url", default="http://localhost:8000", help="URL base da API"
    )
    parser.add_argument(
        "--top-k", type=int, default=10, help="Número de resultados top-k para avaliar"
    )
    parser.add_argument(
        "--output",
        default="test_results.json",
        help="Arquivo para salvar os resultados",
    )

    args = parser.parse_args()

    print("Iniciando testes de performance das rotas de busca...")
    print(f"URL base: {args.base_url}")
    print(f"Arquivo de dados: {args.data}")
    print(f"Top-K: {args.top_k}")

    tester = SearchTester(args.base_url)

    try:
        results = tester.run_tests(args.data, args.top_k)
        tester.print_summary(results)
        tester.save_results(results, args.output)

    except FileNotFoundError:
        print(f"Erro: Arquivo de dados não encontrado: {args.data}")
    except requests.exceptions.ConnectionError:
        print(f"Erro: Não foi possível conectar à API em {args.base_url}")
        print("Certifique-se de que o servidor está rodando.")
    except Exception as e:
        print(f"Erro inesperado: {e}")


if __name__ == "__main__":
    main()
