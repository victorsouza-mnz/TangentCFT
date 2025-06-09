# app/modules/search/use_cases/convert_formula_to_tuples.py
from typing import List
from lib.tangentS.math_tan.math_extractor import MathExtractor


class ParseFormulaToTuplesUseCase:
    def execute(self, formula: str, operator: bool = False) -> List[str]:
        """
        Converte uma fórmula MathML em uma lista de tuplas SLT ou OPT dependendo do valor de operator

        Args:
            formula: String contendo a fórmula em formato MathML

        Returns:
            Lista de tuplas SLT ou OPT
        """
        try:
            # Converter MathML para Symbol Layout Tree
            # Even when send only one formula, the result is a dictionary of SymbolTrees
            trees = MathExtractor.parse_from_xml(
                formula,
                content_id=1,  # ID temporário
                operator=operator,
                missing_tags=None,
                problem_files=None,
            )

            for key in trees:
                tuples = trees[key].get_pairs(window=2, eob=True)
                """
                Because we're only sending one formula we can return the first tuple
                (slt_trees should have only one item any way)
                """
                return tuples

            # Se não houver formulas
            return []
        except Exception as e:
            import traceback

            print(f"Erro ao converter fórmula para tuplas: {str(e)}")
            print("Stacktrace:")
            print(traceback.format_exc())
            return []


def make_parse_formula_to_tuples_use_case() -> ParseFormulaToTuplesUseCase:
    """Factory function para criar o caso de uso de conversão de fórmulas para tuplas"""
    return ParseFormulaToTuplesUseCase()
