from bs4 import BeautifulSoup, NavigableString
from typing import List, Tuple


class SeparateTextAndFormulasUseCase:
    def __init__(self, content_type: str):
        self.content_type = content_type

    def execute(self, content: str) -> Tuple[str, List[str], List[int]]:
        if self.content_type != "mathml":
            raise ValueError("Content type not supported")

        soup = BeautifulSoup(content, "html.parser")

        formulas = []
        formula_positions = []
        current_offset = 0
        clean_text_parts = []

        def extract_text_and_formulas(node):
            nonlocal current_offset

            if isinstance(node, NavigableString):
                text = str(node)
                clean_text_parts.append(text)
                current_offset += len(text)
            elif node.name == "math":
                formula_str = str(node)
                formulas.append(formula_str)
                formula_positions.append(current_offset)
                clean_text_parts.append(" ")  # espaço no lugar da fórmula
                current_offset += 1
            elif node.name:
                for child in node.children:
                    extract_text_and_formulas(child)

        extract_text_and_formulas(soup)

        clean_text = " ".join("".join(clean_text_parts).split())
        return clean_text, formulas, formula_positions


def make_separate_text_and_formulas_use_case():
    return SeparateTextAndFormulasUseCase(content_type="mathml")
