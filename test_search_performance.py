#!/usr/bin/env python3
"""
Script para testar a performance das diferentes rotas de busca
usando as queries da base de dados de teste
"""

import json
import requests
import time
from typing import Dict, List, Any
import argparse


class SearchTester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results = {}

    def load_test_data(self, json_file: str) -> List[Dict]:
        """Carrega os dados de teste do arquivo JSON"""
        with open(json_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def test_search_endpoint(
        self, endpoint: str, query: str, expected_post_id: int, top_k: int = 10
    ) -> Dict[str, Any]:
        """Testa um endpoint de busca específico"""
        url = f"{self.base_url}/{endpoint}"
        payload = {"query": query}

        try:
            start_time = time.time()
            response = requests.post(url, json=payload, timeout=30)
            end_time = time.time()

            if response.status_code == 200:
                result = response.json()
                top_posts = result.get("top_posts", [])

                # Verifica se o post correto está nos top_k resultados
                found_positions = []
                for i, post in enumerate(top_posts[:top_k]):
                    if post.get("post_id") == expected_post_id:
                        found_positions.append(i + 1)  # posição 1-indexed

                return {
                    "success": True,
                    "response_time": end_time - start_time,
                    "total_results": len(top_posts),
                    "expected_post_id": expected_post_id,
                    "found_at_positions": found_positions,
                    "found_in_top_k": len(found_positions) > 0,
                    "best_position": min(found_positions) if found_positions else None,
                    "top_k_results": [
                        {"post_id": post.get("post_id"), "score": post.get("score", 0)}
                        for post in top_posts[:top_k]
                    ],
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "response_time": end_time - start_time,
                }

        except Exception as e:
            return {"success": False, "error": str(e), "response_time": None}

    def run_tests(self, test_data_file: str, top_k: int = 10) -> Dict[str, Any]:
        """Executa todos os testes"""
        print(f"Carregando dados de teste de: {test_data_file}")
        test_data = self.load_test_data(test_data_file)
        print(f"Carregados {len(test_data)} casos de teste")

        # Mapeamento dos tipos de query para endpoints
        query_endpoint_mapping = {
            "text_with_formulas_replaced": "search-pure-text",
            "text_lightly_modified": "search-text-with-treated-formulas",
            "text_semantically_modified": "search-text-vector",
            "text_natural_language": "search-with-text-without-formula-combined-with-slt-formula-vector",
        }

        results = {
            "summary": {
                "total_tests": len(test_data),
                "top_k": top_k,
                "query_types": list(query_endpoint_mapping.keys()),
            },
            "detailed_results": {},
            "performance_summary": {},
        }

        for query_type, endpoint in query_endpoint_mapping.items():
            print(f"\n=== Testando {query_type} usando endpoint /{endpoint} ===")

            query_results = []
            successful_tests = 0
            found_in_top_k = 0
            total_response_time = 0
            positions = []

            for i, test_case in enumerate(test_data):
                query_text = test_case.get(query_type, "")
                expected_post_id = test_case.get("post_id")

                if not query_text or not expected_post_id:
                    print(f"  Caso {i+1}: Dados incompletos, pulando...")
                    continue

                print(f"  Caso {i+1}: Testando post_id {expected_post_id}")

                result = self.test_search_endpoint(
                    endpoint, query_text, expected_post_id, top_k
                )
                result["test_case_id"] = i + 1
                result["query_type"] = query_type
                result["query_text"] = (
                    query_text[:100] + "..." if len(query_text) > 100 else query_text
                )

                query_results.append(result)

                if result["success"]:
                    successful_tests += 1
                    total_response_time += result["response_time"]

                    if result["found_in_top_k"]:
                        found_in_top_k += 1
                        positions.append(result["best_position"])
                        print(f"    ✓ Encontrado na posição {result['best_position']}")
                    else:
                        print(f"    ✗ Não encontrado no top-{top_k}")
                else:
                    print(f"    ✗ Erro: {result['error']}")

            # Calcula estatísticas
            avg_response_time = (
                total_response_time / successful_tests if successful_tests > 0 else 0
            )
            success_rate = successful_tests / len(test_data) * 100
            hit_rate = (
                found_in_top_k / successful_tests * 100 if successful_tests > 0 else 0
            )
            avg_position = sum(positions) / len(positions) if positions else None

            results["detailed_results"][query_type] = query_results
            results["performance_summary"][query_type] = {
                "endpoint": endpoint,
                "total_cases": len(test_data),
                "successful_requests": successful_tests,
                "success_rate_percent": round(success_rate, 2),
                "found_in_top_k": found_in_top_k,
                "hit_rate_percent": round(hit_rate, 2),
                "avg_response_time_seconds": round(avg_response_time, 3),
                "avg_position_when_found": (
                    round(avg_position, 2) if avg_position else None
                ),
                "best_positions": positions,
            }

            print(
                f"  Resumo: {successful_tests}/{len(test_data)} sucessos ({success_rate:.1f}%)"
            )
            print(
                f"  Taxa de acerto no top-{top_k}: {found_in_top_k}/{successful_tests} ({hit_rate:.1f}%)"
            )
            print(f"  Tempo médio de resposta: {avg_response_time:.3f}s")

        return results

    def print_summary(self, results: Dict[str, Any]):
        """Imprime um resumo dos resultados"""
        print("\n" + "=" * 80)
        print("RESUMO FINAL DOS TESTES")
        print("=" * 80)

        summary = results["summary"]
        print(f"Total de casos de teste: {summary['total_tests']}")
        print(f"Top-K avaliado: {summary['top_k']}")
        print(f"Tipos de query testados: {len(summary['query_types'])}")

        print(
            f"\n{'Tipo de Query':<35} {'Endpoint':<45} {'Taxa Sucesso':<12} {'Taxa Acerto':<12} {'Pos. Média':<10} {'Tempo Médio'}"
        )
        print("-" * 130)

        for query_type, perf in results["performance_summary"].items():
            endpoint = perf["endpoint"]
            success_rate = f"{perf['success_rate_percent']}%"
            hit_rate = f"{perf['hit_rate_percent']}%"
            avg_pos = (
                f"{perf['avg_position_when_found']:.1f}"
                if perf["avg_position_when_found"]
                else "N/A"
            )
            avg_time = f"{perf['avg_response_time_seconds']:.3f}s"

            print(
                f"{query_type:<35} {endpoint:<45} {success_rate:<12} {hit_rate:<12} {avg_pos:<10} {avg_time}"
            )

    def save_results(self, results: Dict[str, Any], output_file: str):
        """Salva os resultados em um arquivo JSON"""
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\nResultados salvos em: {output_file}")


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
