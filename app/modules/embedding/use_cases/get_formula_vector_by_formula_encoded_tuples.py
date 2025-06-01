from services.tanget_cft_service import TangentCFTService
from lib.tangentS.math_tan.math_extractor import MathExtractor
from typing import List, Literal


class GetFormulaVectorByFormulaEncodedTuplesUseCase:
    def __init__(self, graph_type: Literal["SLT", "OPT", "SLT_TYPE"]):
        # Inicializa o módulo TangentCFT com o modelo pré-treinado
        if graph_type == "SLT":
            self.tangent_cft_service = TangentCFTService(
                "./lib/tangentCFT/trained_model/slt_model"
            )
        elif graph_type == "OPT":
            self.tangent_cft_service = TangentCFTService(
                "./lib/tangentCFT/trained_model/opt_model"
            )
        else:
            self.tangent_cft_service = TangentCFTService(
                "./lib/tangentCFT/trained_model/slt_type_model"
            )

    def execute(self, formula_encoded_tuples: List):
        try:
            vector = self.tangent_cft_service.get_query_vector(formula_encoded_tuples)
            return vector

        except Exception as e:
            # Registrar erro
            print(f"Erro ao processar fórmula: {e}")
            return None


def make_get_formula_vector_by_formula_encoded_tuples_use_case(
    graph_type: Literal["SLT", "OPT", "SLT_TYPE"],
):
    return GetFormulaVectorByFormulaEncodedTuplesUseCase(graph_type)
