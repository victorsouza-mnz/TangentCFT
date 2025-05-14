from sentence_transformers import SentenceTransformer


class GetTextVectorUseCase:
    model: SentenceTransformer

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)

    def execute(self, text: str):
        embedding = self.model.encode(
            text, convert_to_numpy=True, normalize_embeddings=True
        )
        return embedding


def make_get_text_vector_use_case():
    return GetTextVectorUseCase("all-MiniLM-L6-v2")
