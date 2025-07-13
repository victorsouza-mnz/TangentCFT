# Arquivo de compatibilidade para modelos salvos com referência ao módulo tangent_cft_model
# Importa a classe do local atual para manter compatibilidade com modelos pré-treinados

from lib.tangentCFT.model import TangentCftModel, ProgressCallback

# Re-exporta as classes para que o pickle possa encontrá-las
__all__ = ["TangentCftModel", "ProgressCallback"]
