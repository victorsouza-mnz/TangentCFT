from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import re
from bs4 import BeautifulSoup
from tangent_cft_module import TangentCFTModule
import torch

from app.modules.search.use_cases.separate_text_and_formulas import (
    make_separate_text_and_formulas_use_case,
)

from app.modules.search.use_cases.search_with_text_combined_with_formula_vector_use_case import (
    make_search_with_text_combined_with_formula_vector_use_case,
)

from app.modules.embedding.use_cases.get_text_vector import (
    make_get_text_vector_use_case,
)
from app.modules.search.use_cases.search_pure_text_use_case import (
    make_search_pure_text_use_case,
)
from app.modules.search.use_cases.search_text_with_treated_latex_use_case import (
    make_search_text_with_treated_latex_use_case,
)
from app.modules.search.use_cases.search_with_text_vector_use_case import (
    make_search_text_vector_use_case,
)
from app.modules.embedding.use_cases.get_slt_opt_and_type_combined_formula_vector_use_case import (
    make_get_slt_opt_and_type_combined_formula_vector_use_case,
)

app = FastAPI()


@app.get("/health")
async def health():
    return {"status": "ok"}


class SearchReqParams(BaseModel):
    query: str


# OK
@app.post("/search-pure-text")
async def search_pure_text(params: SearchReqParams):
    result = make_search_pure_text_use_case().execute(params.query, 10)
    return {"status": "ok", "top_posts": result}


# OK
@app.post("/search-text-with-treated-latex")
async def search_text_with_treated_latex(params: SearchReqParams):
    result = make_search_text_with_treated_latex_use_case().execute(params.query, 10)
    return {"status": "ok", "top_posts": result}


# ok
@app.post("/search-text-vector")
async def search_text_vector(params: SearchReqParams):
    text_without_formulas = make_separate_text_and_formulas_use_case().execute(
        params.query
    )
    result = make_search_text_vector_use_case().execute(text_without_formulas, 10)
    return {"status": "ok", "top_posts": result}


@app.post("/search-with-text-combined-with-combined-formula-vector")
async def search_with_text_combined_with_combined_formula_vector(
    params: SearchReqParams,
):
    text_without_formulas, formulas = (
        make_separate_text_and_formulas_use_case().execute(params.query)
    )

    text_vector = make_get_text_vector_use_case().execute(text_without_formulas)

    formula_vectors = []

    for formula in formulas:

        formula_vector = (
            make_get_slt_opt_and_type_combined_formula_vector_use_case().execute(
                formula
            )
        )

        formula_vectors.append(formula_vector)

    result_approach_1 = (
        make_search_with_text_combined_with_formula_vector_use_case().execute(
            text_vector, formula_vectors, 10
        )
    )

    result_approach_2 = (
        make_search_with_text_combined_with_formula_vector_use_case().execute(
            text_vector, formula_vectors, 10
        )
    )

    # ...
    # Other approaches
    # ...
    return {
        "status": "ok",
        "top_posts_approach_1": result_approach_1,
        "top_posts_approach_2": result_approach_2,
    }


@app.post("/search-with-text-combined-with-slt-vector")
async def search_with_text_combined_with_formula_vector_and_slt_type(
    params: SearchReqParams,
):
    pass


@app.post("/search-with-text-combined-with-slt-type-vector")
async def search_with_text_combined_with_formula_vector_and_slt_type(
    params: SearchReqParams,
):
    pass


@app.post("/search-with-text-combined-with-opt-vector")
async def search_with_text_combined_with_formula_vector_and_opt_type(
    params: SearchReqParams,
):
    pass


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
