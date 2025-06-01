from services.elasticsearch_service import ElasticsearchService
from scripts.utils.text_celaner import clean_text
from typing import List, Dict, Any


class SearchTextWithTreatedLatexUseCase:
    """
    Use case para buscar posts usando texto limpo de LaTeX no Elasticsearch.
    """

    def __init__(self, elasticsearch_service: ElasticsearchService):
        self.elasticsearch_service = elasticsearch_service

    def execute(self, query: str, size: int = 10) -> List[Dict[str, Any]]:
        """
        Executa a busca com texto tratado para LaTeX no Elasticsearch.

        Args:
            query: Texto para buscar
            size: Número máximo de resultados

        Returns:
            Lista dos posts encontrados, com informações relevantes
        """
        try:
            # Limpa o texto da consulta usando o cleaner
            cleaned_query = clean_text(query)

            # Prepara a query para buscar no campo 'text'
            search_query = {"query": {"match": {"text": cleaned_query}}, "size": size}

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
                        # Inclui o texto limpo para depuração/verificação
                        "clean_text": clean_text(source.get("text", "")),
                    }
                )

            return formatted_results

        except Exception as e:
            print(f"Error searching with treated latex: {str(e)}")
            return []


def make_search_text_with_treated_latex_use_case():
    """
    Factory function para criar o caso de uso de busca com texto tratado.
    """
    elasticsearch_service = ElasticsearchService()
    return SearchTextWithTreatedLatexUseCase(elasticsearch_service)
