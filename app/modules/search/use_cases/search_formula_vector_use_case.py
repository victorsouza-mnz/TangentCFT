from collections import defaultdict


# TODO da para parelelizar ou cirar nova index de formulas
class SearchFormulaVectorUseCase:
    def __init__(self, es_client, index_name: str):
        self.es = es_client
        self.index = index_name

    def execute(self, formula_vectors: list[list[float]], top_k: int = 10):
        scores_by_doc = defaultdict(float)

        for vector in formula_vectors:
            response = self.es.search(
                index=self.index,
                size=top_k
                * 2,  # busca mais resultados por vetor (ajuda na fusão final)
                query={
                    "nested": {
                        "path": "formula_vectors",
                        "score_mode": "max",
                        "query": {
                            "script_score": {
                                "query": {"match_all": {}},
                                "script": {
                                    "source": "cosineSimilarity(params.vector, 'formula_vectors.vector')",
                                    "params": {"vector": vector},
                                },
                            }
                        },
                    }
                },
            )

            for hit in response["hits"]["hits"]:
                doc_id = hit["_id"]
                score = hit["_score"]
                # Estratégia: acumula o maior score obtido por esse doc (poderia somar ou média também)
                scores_by_doc[doc_id] = max(scores_by_doc[doc_id], score)

        # Ordena os documentos por score acumulado e retorna os top_k
        sorted_results = sorted(
            scores_by_doc.items(), key=lambda x: x[1], reverse=True
        )[:top_k]

        # Busca os documentos completos para retorno
        if sorted_results:
            ids = [doc_id for doc_id, _ in sorted_results]
            docs = self.es.mget(index=self.index, ids=ids)["docs"]
            docs_by_id = {doc["_id"]: doc for doc in docs if doc["found"]}
            return [docs_by_id[doc_id] for doc_id, _ in sorted_results]

        return []
