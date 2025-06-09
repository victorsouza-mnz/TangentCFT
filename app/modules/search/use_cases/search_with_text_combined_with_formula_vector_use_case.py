import numpy as np

from app.modules.search.use_cases.search_pure_text_use_case import (
    make_search_pure_text_use_case,
)
from app.modules.search.use_cases.search_formula_vector_use_case import (
    make_search_formula_vector_use_case,
)
from app.shared.similarity import (
    cosine_similarity,
)  # Supondo que exista um módulo para isso


class SearchWithTextCombinedWithFormulaVectorUseCase:
    def __init__(self, text_vector: str, formula_vectors: list[str]):
        self.text_vector = np.array(text_vector)
        self.formula_vectors = [np.array(v) for v in formula_vectors if v]

    def approach_1_combined_vector_search(
        self, top_k: int = 10, alpha: float = 0.7, beta: float = 0.3
    ):
        """
        Combina resultados de texto e fórmula via weighted sum de scores.
        """
        text_results = make_search_pure_text_use_case().execute(
            self.text_vector, top_k * 3
        )
        formula_results = make_search_formula_vector_use_case().execute(
            self.formula_vectors, top_k * 3
        )

        text_map = {r["_id"]: r["_score"] for r in text_results}
        formula_map = {r["_id"]: r["_score"] for r in formula_results}

        combined_scores = {}
        all_ids = set(text_map.keys()) | set(formula_map.keys())
        for _id in all_ids:
            t_score = text_map.get(_id, 0)
            f_score = formula_map.get(_id, 0)
            combined_scores[_id] = alpha * t_score + beta * f_score

        sorted_ids = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)[
            :top_k
        ]
        id_to_doc = {r["_id"]: r for r in text_results + formula_results}
        return [{**id_to_doc[_id], "_score": score} for _id, score in sorted_ids]

    def approach_2_combined_vector_search(
        self, top_k: int = 10, alpha: float = 0.5, beta: float = 0.5
    ):
        """
        Considera apenas documentos que aparecem nas duas buscas (texto e fórmula).
        """
        text_results = make_search_pure_text_use_case().execute(
            self.text_vector, top_k * 10
        )
        formula_results = make_search_formula_vector_use_case().execute(
            self.formula_vectors, top_k * 10
        )

        text_map = {r["_id"]: r["_score"] for r in text_results}
        formula_map = {r["_id"]: r["_score"] for r in formula_results}

        combined_scores = {}
        shared_ids = set(text_map.keys()) & set(formula_map.keys())
        for _id in shared_ids:
            combined_scores[_id] = alpha * text_map[_id] + beta * formula_map[_id]

        sorted_ids = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)[
            :top_k
        ]
        id_to_doc = {r["_id"]: r for r in text_results + formula_results}
        return [{**id_to_doc[_id], "_score": score} for _id, score in sorted_ids]

    def approach_3_max_formula_match_search(
        self, top_k: int = 10, alpha: float = 0.7, beta: float = 0.3
    ):
        """
        Calcula similaridade do texto + máximo match de fórmulas.
        """
        text_results = make_search_pure_text_use_case().execute(
            self.text_vector, top_k * 5
        )

        formula_results = make_search_formula_vector_use_case().execute(
            self.formula_vectors, top_k * 5
        )

        # Agrupa fórmulas por post
        post_formula_map = {}
        for result in formula_results:
            _id = result["_id"]
            vector = np.array(result["_source"]["formula_vector"])
            if _id not in post_formula_map:
                post_formula_map[_id] = []
            post_formula_map[_id].append(vector)

        combined_scores = {}
        for r in text_results:
            _id = r["_id"]
            text_score = r["_score"]
            formula_score = 0

            # Se houver fórmulas, calcula a máxima similaridade
            if _id in post_formula_map:
                max_sim = 0
                for doc_formula_vector in post_formula_map[_id]:
                    for query_formula_vector in self.formula_vectors:
                        sim = cosine_similarity(
                            query_formula_vector, doc_formula_vector
                        )
                        if sim > max_sim:
                            max_sim = sim
                formula_score = max_sim

            combined_scores[_id] = alpha * text_score + beta * formula_score

        sorted_ids = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)[
            :top_k
        ]
        id_to_doc = {r["_id"]: r for r in text_results}
        return [{**id_to_doc[_id], "_score": score} for _id, score in sorted_ids]

    def approach_4_formula_weight_by_quantity(
        self, top_k: int = 10, base_formula_weight: float = 0.1
    ):
        """
        Ajusta o peso da fórmula dinamicamente baseado na quantidade de fórmulas.
        """
        text_results = make_search_pure_text_use_case().execute(
            self.text_vector, top_k * 3
        )
        formula_results = make_search_formula_vector_use_case().execute(
            self.formula_vectors, top_k * 3
        )

        text_map = {r["_id"]: r["_score"] for r in text_results}
        formula_map = {r["_id"]: r["_score"] for r in formula_results}

        combined_scores = {}
        all_ids = set(text_map.keys()) | set(formula_map.keys())

        # Define pesos dinâmicos
        formula_weight = min(0.5, base_formula_weight * len(self.formula_vectors))
        text_weight = 1 - formula_weight

        for _id in all_ids:
            t_score = text_map.get(_id, 0)
            f_score = formula_map.get(_id, 0)
            combined_scores[_id] = text_weight * t_score + formula_weight * f_score

        sorted_ids = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)[
            :top_k
        ]
        id_to_doc = {r["_id"]: r for r in text_results + formula_results}
        return [{**id_to_doc[_id], "_score": score} for _id, score in sorted_ids]

    # TODO criar esse indice
    # def approach_5_concatenated_vector_search(self, top_k: int = 10):
    #     """
    #     Concatena vetor do texto com média dos vetores de fórmula.
    #     A busca depende de um índice específico para esse vetor concatenado.
    #     """
    #     if not self.formula_vectors:
    #         combined_vector = self.text_vector
    #     else:
    #         mean_formula = np.mean(self.formula_vectors, axis=0)
    #         combined_vector = np.concatenate([self.text_vector, mean_formula])

    #     # Supõe que há um índice separado para esse vetor concatenado
    #     from app.modules.search.use_cases.search_combined_vector_use_case import (
    #         make_search_combined_vector_use_case,
    #     )

    #     combined_results = make_search_combined_vector_use_case().execute(
    #         combined_vector, top_k
    #     )
    #     return combined_results


def make_search_with_text_combined_with_formula_vector_use_case(
    text_vector: str, formula_vectors: list[str]
):
    return SearchWithTextCombinedWithFormulaVectorUseCase(text_vector, formula_vectors)
