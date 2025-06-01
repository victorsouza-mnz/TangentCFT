from app.modules.embedding.use_cases.get_formula_vector_by_formula_encoded_tuples import (
    make_get_formula_vector_by_formula_encoded_tuples_use_case,
)
from app.modules.embedding.use_cases.parse_formula_to_tuples import (
    make_parse_formula_to_tuples_use_case,
)
from app.modules.embedding.use_cases.encode_formula_tuples import (
    make_encode_formula_tuples_use_case,
)


class GetSLTOptAndTypeCombinedFormulaVectorUseCase:

    def execute(self, formula: str):
        formula_tuples = make_parse_formula_to_tuples_use_case().execute(formula)

        encoded_tuples = make_encode_formula_tuples_use_case().execute(formula_tuples)

        slt_vector = make_get_formula_vector_by_formula_encoded_tuples_use_case(
            "SLT"
        ).execute(encoded_tuples)

        opt_vector = make_get_formula_vector_by_formula_encoded_tuples_use_case(
            "OPT"
        ).execute(encoded_tuples)

        slt_type_vector = make_get_formula_vector_by_formula_encoded_tuples_use_case(
            "SLT_TYPE"
        ).execute(encoded_tuples)

        combined_vector = combine_vector(slt_vector, opt_vector, slt_type_vector)

        return combined_vector


def make_get_slt_opt_and_type_combined_formula_vector_use_case():
    return GetSLTOptAndTypeCombinedFormulaVectorUseCase()


def combine_vector(slt_vector, opt_vector, slt_type_vector):
    """
    Combines three vectors by addition.

    Args:
        slt_vector: Vector representation from SLT encoding
        opt_vector: Vector representation from OPT encoding
        slt_type_vector: Vector representation from SLT_TYPE encoding

    Returns:
        The combined vector (sum of all input vectors)
    """
    combined = slt_vector.copy()
    combined = combined + opt_vector
    combined = combined + slt_type_vector

    return combined
