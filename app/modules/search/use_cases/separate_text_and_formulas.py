from bs4 import BeautifulSoup
import re


class SeparateTextAndFormulasUseCase:
    def __init__(self, content_type: str):
        self.content_type = content_type

    def execute(self, content: str):
        if self.content_type != "mathml":
            raise ValueError("Content type not supported")

        # Remover tags HTML mas preservar conteúdo e tags math
        content = self._strip_html_preserve_math(content)

        text = self._normalize_whitespace(content)
        mathml_regex = self._get_mathml_regex()

        formulas, formula_positions, text = self._extract_formulas_and_positions(
            text, mathml_regex
        )

        text = self._normalize_whitespace(text)
        return text, formulas, formula_positions

    def _strip_html_preserve_math(self, content: str) -> str:
        # Salvar temporariamente as tags math com marcadores únicos
        math_tags = []
        math_regex = self._get_mathml_regex()

        def replace_math(match):
            math_tags.append(match.group(0))
            return f"[MATH_PLACEHOLDER_{len(math_tags)-1}]"

        # Substituir tags math por placeholders
        content_with_placeholders = math_regex.sub(replace_math, content)

        # Remover todas as tags HTML restantes
        soup = BeautifulSoup(content_with_placeholders, "html.parser")
        text_only = soup.get_text()

        # Restaurar as tags math
        for i, math_tag in enumerate(math_tags):
            text_only = text_only.replace(f"[MATH_PLACEHOLDER_{i}]", math_tag)

        return text_only

    def _normalize_whitespace(self, text: str) -> str:
        return " ".join(text.split())

    def _get_mathml_regex(self) -> re.Pattern:
        return re.compile(r"<math[\s\S]*?</math>")

    def _extract_formulas_and_positions(
        self, text: str, mathml_regex: re.Pattern
    ) -> tuple[list, list, str]:
        formulas = []
        formula_positions = []

        for match in mathml_regex.finditer(text):
            formula = match.group()
            pos = match.start()
            formulas.append(formula)
            formula_positions.append(pos)

            text = text[:pos] + " " * (match.end() - pos) + text[match.end() :]

        return formulas, formula_positions, text


# TODO: make generic to latex
def make_separate_text_and_formulas_use_case():
    return SeparateTextAndFormulasUseCase(content_type="mathml")
