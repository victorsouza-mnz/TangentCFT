from services.tanget_cft_service import TangentCFTService
from TangentS.math_tan.math_extractor import MathExtractor


class GetFormulaVectorUseCase:
    def __init__(self):
        # Inicializa o módulo TangentCFT com o modelo pré-treinado
        self.tangent_cft_service = TangentCFTService(
            "./lib/tangentCFT/trained_data/slt_model"
        )

    def execute(self, formula: str):
        try:
            # Extrai as árvores de símbolos da fórmula MathML
            symbol_trees = MathExtractor.parse_from_xml(
                formula,
                content_id=1,  # ID temporário
                operator=False,  # Usar SLT (Symbol Layout Tree)
                missing_tags=None,
                problem_files=None,
            )

            # Para cada árvore extraída, gera pares de tuplas
            for idx, tree in symbol_trees.items():
                tuples = tree.get_pairs(window=2, eob=True)

                # Obtém o vetor da fórmula usando as tuplas
                if tuples:
                    vector = self.tangent_cft_service.get_query_vector(tuples)
                    return vector

        except Exception as e:
            # Registrar erro
            print(f"Erro ao processar fórmula: {e}")
            return None


def make_get_formula_vector_use_case():
    return GetFormulaVectorUseCase()
