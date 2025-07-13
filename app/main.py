from fastapi import FastAPI, Request
from pydantic import BaseModel
from services.model_manager import model_manager

from app.modules.search.use_cases.separate_text_and_formulas import (
    make_separate_text_and_formulas_use_case,
)

from app.modules.search.use_cases.search_with_text_combined_with_formula_vector_use_case import (
    make_search_with_text_combined_with_formula_vector_use_case,
)

from app.modules.search.use_cases.search_text_field_use_case import (
    make_search_text_field_use_case,
)
from app.modules.search.use_cases.search_text_with_treated_formulas_use_case import (
    make_search_text_with_treated_formulas_use_case,
)
from app.modules.search.use_cases.search_with_text_vector_use_case import (
    make_search_text_vector_use_case,
)
from app.modules.embedding.use_cases.get_slt_opt_and_type_combined_formula_vector_use_case import (
    make_get_slt_opt_and_type_combined_formula_vector_use_case,
)

from app.modules.shared.parse_html_to_text import parse_html_to_text


from fastapi.responses import JSONResponse

import traceback


app = FastAPI()


@app.on_event("startup")
async def startup_event():
    """
    Carrega todos os modelos na inicialização do servidor
    """
    print("🚀 Iniciando servidor e carregando modelos...")

    # Pré-carrega todos os modelos
    model_manager.get_model("SLT")
    model_manager.get_model("OPT")
    model_manager.get_model("SLT_TYPE")

    print("✅ Todos os modelos carregados! Servidor pronto.")


@app.middleware("http")
async def catch_exceptions_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        error_details = {
            "status": "error",
            "error_type": type(e).__name__,
            "error_message": str(e),
            "traceback": traceback.format_exc(),
        }
        return JSONResponse(status_code=500, content={"detail": error_details})


@app.get("/health")
async def health():
    return {"status": "ok"}


class SearchReqParams(BaseModel):
    query: str


@app.post("/search-pure-text")
async def search_pure_text(params: SearchReqParams):
    result = make_search_text_field_use_case().execute(params.query, 10)
    return {"status": "ok", "top_posts": result}


@app.post("/search-text-with-treated-formulas")
async def search_text_with_treated_formulas(params: SearchReqParams):
    result = make_search_text_with_treated_formulas_use_case().execute(params.query, 10)
    return {"status": "ok", "top_posts": result}


@app.post("/search-text-vector")
async def search_text_vector(params: SearchReqParams):
    text_without_html = parse_html_to_text(params.query)
    result = make_search_text_vector_use_case().execute(text_without_html, 10)
    return {"status": "ok", "top_posts": result}


# check
@app.post("/search-with-text-without-formula-combined-with-slt-formula-vector")
async def search_with_text_combined_with_combined_formula_vector(
    params: SearchReqParams,
):
    # 1. Separar texto e fórmulas
    text_without_formulas, formulas, _ = (
        make_separate_text_and_formulas_use_case().execute(params.query)
    )

    # 2. Gerar vetores SLT para as fórmulas
    all_formula_vectors = []

    for formula in formulas:
        vectors_dict = (
            make_get_slt_opt_and_type_combined_formula_vector_use_case().execute(
                formula, vector_types=["slt"]
            )
        )
        if vectors_dict:
            all_formula_vectors.append(vectors_dict["slt_vector"])

    # 3. Criar use case de combinação
    combined_search_use_case = (
        make_search_with_text_combined_with_formula_vector_use_case(
            text_without_formulas,
            all_formula_vectors,
        )
    )

    # 4. Executar os approaches
    result_size = 10

    result_approach_1 = combined_search_use_case.approach_1_individual_formula_max(
        top_k=result_size
    )
    result_approach_2 = combined_search_use_case.approach_2_mean_formula_score(
        top_k=result_size
    )
    result_approach_3 = (
        combined_search_use_case.approach_3_individual_formula_max_weighted(
            top_k=result_size
        )
    )
    result_approach_4 = combined_search_use_case.approach_4_mean_formula_score_weighted(
        top_k=result_size
    )

    # 5. Retornar resultados de todos os approaches
    return {
        "status": "ok",
        "query": params.query,
        "text_without_formulas": text_without_formulas,
        "num_formulas": len(formulas),
        "results": {
            "approach_1_individual_formula_max": result_approach_1,
            "approach_2_mean_formula_score": result_approach_2,
            "approach_3_individual_formula_max_weighted": result_approach_3,
            "approach_4_mean_formula_score_weighted": result_approach_4,
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, timeout_keep_alive=1000)
