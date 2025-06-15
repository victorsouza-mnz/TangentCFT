from bs4 import BeautifulSoup


class RemoveFormulasFromTextUseCase:
    def execute(self, text: str):
        soup = BeautifulSoup(text, "html.parser")

        for el in soup.select(".math-container"):
            el.decompose()
        text_without_formula = soup.get_text(separator=" ", strip=True)
        return text_without_formula


def make_remove_formulas_from_text_use_case():
    return RemoveFormulasFromTextUseCase()
