import os
import sys
import xml.etree.ElementTree as ET
from tqdm import tqdm
import html
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
import threading


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from scripts.utils.text_celaner import clean_text
import xml.etree.ElementTree as ET
from tqdm import tqdm
import html
from bs4 import BeautifulSoup


from services.elasticsearch_service import ElasticsearchService


POSTS_XML_PATH = "data/arqmath/Posts.V1.3.xml"
POSTS_FORMULAS_IN_SLT_FOLDER_PATH = (
    "data/arqmath/slt_representation/slt_representation_v3"
)

from services.elasticsearch_service import ElasticsearchService

POSTS_XML_PATH = "data/arqmath/Posts.V1.3.xml"
CHECKPOINT_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "checkpoint.txt"
)
BATCH_SIZE = 100
MAX_WORKERS = 4
MAX_POSTS = 15000  # Limit to first 30k posts

lock = threading.Lock()


def load_last_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, "r") as f:
            return int(f.read().strip())
    return -1


def save_checkpoint(post_id):
    with lock:
        with open(CHECKPOINT_FILE, "w") as f:
            f.write(str(post_id))


def process_post(elem):
    post_id = int(elem.attrib.get("Id"))
    body = html.unescape(elem.attrib.get("Body", ""))
    title = html.unescape(elem.attrib.get("Title", ""))

    text = f"{title} {body}" if title else body
    soup = BeautifulSoup(text, "html.parser")

    full_text_without_html = soup.get_text(separator=" ", strip=True)

    # Contar o número de fórmulas antes de removê-las
    formulas_count = len(soup.select(".math-container"))

    for el in soup.select(".math-container"):
        el.decompose()

    text_without_formula = soup.get_text(separator=" ", strip=True)

    if len(text) == 0 or len(text_without_formula) == 0:
        print("Erro texto vazio por algum motivo")
        print("text:")
        print(text)
        print("text without formula:")
        print(text_without_formula)
    if not (text):
        return None

    return {
        "post_id": post_id,
        "text": text,
        "text_latex_search": clean_text(full_text_without_html),
        "text_without_formula": text_without_formula,
        "formulas_count": formulas_count,  # Novo campo com o número de fórmulas
        "formulas": [],
        "formulas_mathml": [],
        "formulas_latex": [],
        "formula_vectors": [],
        "formulas_ids": [],
    }


def count_total_posts():
    total = 0
    context = ET.iterparse(POSTS_XML_PATH, events=("end",))
    for event, elem in context:
        if elem.tag == "row":
            total += 1
        elem.clear()
    return total


def index_posts_from_xml(elastic_service):
    last_post_id = load_last_checkpoint()
    print(f"Último post indexado: {last_post_id}")

    # Contar total de posts
    total_posts = count_total_posts()
    print(f"Total de posts: {total_posts}")

    context = ET.iterparse(POSTS_XML_PATH, events=("end",))
    batch = []
    futures = []
    executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)
    current_post = 0
    processed_posts = 0

    for event, elem in context:
        if elem.tag == "row":
            post_id = int(elem.attrib.get("Id"))
            post_type_id = elem.attrib.get("PostTypeId")
            current_post += 1

            # Só processar posts do tipo 1 (questions)
            if post_type_id != "1":
                elem.clear()
                continue

            if post_id <= last_post_id:
                elem.clear()
                continue

            doc = process_post(elem)
            if doc:
                batch.append(doc)
                processed_posts += 1

            if len(batch) >= BATCH_SIZE:
                futures.append(
                    executor.submit(index_batch, elastic_service, batch.copy())
                )
                save_checkpoint(post_id)
                # Printar progresso apenas no final de cada batch
                print(
                    f"Posts tipo 1 processados: {processed_posts}/{MAX_POSTS} (Post atual: {current_post}/{total_posts})"
                )
                batch = []

            elem.clear()

            # Stop after processing MAX_POSTS of type 1
            if processed_posts >= MAX_POSTS:
                print(f"Reached limit of {MAX_POSTS} posts of type 1. Stopping.")
                break

    if batch:
        futures.append(executor.submit(index_batch, elastic_service, batch.copy()))
        save_checkpoint(post_id)
        print(
            f"Posts tipo 1 processados: {processed_posts}/{MAX_POSTS} (Post atual: {current_post}/{total_posts})"
        )

    for f in futures:
        f.result()  # garante que todas as tarefas terminaram

    print(
        f"Indexação finalizada: {processed_posts} posts do tipo 1 processados de {current_post} posts analisados"
    )


def index_batch(elastic_service, batch):
    try:
        elastic_service.bulk_index_posts(batch)
    except Exception as e:
        print(f"Erro ao indexar batch: {e}")


def main():
    elastic_service = ElasticsearchService()
    index_posts_from_xml(elastic_service)


if __name__ == "__main__":
    main()
