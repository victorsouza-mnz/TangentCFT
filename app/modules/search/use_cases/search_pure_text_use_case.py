from services.elasticsearch_service import ElasticsearchService
from typing import List, Dict, Any


class SearchPureTextUseCase:
    """
    Use case para buscar posts usando texto puro no Elasticsearch.
    """

    def __init__(self, elasticsearch_service: ElasticsearchService):
        self.elasticsearch_service = elasticsearch_service

    def execute(self, query: str, size: int = 10) -> List[Dict[str, Any]]:
        """
        Executa a busca de texto puro no Elasticsearch.

        Args:
            query: Texto para buscar
            size: Número máximo de resultados

        Returns:
            Lista dos posts encontrados, com informações relevantes
        """
        try:
            # Prepara a query para buscar no campo 'text'
            search_query = {"query": {"match": {"text": query}}, "size": size}

            # Executa a busca
            results = self.elasticsearch_service.es.search(
                index=self.elasticsearch_service.index_name, body=search_query
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
                        # Adicione outros campos relevantes conforme necessário
                    }
                )

            return formatted_results

        except Exception as e:
            print(f"Error searching pure text: {str(e)}")
            return []


def make_search_pure_text_use_case():
    """
    Factory function para criar o caso de uso de busca de texto puro.
    """
    elasticsearch_service = ElasticsearchService()
    return SearchPureTextUseCase(elasticsearch_service)
