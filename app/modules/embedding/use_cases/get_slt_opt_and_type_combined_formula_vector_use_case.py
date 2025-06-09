from app.modules.embedding.use_cases.get_formula_vector_by_formula_encoded_tuples import (
    make_get_formula_vector_by_formula_encoded_tuples_use_case,
)
from app.modules.embedding.use_cases.parse_formula_to_tuples import (
    make_parse_formula_to_tuples_use_case,
)
from app.modules.embedding.use_cases.encode_formula_tuples import (
    make_encode_formula_tuples_use_case,
)

from lib.tangentCFT.touple_encoder.encoder import TupleTokenizationMode


class EncodeFormulaTuplesUseCaseParams(Enum):
    SLT = {
        "encoder_type": "SLT",
        "embedding_type": TupleTokenizationMode.Both_Separated,
        "tokenize_numbers": True,
    }

    SLT_TYPE = {
        "encoder_type": "SLT_TYPE",
        "embedding_type": TupleTokenizationMode.Type,
        "tokenize_numbers": False,
    }

    OPT = {
        "encoder_type": "OPT",
        "embedding_type": TupleTokenizationMode.Both_Separated,
        "tokenize_numbers": False,
    }


class GetSLTOptAndTypeCombinedFormulaVectorUseCase:

    def execute(self, formula: str):
        # TODO: aqui vai ser diferente para cada tipo de embedding
        # Ainda assim ta errado, tenho que pensar em uma forma de mandar o opt, se mandar essa formula direto
        # vai dar merda.
        slt_and_slt_type_formula_tuples = (
            make_parse_formula_to_tuples_use_case().execute(formula, operator=False)
        )
        opt_formula_tuples = make_parse_formula_to_tuples_use_case().execute(
            formula, operator=True
        )

        if not slt_and_slt_type_formula_tuples or not opt_formula_tuples:
            print(f"No tuples generated for formula {formula}, skipping...")
            return None

        slt_encoded_tuples = make_encode_formula_tuples_use_case().execute(
            slt_and_slt_type_formula_tuples,
            **EncodeFormulaTuplesUseCaseParams.SLT.value,
        )

        slt_type_encoded_tuples = make_encode_formula_tuples_use_case().execute(
            slt_and_slt_type_formula_tuples,
            **EncodeFormulaTuplesUseCaseParams.SLT_TYPE.value,
        )

        opt_encoded_tuples = make_encode_formula_tuples_use_case().execute(
            opt_formula_tuples,
            **EncodeFormulaTuplesUseCaseParams.OPT.value,
        )

        slt_vector = make_get_formula_vector_by_formula_encoded_tuples_use_case(
            "SLT"
        ).execute(slt_encoded_tuples)

        opt_vector = make_get_formula_vector_by_formula_encoded_tuples_use_case(
            "OPT"
        ).execute(opt_encoded_tuples)

        slt_type_vector = make_get_formula_vector_by_formula_encoded_tuples_use_case(
            "SLT_TYPE"
        ).execute(slt_type_encoded_tuples)

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
