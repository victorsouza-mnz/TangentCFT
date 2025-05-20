# app/modules/search/use_cases/convert_formula_to_tuples.py
from typing import List
from lib.tangentS.math_tan.math_extractor import MathExtractor


class ParseFormulaToTuplesUseCase:
    def execute(self, formula: str) -> List[str]:
        """
        Converte uma fórmula MathML em uma lista de tuplas SLT

        Args:
            formula: String contendo a fórmula em formato MathML

        Returns:
            Lista de tuplas SLT
        """
        try:
            # Converter MathML para Symbol Layout Tree
            symbol_trees = MathExtractor.parse_from_xml(
                formula,
                content_id=1,  # ID temporário
                operator=False,  # Usar SLT (Symbol Layout Tree)
                missing_tags=None,
                problem_files=None,
            )

            # Gerar tuplas a partir da SLT
            # Para cada árvore extraída, gera pares de tuplas
            for _, tree in symbol_trees.items():

                tuples = tree.get_pairs(window=2, eob=True)

            return tuples
        except Exception as e:
            print(f"Erro ao converter fórmula para tuplas: {str(e)}")
            return []


def make_parse_formula_to_tuples_use_case() -> ParseFormulaToTuplesUseCase:
    """Factory function para criar o caso de uso de conversão de fórmulas para tuplas"""
    return ParseFormulaToTuplesUseCase()
