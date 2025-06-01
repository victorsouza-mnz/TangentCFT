# app/modules/search/use_cases/encode_formula_tuples.py
from typing import List, Literal
from services.tanget_cft_service import TangentCFTService


class EncodeFormulaTuplesUseCase:
    def __init__(self):
        self.service = TangentCFTService()

    def execute(
        self,
        formula_tuples: List[str],
        encoder_type: Literal["SLT", "OPT", "SLT_TYPE"],
        embedding_type: int = None,
        tokenize_numbers: bool = None,
    ) -> List[str]:
        """
        Encodifica as tuplas da fórmula usando o serviço TangentCFT

        Args:
            formula_tuples: Lista de tuplas extraídas de uma fórmula
            encoder_type: Tipo de encoder (SLT, OPT, ou SLT_TYPE)
            embedding_type: Tipo de embeddings a serem usados
            tokenize_numbers: Determina se os números devem ser tokenizados

        Returns:
            Lista de tuplas encodificadas
        """
        return self.service.encode_formula_tuples(
            formula_tuples,
            encoder_type,
            embedding_type,
            tokenize_numbers,
        )


def make_encode_formula_tuples_use_case() -> EncodeFormulaTuplesUseCase:
    """Factory function para criar o caso de uso de encodificação de tuplas de fórmulas"""
    return EncodeFormulaTuplesUseCase()
