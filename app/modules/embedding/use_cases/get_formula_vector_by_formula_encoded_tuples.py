from services.model_manager import model_manager
from typing import List, Literal


class GetFormulaVectorByFormulaEncodedTuplesUseCase:
    def __init__(self, graph_type: Literal["SLT", "OPT", "SLT_TYPE"]):
        self.graph_type = graph_type
        # Não carrega o modelo aqui, apenas armazena o tipo

    def execute(self, formula_encoded_tuples: List):
        try:
            # Pega o modelo do gerenciador (carrega apenas uma vez)
            tangent_cft_service = model_manager.get_model(self.graph_type)
            vector = tangent_cft_service.get_query_vector(formula_encoded_tuples)
            return vector

        except Exception as e:
            print(f"Erro ao processar fórmula: {e}")
            return None


def make_get_formula_vector_by_formula_encoded_tuples_use_case(
    graph_type: Literal["SLT", "OPT", "SLT_TYPE"],
):
    return GetFormulaVectorByFormulaEncodedTuplesUseCase(graph_type)
