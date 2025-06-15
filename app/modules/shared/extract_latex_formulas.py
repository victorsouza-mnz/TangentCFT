import re
from typing import List


def get_latex_formulas_larger_than_5_with_only_dollar_delimiters(
    text: str,
) -> List[str]:
    # Regex abrangente para capturar várias notações LaTeX
    latex_pattern = re.compile(
        r"(\$\$([\s\S]*?)\$\$|\$([^\n]*?)\$|\\\[(.*?)\\\]|\\begin\{.*?\}([\s\S]*?)\\end\{.*?\})",
        re.MULTILINE,
    )
    matches = latex_pattern.findall(text)

    formulas = []

    for match in matches:
        # Pegamos o primeiro grupo não vazio dentre os grupos internos
        inner_formula = next((g for g in match[1:] if g and len(g.strip()) > 5), None)
        if inner_formula:
            # Normaliza sempre como $...$ igual no JS
            formulas.append(f"${inner_formula.strip()}$")

    return formulas
