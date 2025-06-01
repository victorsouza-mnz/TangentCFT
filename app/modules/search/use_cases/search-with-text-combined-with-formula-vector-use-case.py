from app.modules.search.use_cases.search_pure_text_use_case import (
    make_search_pure_text_use_case,
)


class SearchWithTextCombinedWithFormulaVectorUseCase:
    def __init__(self, text_vector: str, formula_vectors: list[str]):
        self.text_vector = text_vector
        self.formula_vectors = formula_vectors

    def weighted_sum(self, top_k: int = 10):
        """Faz busca vetorial no texto e nas fórmulas e combina os scores com pesos."""
        text_results = make_search_pure_text_use_case().execute(
            self.text_vector, top_k * 3
        )

        formula_results = make_search_formula_vector_use_case().execute(
            self.formula_vectors, top_k * 3
        )


def make_search_with_text_combined_with_formula_vector_use_case(
    text_vector: str, formula_vectors: list[str]
):
    return SearchWithTextCombinedWithFormulaVectorUseCase(text_vector, formula_vectors)
