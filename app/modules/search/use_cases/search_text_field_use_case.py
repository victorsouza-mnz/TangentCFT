from services.elasticsearch_service import ElasticsearchService
from typing import List, Dict, Any


class SearchTextFieldUseCase:
    """
    Use case para buscar posts usando texto puro no Elasticsearch.
    """

    def __init__(self, elasticsearch_service: ElasticsearchService):
        self.elasticsearch_service = elasticsearch_service

    def execute(
        self, query: str, size: int = 10, field: str = "text"
    ) -> List[Dict[str, Any]]:
        """
        Executa a busca de texto puro no Elasticsearch.

        Args:
            query: Texto para buscar
            size: Número máximo de resultados
            field: Nome do campo de texto para buscar (padrão: "text")

        Returns:
            Lista dos posts encontrados, com informações relevantes
        """
        try:
            # Prepara a query para buscar no campo especificado
            search_query = {"query": {"match": {field: query}}, "size": size}

            # Executa a busca
            results = self.elasticsearch_service.es.search(
                index=self.elasticsearch_service.posts_index_name, body=search_query
            )

            # Extrai e formata os resultados
            hits = results["hits"]["hits"]
            formatted_results = []

            for hit in hits:
                source = hit["_source"]
                formatted_results.append(
                    {
                        "post_id": source.get("post_id"),
                        "text": source.get("text"),
                        "score": hit["_score"],
                    }
                )

            return formatted_results

        except Exception as e:
            print(f"Error searching pure text: {str(e)}")
            raise e


def make_search_text_field_use_case():
    """
    Factory function para criar o caso de uso de busca de texto puro.
    """
    elasticsearch_service = ElasticsearchService()
    return SearchTextFieldUseCase(elasticsearch_service)
