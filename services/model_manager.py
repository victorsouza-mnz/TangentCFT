from services.tanget_cft_service import TangentCFTService
from typing import Dict, Literal


class ModelManager:
    """
    Gerenciador singleton para carregar e reutilizar modelos TangentCFT
    """

    _instance = None
    _models: Dict[str, TangentCFTService] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ModelManager, cls).__new__(cls)
        return cls._instance

    def get_model(
        self, model_type: Literal["SLT", "OPT", "SLT_TYPE"]
    ) -> TangentCFTService:
        """
        Retorna uma instância do modelo, carregando apenas se necessário
        """
        if model_type not in self._models:
            print(f"🔄 Carregando modelo {model_type} pela primeira vez...")

            if model_type == "SLT":
                model_path = "./lib/tangentCFT/trained_model/slt_model"
            elif model_type == "OPT":
                model_path = "./lib/tangentCFT/trained_model/opt_model"
            else:  # SLT_TYPE
                model_path = "./lib/tangentCFT/trained_model/slt_type_model"

            self._models[model_type] = TangentCFTService(model_path)
            print(f"✅ Modelo {model_type} carregado com sucesso!")

        return self._models[model_type]


# Instância global
model_manager = ModelManager()
