from services.elasticsearch_service import ElasticsearchService
from app.modules.shared.text_celaner import clean_text
from typing import List, Dict, Any
from app.modules.shared.extract_latex_formulas import (
    get_latex_formulas_larger_than_5_with_only_dollar_delimiters,
)
from app.modules.shared.parse_html_to_text_with_latex import (
    parse_html_to_text_with_latex,
)


class SearchTextWithTreatedFormulasUseCase:
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
            print("query: ", query)
            # Remove <span> tags and add $ delimiters and remove other html tags
            text_query = parse_html_to_text_with_latex(query)
            print("text_query: ", text_query)

            # Sanitize latex formulas in the query for more accurate search
            cleaned_query = clean_text(text_query)
            print("cleaned_query: ", cleaned_query)
            raw_formulas = get_latex_formulas_larger_than_5_with_only_dollar_delimiters(
                text_query
            )

            print("raw_formulas: ", raw_formulas)

            cleaned_formulas = [
                clean_text(f) for f in raw_formulas if len(f.strip()) > 5
            ]

            print("cleaned_formulas: ", cleaned_formulas)

            should_clauses = [{"match": {"text_latex_search": cleaned_query}}] + [
                {
                    "match_phrase": {
                        "text_latex_search": {
                            "query": formula,
                            "boost": 2,
                        }
                    }
                }
                for formula in cleaned_formulas
            ]
            search_query = {"query": {"bool": {"should": should_clauses}}, "size": size}

            # Executa a busca
            results = self.elasticsearch_service.es.search(
                index=self.elasticsearch_service.posts_index_name, body=search_query
            )

            # Processa os hits
            hits = results["hits"]["hits"]
            formatted_results = []
            print("hits: ", hits[0]["_source"].get("text_latex_search"))
            for hit in hits:
                source = hit["_source"]
                formatted_results.append(
                    {
                        "post_id": source.get("post_id"),
                        "text": source.get("text"),
                        "text_latex_search": source.get("text_latex_search"),
                        "score": hit["_score"],
                        # Inclui o texto limpo para depuração/verificação
                        "clean_text": clean_text(source.get("text", "")),
                    }
                )

            return formatted_results

        except Exception as e:
            print(f"Error searching with treated latex: {str(e)}")
            return []


def make_search_text_with_treated_formulas_use_case():
    """
    Factory function para criar o caso de uso de busca com texto tratado.
    """
    elasticsearch_service = ElasticsearchService()
    return SearchTextWithTreatedFormulasUseCase(elasticsearch_service)
