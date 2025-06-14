from services.elasticsearch_service import ElasticsearchService
from app.modules.embedding.use_cases.get_text_vector import (
    make_get_text_vector_use_case,
)
from typing import List, Dict, Any


class SearchTextVectorUseCase:
    """
    Use case para buscar posts usando similaridade vetorial de texto.
    """

    def __init__(self, elasticsearch_service: ElasticsearchService):
        self.elasticsearch_service = elasticsearch_service
        self.get_text_vector_use_case = make_get_text_vector_use_case()

    def execute(self, query: str, size: int = 10) -> List[Dict[str, Any]]:
        """
        Executa a busca vetorial de texto no Elasticsearch.

        Args:
            query: Texto para buscar
            size: Número máximo de resultados

        Returns:
            Lista dos posts encontrados, com informações relevantes
        """
        try:

            # Gerar o vetor de embedding para a consulta
            print("generating query vector")
            query_vector = self.get_text_vector_use_case.execute(query)
            print("query_vector: ", query_vector)
            if query_vector is None:
                print("Failed to generate embedding for query")
                return []

            # Prepara a query de similaridade vetorial
            # TODO verficar se a query com dense vector é feita dessa forma
            print("preparing search query")
            search_query = {
                "knn": {
                    "field": "text_without_formula_vector",
                    "query_vector": query_vector,
                    "k": size,
                    "num_candidates": size * 2,
                }
            }
            print("searching... search query: ", search_query)
            # Executa a busca
            results = self.elasticsearch_service.es.knn_search(
                index=self.elasticsearch_service.posts_index_name, body=search_query
            )
            print("results: ", results)
            # Extrai e formata os resultados
            hits = results["hits"]["hits"]
            formatted_results = []

            for hit in hits:
                source = hit["_source"]
                formatted_results.append(
                    {
                        "post_id": source.get("post_id"),
                        "text": source.get("text"),
                        "text_without_formula": source.get("text_without_formula"),
                        "score": hit["_score"],
                    }
                )

            return formatted_results

        except Exception as e:
            print(f"Error searching with text vector: {str(e)}")
            return []


def make_search_text_vector_use_case():
    """
    Factory function para criar o caso de uso de busca vetorial de texto.
    """
    elasticsearch_service = ElasticsearchService()
    return SearchTextVectorUseCase(elasticsearch_service)
