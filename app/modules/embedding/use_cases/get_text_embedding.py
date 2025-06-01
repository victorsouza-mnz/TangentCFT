from sentence_transformers import SentenceTransformer


class GetTextEmbeddingUseCase:
    model: SentenceTransformer

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)

    def execute(self, text: str):
        embedding = self.model.encode(
            text, convert_to_numpy=True, normalize_embeddings=True
        )
        return embedding.tolist()  # Convertido para lista para uso com Elasticsearch


def make_get_text_embedding_use_case():
    return GetTextEmbeddingUseCase("all-MiniLM-L6-v2")
