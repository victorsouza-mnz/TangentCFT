from services.tanget_cft_service import TangentCFTService
from lib.tangentS.math_tan.math_extractor import MathExtractor
from typing import List


class GetFormulaVectorByFormulaEncodedTuplesUseCase:
    def __init__(self):
        # Inicializa o módulo TangentCFT com o modelo pré-treinado
        self.tangent_cft_service = TangentCFTService(
            "./lib/tangentCFT/trained_model/slt_model"
        )

    def execute(self, formula_encoded_tuples: List):
        try:
            vector = self.tangent_cft_service.get_query_vector(formula_encoded_tuples)
            return vector

        except Exception as e:
            # Registrar erro
            print(f"Erro ao processar fórmula: {e}")
            return None


def make_get_formula_vector_by_formula_encoded_tuples_use_case():
    return GetFormulaVectorByFormulaEncodedTuplesUseCase()
