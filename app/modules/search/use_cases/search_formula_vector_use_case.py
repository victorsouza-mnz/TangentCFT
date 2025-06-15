from services.elasticsearch_service import ElasticsearchService

FORMULAS_INDEX = "formulas"


class SearchFormulaVectorUseCase:
    def __init__(self, es: ElasticsearchService, vector_type: str = "formula_vector"):
        self.es = es
        self.vector_type = vector_type

        # Validate vector type
        valid_types = ["formula_vector", "slt_vector", "slt_type_vector", "opt_vector"]
        if vector_type not in valid_types:
            raise ValueError(
                f"Invalid vector_type '{vector_type}'. Must be one of: {valid_types}"
            )

    def execute(self, formula_vector: list, top_k: int):
        """
        Execute vector similarity search.

        Args:
            formula_vector: Single query vector
            top_k: Number of top results to return

        Returns:
            List of search results with score and document id
        """
        search_query = {
            "knn": {
                "field": self.vector_type,
                "query_vector": formula_vector,
                "k": top_k,
                "num_candidates": top_k * 2,
            }
        }
        # Executa a busca
        results = self.es.es.knn_search(
            index=self.es.formulas_index_name, body=search_query
        )

        # Format results to return score and document id
        formatted_results = []
        for hit in results["hits"]["hits"]:
            source = hit["_source"]
            formatted_results.append(
                {
                    "score": hit["_score"],
                    "formula_id": source.get("formula_id"),
                    "document_id": hit["_id"],
                }
            )

        return formatted_results


def make_search_formula_vector_use_case(vector_type: str = "formula_vector"):
    """
    Factory function to create SearchFormulaVectorUseCase.

    Args:
        vector_type: Type of vector to search on. Options:
                    - "formula_vector" (default): Combined vector
                    - "slt_vector": SLT representation vector
                    - "slt_type_vector": SLT type representation vector
                    - "opt_vector": OPT representation vector

    Returns:
        SearchFormulaVectorUseCase instance
    """
    from services.elasticsearch_service import ElasticsearchService

    es_service = ElasticsearchService()
    return SearchFormulaVectorUseCase(es_service, vector_type)
