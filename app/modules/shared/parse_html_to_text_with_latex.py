from bs4 import BeautifulSoup


def parse_html_to_text_with_latex(text: str) -> str:
    soup = BeautifulSoup(text, "html.parser")
    for span in soup.find_all("span", class_="math-container"):
        inner = span.get_text()
        span.replace_with(f"${inner}$")

    return soup.get_text(separator=" ", strip=True)
