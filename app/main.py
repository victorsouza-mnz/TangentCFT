from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import re
from bs4 import BeautifulSoup
from tangent_cft_module import TangentCFTModule
import torch

from app.modules.search.use_cases.separate_text_and_formulas import (
    make_separate_text_and_formulas_use_case,
)

from app.modules.embedding.use_cases.parse_formula_to_tuples import (
    make_parse_formula_to_tuples_use_case,
)

from app.modules.embedding.use_cases.encode_formula_tuples import (
    make_encode_formula_tuples_use_case,
)

from app.modules.search.use_cases.get_formula_vector_by_formula_encoded_tuples import (
    make_get_formula_vector_by_formula_encoded_tuples_use_case,
)
from app.modules.search.use_cases.get_text_vector import make_get_text_vector_use_case

app = FastAPI()


@app.get("/health")
async def health():
    return {"status": "ok"}


class SearchReqParams(BaseModel):
    query: str


@app.post("/search")
async def search(params: SearchReqParams):

    text, formulas, formula_positions = (
        make_separate_text_and_formulas_use_case().execute(params.query)
    )

    formula_vectors = []

    for formula in formulas:

        formula_tuples = make_parse_formula_to_tuples_use_case().execute(formula)

        encoded_tuples = make_encode_formula_tuples_use_case().execute(formula_tuples)

        vector = make_get_formula_vector_by_formula_encoded_tuples_use_case().execute(
            encoded_tuples
        )

        formula_vectors.append(vector)

    text_vector = make_get_text_vector_use_case().execute(text)

    # # TODO: realizar busca
    # results = make_formula_retrieval_use_case().execute(
    #     collection_tensor, formula_index, query_vector, top_k=10
    # )
    # # TODO: retornar resultados

    # Convert numpy arrays to lists for JSON serialization
    serializable_vectors = [
        vector.tolist() if vector is not None else None for vector in formula_vectors
    ]

    return {
        "original_text": params.query,
        "text": text,
        "text_vector": text_vector.tolist(),
        "text_vector_dims": len(text_vector),
        "formulas": formulas,
        "formula_positions": formula_positions,
        "formula_vectors": serializable_vectors,
        "formula_vectors_dims": [
            len(v) if v is not None else None for v in formula_vectors
        ],
    }


# ####### migrar codigo abaixo

# # Inicializar o modelo TangentCFT
# model = TangentCFTModule(
#     "slt_model.wv.vectors.npy"
# )  # Ajuste o caminho do modelo conforme necessário


# class SearchQuery(BaseModel):
#     content: str


# def extract_mathml_and_text(content: str):
#     """
#     Separa o texto e as fórmulas MathML do conteúdo.
#     Retorna uma tupla (texto, lista_de_formulas_mathml)
#     """
#     soup = BeautifulSoup(content, "xml")

#     # Encontrar todas as fórmulas MathML
#     mathml_elements = soup.find_all("math")
#     formulas = [str(math) for math in mathml_elements]

#     # Remover as fórmulas do texto original para obter apenas o texto
#     text = content
#     for formula in formulas:
#         text = text.replace(formula, " ")

#     # Limpar espaços extras
#     text = " ".join(text.split())

#     return text, formulas


# @app.post("/search")
# async def search(query: SearchQuery):
#     try:
#         # Separar texto e fórmulas
#         text, formulas = extract_mathml_and_text(query.content)

#         if not formulas:
#             raise HTTPException(
#                 status_code=400, detail="No MathML formulas found in the query"
#             )

#         # Por enquanto, vamos processar apenas a primeira fórmula encontrada
#         formula = formulas[0]

#         # TODO: Aqui você precisará implementar a conversão da fórmula MathML
#         # para o formato de tuplas que o TangentCFT espera
#         # Esta é uma implementação simplificada

#         # Obter o vetor da query
#         query_vector = model.get_query_vector([formula])  # Você precisará ajustar isso

#         # Realizar a busca
#         # Você precisará implementar a parte de carregar collection_tensor e formula_index
#         results = model.formula_retrieval(
#             collection_tensor, formula_index, query_vector, top_k=10
#         )

#         return {"text": text, "formula": formula, "results": results}

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
