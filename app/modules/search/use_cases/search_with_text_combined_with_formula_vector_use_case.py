import numpy as np
from app.modules.search.use_cases.search_text_field_use_case import (
    make_search_text_field_use_case,
)
from app.modules.search.use_cases.search_formula_vector_use_case import (
    make_search_formula_vector_use_case,
)

from app.modules.search.use_cases.search_text_with_treated_formulas_use_case import (
    make_search_text_with_treated_formulas_use_case,
)


def weighted_score(text_score: float, formula_score: float, alpha: float, beta: float):
    return alpha * text_score + beta * formula_score


class SearchWithTextCombinedWithFormulaVectorUseCase:
    def __init__(self, text: str, formula_vectors: list[list[float]]):
        self.text = text
        self.formula_vectors = [
            np.array(f) for f in formula_vectors if f is not None and len(f) > 0
        ]

    def _fetch_formula_results(self, formula_vector: np.ndarray, top_k: int):
        return make_search_formula_vector_use_case().execute([formula_vector], top_k)

    def _fetch_all_formula_results(self, top_k: int):
        return make_search_formula_vector_use_case().execute(
            self.formula_vectors, top_k
        )

    def _formula_weight(self, formula: np.ndarray) -> float:
        return min(1.0, np.linalg.norm(formula) / 10)  # fórmula grande = peso maior

    def _mean_formula_score(self, scores: list[float]) -> float:
        return sum(scores) / len(scores) if scores else 0.0

    # -------------------- Approach 01 --------------------

    def approach_1_individual_formula_max(
        self, top_k: int = 10, alpha: float = 0.5, beta: float = 0.5
    ):
        """
        Combina resultados de texto com o maior score de qualquer fórmula individual dentro de um post.
        """
        # Busca textual
        text_results = make_search_text_field_use_case().execute(
            self.text, top_k * 3, field="text_without_formula"
        )

        text_map = {str(r["post_id"]): r["score"] for r in text_results}

        # Busca por cada fórmula (retorna uma lista de listas de resultados)
        formula_results_nested = []
        for formula_vector in self.formula_vectors:
            results = make_search_formula_vector_use_case("slt_vector").execute(
                formula_vector, top_k * 3
            )
            formula_results_nested.append(results)

        # Flatten e pega maior score por post_id entre as fórmulas
        formula_map = {}
        flat_formula_results = []
        for result_list in formula_results_nested:
            for r in result_list:
                post_id = str(r["post_id"])
                score = r["score"]
                flat_formula_results.append(r)
                formula_map[post_id] = max(formula_map.get(post_id, 0), score)

        # Combinação de scores
        combined_scores = {}
        all_post_ids = set(text_map.keys()) | set(formula_map.keys())
        for post_id in all_post_ids:
            t_score = text_map.get(post_id, 0)
            f_score = formula_map.get(post_id, 0)
            print("post_id:", post_id, "t_score:", t_score, "f_score:", f_score)
            combined_scores[post_id] = weighted_score(t_score, f_score, alpha, beta)

        # Monta dicionário de docs, sem sobrescrever
        id_to_doc = {}

        for r in flat_formula_results:
            post_id = str(r["post_id"])  # importante forçar str!
            if post_id not in id_to_doc:
                id_to_doc[post_id] = {"post_id": post_id}
            id_to_doc[post_id]["_score_formula"] = r["score"]
            if "source" in r:
                id_to_doc[post_id].update(r["source"])

        for r in text_results:
            post_id = str(r["post_id"])  # importante forçar str!
            if post_id not in id_to_doc:
                id_to_doc[post_id] = {"post_id": post_id}
            id_to_doc[post_id]["_score_text"] = r["score"]
            if "source" in r:
                id_to_doc[post_id].update(r["source"])

        # Ordena pelo score combinado
        sorted_ids = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)[
            :top_k
        ]

        return [
            {**id_to_doc[post_id], "_score": score} for post_id, score in sorted_ids
        ]

    # -------------------- Approach 02 --------------------
    def approach_2_mean_formula_score(
        self, top_k: int = 10, alpha: float = 0.5, beta: float = 0.5
    ):
        """
        Combina os resultados de texto com a média dos scores de todas as fórmulas do post.
        """
        text_results = make_search_text_field_use_case().execute(
            self.text, top_k * 3, field="text_without_formula"
        )
        text_map = {str(r["post_id"]): r["score"] for r in text_results}

        formula_results_nested = []
        for formula_vector in self.formula_vectors:
            results = make_search_formula_vector_use_case("slt_vector").execute(
                formula_vector, top_k * 3
            )
            formula_results_nested.append(results)

        formula_score_map: dict[str, list[float]] = {}
        flat_formula_results = []
        for result_list in formula_results_nested:
            for r in result_list:
                post_id = str(r["post_id"])
                flat_formula_results.append(r)
                formula_score_map.setdefault(post_id, []).append(r["score"])

        formula_avg_map = {
            post_id: sum(scores) / len(scores)
            for post_id, scores in formula_score_map.items()
        }

        combined_scores = {}
        all_post_ids = set(text_map) | set(formula_avg_map)
        for post_id in all_post_ids:
            t_score = text_map.get(post_id, 0)
            f_score = formula_avg_map.get(post_id, 0)
            combined_scores[post_id] = weighted_score(t_score, f_score, alpha, beta)

        id_to_doc = {}
        for r in flat_formula_results:
            post_id = str(r["post_id"])
            if post_id not in id_to_doc:
                id_to_doc[post_id] = {"post_id": post_id}
            id_to_doc[post_id]["_score_formula"] = r["score"]
            if "source" in r:
                id_to_doc[post_id].update(r["source"])
        for r in text_results:
            post_id = str(r["post_id"])
            if post_id not in id_to_doc:
                id_to_doc[post_id] = {"post_id": post_id}
            id_to_doc[post_id]["_score_text"] = r["score"]
            if "source" in r:
                id_to_doc[post_id].update(r["source"])

        sorted_ids = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)[
            :top_k
        ]
        return [
            {**id_to_doc[pid], "_score": score}
            for pid, score in sorted_ids
            if pid in id_to_doc
        ]

    # -------------------- Approach 03 --------------------
    def approach_3_individual_formula_max_weighted(
        self, top_k: int = 10, alpha: float = 0.5, beta: float = 0.5
    ):
        """
        Igual ao approach 1, mas aplica um peso proporcional ao tamanho da fórmula em cada score.
        """
        text_results = make_search_text_field_use_case().execute(
            self.text, top_k * 3, field="text_without_formula"
        )
        text_map = {str(r["post_id"]): r["score"] for r in text_results}

        formula_map = {}
        flat_formula_results = []
        for formula_vector in self.formula_vectors:
            weight = self._formula_weight(formula_vector)
            results = make_search_formula_vector_use_case("slt_vector").execute(
                formula_vector, top_k * 3
            )
            for r in results:
                post_id = str(r["post_id"])
                weighted_score_value = r["score"] * weight
                r["score"] = weighted_score_value
                flat_formula_results.append(r)
                formula_map[post_id] = max(
                    formula_map.get(post_id, 0), weighted_score_value
                )

        combined_scores = {}
        all_post_ids = set(text_map) | set(formula_map)
        for post_id in all_post_ids:
            t_score = text_map.get(post_id, 0)
            f_score = formula_map.get(post_id, 0)
            combined_scores[post_id] = weighted_score(t_score, f_score, alpha, beta)

        id_to_doc = {}
        for r in flat_formula_results:
            post_id = str(r["post_id"])
            if post_id not in id_to_doc:
                id_to_doc[post_id] = {"post_id": post_id}
            id_to_doc[post_id]["_score_formula"] = r["score"]
            if "source" in r:
                id_to_doc[post_id].update(r["source"])
        for r in text_results:
            post_id = str(r["post_id"])
            if post_id not in id_to_doc:
                id_to_doc[post_id] = {"post_id": post_id}
            id_to_doc[post_id]["_score_text"] = r["score"]
            if "source" in r:
                id_to_doc[post_id].update(r["source"])

        sorted_ids = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)[
            :top_k
        ]
        return [
            {**id_to_doc[pid], "_score": score}
            for pid, score in sorted_ids
            if pid in id_to_doc
        ]

    # -------------------- Approach 04 --------------------
    def approach_4_mean_formula_score_weighted(
        self, top_k: int = 10, alpha: float = 0.5, beta: float = 0.5
    ):
        """
        Igual ao approach 2, mas cada score de fórmula é ponderado pelo seu tamanho.
        """
        text_results = make_search_text_field_use_case().execute(
            self.text, top_k * 3, field="text_without_formula"
        )
        text_map = {str(r["post_id"]): r["score"] for r in text_results}

        formula_score_map: dict[str, list[float]] = {}
        flat_formula_results = []
        for formula_vector in self.formula_vectors:
            weight = self._formula_weight(formula_vector)
            results = make_search_formula_vector_use_case("slt_vector").execute(
                formula_vector, top_k * 3
            )
            for r in results:
                post_id = str(r["post_id"])
                weighted_score_value = r["score"] * weight
                r["score"] = weighted_score_value
                flat_formula_results.append(r)
                formula_score_map.setdefault(post_id, []).append(weighted_score_value)

        formula_avg_map = {
            post_id: sum(scores) / len(scores)
            for post_id, scores in formula_score_map.items()
        }

        combined_scores = {}
        all_post_ids = set(text_map) | set(formula_avg_map)
        for post_id in all_post_ids:
            t_score = text_map.get(post_id, 0)
            f_score = formula_avg_map.get(post_id, 0)
            combined_scores[post_id] = weighted_score(t_score, f_score, alpha, beta)

        id_to_doc = {}
        for r in flat_formula_results:
            post_id = str(r["post_id"])
            if post_id not in id_to_doc:
                id_to_doc[post_id] = {"post_id": post_id}
            id_to_doc[post_id]["_score_formula"] = r["score"]
            if "source" in r:
                id_to_doc[post_id].update(r["source"])
        for r in text_results:
            post_id = str(r["post_id"])
            if post_id not in id_to_doc:
                id_to_doc[post_id] = {"post_id": post_id}
            id_to_doc[post_id]["_score_text"] = r["score"]
            if "source" in r:
                id_to_doc[post_id].update(r["source"])

        sorted_ids = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)[
            :top_k
        ]
        return [
            {**id_to_doc[pid], "_score": score}
            for pid, score in sorted_ids
            if pid in id_to_doc
        ]

    # -------------------- Approach 05 --------------------


def make_search_with_text_combined_with_formula_vector_use_case(
    text: str, formula_vectors: list[list[float]]
) -> SearchWithTextCombinedWithFormulaVectorUseCase:
    return SearchWithTextCombinedWithFormulaVectorUseCase(text, formula_vectors)
