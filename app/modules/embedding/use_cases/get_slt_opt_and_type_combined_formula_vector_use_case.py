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
from enum import Enum
from typing import List, Optional, Dict, Any


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

    def execute(
        self,
        formula: str,
        vector_types: List[str] = ["slt", "slt_type", "opt", "combined"],
    ):
        """
        Generate formula vectors for specified representations.

        Args:
            formula: Formula string to process
            vector_types: List of vector types to generate. Options: "slt", "slt_type", "opt", "combined"

        Returns:
            Dictionary with requested vector types:
            {
                "slt_vector": numpy array (if requested),
                "slt_type_vector": numpy array (if requested),
                "opt_vector": numpy array (if requested),
                "formula_vector": numpy array (combined, if requested)
            }
            Returns None if formula cannot be processed.
        """
        result = {}

        # Normalize vector_types to lowercase
        vector_types = [vt.lower() for vt in vector_types]

        # Check if we need SLT or SLT_TYPE vectors
        need_slt_tuples = (
            "slt" in vector_types
            or "slt_type" in vector_types
            or "combined" in vector_types
        )
        need_opt_tuples = "opt" in vector_types or "combined" in vector_types

        # Parse formula tuples only if needed
        slt_and_slt_type_formula_tuples = None
        opt_formula_tuples = None

        if need_slt_tuples:
            slt_and_slt_type_formula_tuples = (
                make_parse_formula_to_tuples_use_case().execute(formula, operator=False)
            )
            if not slt_and_slt_type_formula_tuples:
                print(f"No SLT tuples generated for formula {formula}, skipping...")
                return None

        if need_opt_tuples:
            opt_formula_tuples = make_parse_formula_to_tuples_use_case().execute(
                formula, operator=True
            )
            if not opt_formula_tuples:
                print(f"No OPT tuples generated for formula {formula}, skipping...")
                return None

        # Generate vectors only for requested types
        slt_vector = None
        slt_type_vector = None
        opt_vector = None

        if "slt" in vector_types or "combined" in vector_types:
            slt_encoded_tuples = make_encode_formula_tuples_use_case().execute(
                slt_and_slt_type_formula_tuples,
                **EncodeFormulaTuplesUseCaseParams.SLT.value,
            )
            slt_vector = make_get_formula_vector_by_formula_encoded_tuples_use_case(
                "SLT"
            ).execute(slt_encoded_tuples)
            result["slt_vector"] = slt_vector

        if "slt_type" in vector_types or "combined" in vector_types:
            slt_type_encoded_tuples = make_encode_formula_tuples_use_case().execute(
                slt_and_slt_type_formula_tuples,
                **EncodeFormulaTuplesUseCaseParams.SLT_TYPE.value,
            )
            slt_type_vector = (
                make_get_formula_vector_by_formula_encoded_tuples_use_case(
                    "SLT_TYPE"
                ).execute(slt_type_encoded_tuples)
            )
            result["slt_type_vector"] = slt_type_vector

        if "opt" in vector_types or "combined" in vector_types:
            opt_encoded_tuples = make_encode_formula_tuples_use_case().execute(
                opt_formula_tuples,
                **EncodeFormulaTuplesUseCaseParams.OPT.value,
            )
            opt_vector = make_get_formula_vector_by_formula_encoded_tuples_use_case(
                "OPT"
            ).execute(opt_encoded_tuples)
            result["opt_vector"] = opt_vector

        if "combined" in vector_types:
            if (
                slt_vector is not None
                and opt_vector is not None
                and slt_type_vector is not None
            ):
                combined_vector = combine_vector(
                    slt_vector, opt_vector, slt_type_vector
                )
                result["formula_vector"] = combined_vector
            else:
                print(
                    "Cannot create combined vector: missing required component vectors"
                )

        return result


def make_get_slt_opt_and_type_combined_formula_vector_use_case() -> (
    GetSLTOptAndTypeCombinedFormulaVectorUseCase
):
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
