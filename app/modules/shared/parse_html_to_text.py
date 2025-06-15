from bs4 import BeautifulSoup


def parse_html_to_text(text: str) -> str:
    soup = BeautifulSoup(text, "html.parser")
    return soup.get_text(separator=" ", strip=True)
