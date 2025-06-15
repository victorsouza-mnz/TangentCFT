import numpy as np
from app.modules.search.use_cases.search_text_use_case import (
    make_search_text_use_case,
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
        self.formula_vectors = [np.array(f) for f in formula_vectors if f]

    def _fetch_text_results(self, top_k: int):
        return make_search_text_use_case().execute(self.text_vector, top_k)

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
        Texto + maior score de qualquer fórmula individual.
        """
        text_results = make_search_text_with_treated_formulas_use_case().execute(
            self.text, 10 * 3  # TODO: pq * 3 ?
        )

        text_map = {r["_id"]: r["_score"] for r in text_results}

        formula_results = []
        for formula in self.formula_vectors:
            formula_results += self._fetch_formula_results(formula, top_k * 3)
        formula_map = {}
        for r in formula_results:
            _id = r["_id"]
            formula_map[_id] = max(formula_map.get(_id, 0), r["_score"])

        combined_scores = {}
        all_ids = set(text_map.keys()) | set(formula_map.keys())
        for _id in all_ids:
            t_score = text_map.get(_id, 0)
            f_score = formula_map.get(_id, 0)
            combined_scores[_id] = weighted_score(t_score, f_score, alpha, beta)

        id_to_doc = {r["_id"]: r for r in text_results + formula_results}
        sorted_ids = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)[
            :top_k
        ]
        return [{**id_to_doc[_id], "_score": score} for _id, score in sorted_ids]

    # -------------------- Approach 02 --------------------
    def approach_2_mean_formula_score(
        self, top_k: int = 10, alpha: float = 0.5, beta: float = 0.5
    ):
        """
        Texto + média dos scores das fórmulas aplicadas ao post.
        """
        text_results = make_search_text_with_treated_formulas_use_case().execute(
            self.text, 10 * 3  # TODO: pq * 3 ?
        )
        text_map = {r["_id"]: r["_score"] for r in text_results}

        formula_results = self._fetch_all_formula_results(top_k * 3)
        formula_scores_map = {}
        for r in formula_results:
            _id = r["_id"]
            formula_scores_map.setdefault(_id, []).append(r["_score"])

        formula_avg_map = {
            _id: self._mean_formula_score(scores)
            for _id, scores in formula_scores_map.items()
        }

        combined_scores = {}
        all_ids = set(text_map.keys()) | set(formula_avg_map.keys())
        for _id in all_ids:
            t_score = text_map.get(_id, 0)
            f_score = formula_avg_map.get(_id, 0)
            combined_scores[_id] = weighted_score(t_score, f_score, alpha, beta)

        id_to_doc = {r["_id"]: r for r in text_results + formula_results}
        sorted_ids = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)[
            :top_k
        ]
        return [{**id_to_doc[_id], "_score": score} for _id, score in sorted_ids]

    # -------------------- Approach 03 --------------------
    def approach_3_individual_formula_max_weighted(
        self, top_k: int = 10, alpha: float = 0.5, beta: float = 0.5
    ):
        """
        Igual ao approach 1, mas fórmula com peso proporcional ao tamanho.
        """
        text_results = make_search_text_with_treated_formulas_use_case().execute(
            self.text, 10 * 3  # TODO: pq * 3 ?
        )
        text_map = {r["_id"]: r["_score"] for r in text_results}

        formula_results = []
        for formula in self.formula_vectors:
            weight = self._formula_weight(formula)
            raw_results = self._fetch_formula_results(formula, top_k * 3)
            for r in raw_results:
                r["_score"] *= weight
            formula_results += raw_results

        formula_map = {}
        for r in formula_results:
            _id = r["_id"]
            formula_map[_id] = max(formula_map.get(_id, 0), r["_score"])

        combined_scores = {}
        all_ids = set(text_map.keys()) | set(formula_map.keys())
        for _id in all_ids:
            t_score = text_map.get(_id, 0)
            f_score = formula_map.get(_id, 0)
            combined_scores[_id] = weighted_score(t_score, f_score, alpha, beta)

        id_to_doc = {r["_id"]: r for r in text_results + formula_results}
        sorted_ids = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)[
            :top_k
        ]
        return [{**id_to_doc[_id], "_score": score} for _id, score in sorted_ids]

    # -------------------- Approach 04 --------------------
    def approach_4_mean_formula_score_weighted(
        self, top_k: int = 10, alpha: float = 0.5, beta: float = 0.5
    ):
        """
        Igual ao approach 2, mas fórmula com peso proporcional ao tamanho.
        """
        text_results = make_search_text_with_treated_formulas_use_case().execute(
            self.text, 10 * 3  # TODO: pq * 3 ?
        )
        text_map = {r["_id"]: r["_score"] for r in text_results}

        formula_results = []
        for formula in self.formula_vectors:
            weight = self._formula_weight(formula)
            raw_results = self._fetch_formula_results(formula, top_k * 3)
            for r in raw_results:
                r["_score"] *= weight
            formula_results += raw_results

        formula_scores_map = {}
        for r in formula_results:
            _id = r["_id"]
            formula_scores_map.setdefault(_id, []).append(r["_score"])

        formula_avg_map = {
            _id: self._mean_formula_score(scores)
            for _id, scores in formula_scores_map.items()
        }

        combined_scores = {}
        all_ids = set(text_map.keys()) | set(formula_avg_map.keys())
        for _id in all_ids:
            t_score = text_map.get(_id, 0)
            f_score = formula_avg_map.get(_id, 0)
            combined_scores[_id] = weighted_score(t_score, f_score, alpha, beta)

        id_to_doc = {r["_id"]: r for r in text_results + formula_results}
        sorted_ids = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)[
            :top_k
        ]
        return [{**id_to_doc[_id], "_score": score} for _id, score in sorted_ids]

    # -------------------- Approach 05 --------------------
    # Approach 07 – Fórmulas como filtro
    # Primeiro busca por fórmulas (com forte recall), depois re-rank com texto.


def make_search_with_text_combined_with_formula_vector_use_case(
    text: str, formula_vectors: list[list[float]]
) -> SearchWithTextCombinedWithFormulaVectorUseCase:
    return SearchWithTextCombinedWithFormulaVectorUseCase(text, formula_vectors)
