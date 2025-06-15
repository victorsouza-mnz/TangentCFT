from fastapi import FastAPI, Request
from pydantic import BaseModel

from app.modules.search.use_cases.separate_text_and_formulas import (
    make_separate_text_and_formulas_use_case,
)

from app.modules.search.use_cases.search_with_text_combined_with_formula_vector_use_case import (
    make_search_with_text_combined_with_formula_vector_use_case,
)

from app.modules.embedding.use_cases.get_text_vector import (
    make_get_text_vector_use_case,
)
from app.modules.search.use_cases.search_text_use_case import (
    make_search_text_use_case,
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
from app.modules.search.use_cases.search_formula_vector_use_case import (
    make_search_formula_vector_use_case,
)

from app.modules.shared.parse_html_to_text import parse_html_to_text


from fastapi.responses import JSONResponse

import traceback


app = FastAPI()


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
    result = make_search_text_use_case().execute(params.query, 10)
    return {"status": "ok", "top_posts": result}


@app.post("/search-text-with-treated-formulas")
async def search_text_with_treated_formulas(params: SearchReqParams):
    result = make_search_text_with_treated_formulas_use_case().execute(params.query, 10)
    return {"status": "ok", "top_posts": result}


@app.post("/search-text-vector")
async def search_text_vector(params: SearchReqParams):
    text_without_html = parse_html_to_text(params.query)
    print("text_without_html: ", text_without_html)
    result = make_search_text_vector_use_case().execute(text_without_html, 10)
    return {"status": "ok", "top_posts": result}


# check
@app.post("/search-with-text-without-formula-combined-with-slt-formula-vector")
async def search_with_text_combined_with_combined_formula_vector(
    params: SearchReqParams,
):
    text_without_formulas, formulas, formula_positions = (
        make_separate_text_and_formulas_use_case().execute(params.query)
    )

    # Store vectors as array of objects, each containing all vector types for one formula
    all_formula_vectors = []
    for formula in formulas:
        vectors_dict = (
            make_get_slt_opt_and_type_combined_formula_vector_use_case().execute(
                formula, vector_types=["slt"]
            )
        )
        if vectors_dict:
            all_formula_vectors.append(vectors_dict["slt_vector"])

    result_size = 10

    text_results = make_search_text_use_case().execute(
        text_without_formulas, result_size, field="text_without_formula"
    )

    formula_results = []
    for formula_vector in all_formula_vectors:
        formula_results.append(
            make_search_formula_vector_use_case(vector_type="slt_vector").execute(
                formula_vector, result_size
            )
        )

    # TODO combinar os resultados de text_results e formula_results baseado nos approachs

    # result_approach_1 = use_case.approach_1_individual_formula_max(result_size)

    # result_approach_2 = use_case.approach_2_mean_formula_score(result_size)

    # result_approach_3 = use_case.approach_3_individual_formula_max_weighted(result_size)

    # result_approach_4 = use_case.approach_4_mean_formula_score_weighted(result_size)

    return {
        "status": "ok",
    }


# TODO :  implements with vector
@app.post(
    "/search-with-text-without-formulas-vector-combined-with-combined-formula-vector"
)
async def search_with_text_without_formulas_vector_combined_with_slt_formula_vector(
    params: SearchReqParams,
):
    pass


@app.post("/search-with-latex-text-search-combined-with-combined-type-formula-vector")
async def search_with_text_without_formulas_vector_combined_with_slt_type_formula_vector(
    params: SearchReqParams,
):
    pass


@app.post("/search-with-latex-text-search-vector-combined-with-slt-type-formula-vector")
async def search_with_latex_text_search_vector_combined_with_combined_type_formula_vector(
    params: SearchReqParams,
):
    pass


@app.post(
    "/search-with-latex-text-search-vector-combined-with-combined-type-formula-vector"
)
async def search_with_latex_text_search_vector_combined_with_combined_type_formula_vector(
    params: SearchReqParams,
):
    pass


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
