# app/modules/search/use_cases/encode_formula_tuples.py
from typing import List
from services.tanget_cft_service import TangentCFTService


class EncodeFormulaTuplesUseCase:
    def __init__(self):
        self.service = TangentCFTService()

    def execute(self, formula_tuples: List[str]) -> List[str]:
        """
        Encodifica as tuplas da fórmula usando o serviço TangentCFT

        Args:
            formula_tuples: Lista de tuplas extraídas de uma fórmula

        Returns:
            Lista de tuplas encodificadas
        """
        return self.service.encode_formula_tuples(formula_tuples)


def make_encode_formula_tuples_use_case() -> EncodeFormulaTuplesUseCase:
    """Factory function para criar o caso de uso de encodificação de tuplas de fórmulas"""
    return EncodeFormulaTuplesUseCase()
