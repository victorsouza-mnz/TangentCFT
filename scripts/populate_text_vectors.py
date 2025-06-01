import os
import sys
import threading
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm
import html
from bs4 import BeautifulSoup

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.modules.embedding.use_cases.get_text_vector import (
    make_get_text_vector_use_case,
)

# Input XML file path
POSTS_XML_PATH = "data/arqmath/Posts.V1.3.xml"
# Output XML file with vectors
OUTPUT_XML_PATH = "data/output_vectors.xml"
CHECKPOINT_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "vector_xml_checkpoint.txt"
)
# Batch settings
BATCH_SIZE = 500
MAX_WORKERS = 8

lock = threading.Lock()
text_vector_use_case = make_get_text_vector_use_case()


def load_last_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, "r") as f:
            return int(f.read().strip())
    return -1


def save_checkpoint(last_post_id):
    with lock:
        with open(CHECKPOINT_FILE, "w") as f:
            f.write(str(last_post_id))


def process_post(elem):
    """Extract text content from XML element"""
    post_id = int(elem.attrib.get("Id"))
    body = html.unescape(elem.attrib.get("Body", ""))
    title = html.unescape(elem.attrib.get("Title", ""))

    text = f"{title} {body}" if title else body
    soup = BeautifulSoup(text, "html.parser")

    # Remove formulas
    for el in soup.select(".math-container"):
        el.decompose()

    text_without_formula = soup.get_text(separator=" ", strip=True)

    if not text_without_formula:
        return None

    return {
        "post_id": post_id,
        "text_without_formula": text_without_formula,
    }


def process_batch(posts):
    """Process a batch of posts to generate vectors all at once"""
    if not posts:
        return []

    # Extract post IDs and texts
    post_ids = []
    texts = []

    for post in posts:
        post_id = post.get("post_id")
        text = post.get("text_without_formula")

        if post_id and text:
            post_ids.append(post_id)
            texts.append(text)

    if not texts:
        return []

    try:
        # Batch encode all texts at once
        vectors = text_vector_use_case.model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            batch_size=32,
            show_progress_bar=False,
        )

        # Create result objects
        results = []
        for i, post_id in enumerate(post_ids):
            results.append({"post_id": post_id, "vector": vectors[i].tolist()})

        return results
    except Exception as e:
        print(f"Error batch processing vectors: {e}")
        return []


def save_batch_to_xml(batch, output_file):
    """Save a batch of vectors to the XML file"""
    with lock:
        # Check if file exists, if not create root element
        if not os.path.exists(output_file):
            root = ET.Element("vectors")
            tree = ET.ElementTree(root)
            tree.write(output_file, encoding="utf-8", xml_declaration=True)

        # Parse existing file
        tree = ET.parse(output_file)
        root = tree.getroot()

        # Add new elements
        for item in batch:
            post_elem = ET.SubElement(root, "post")
            post_elem.set("id", str(item["post_id"]))

            # Convert vector to string (join with spaces)
            vector_str = " ".join([str(val) for val in item["vector"]])
            post_elem.text = vector_str

        # Write back to file
        tree.write(output_file, encoding="utf-8", xml_declaration=True)


def count_total_posts():
    """Count total posts in XML file for progress tracking"""
    total = 0
    context = ET.iterparse(POSTS_XML_PATH, events=("end",))
    for event, elem in context:
        if elem.tag == "row":
            total += 1
        elem.clear()
    return total


def process_vectors_from_xml():
    last_post_id = load_last_checkpoint()
    print(f"Last processed post ID: {last_post_id}")

    # Count total posts for progress bar
    total_posts = count_total_posts()
    print(f"Total posts: {total_posts}")

    context = ET.iterparse(POSTS_XML_PATH, events=("end",))
    batch = []
    futures = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        pbar = tqdm(total=total_posts, desc="Processing vectors")
        current_post = 0

        for event, elem in context:
            if elem.tag == "row":
                post_id = int(elem.attrib.get("Id"))
                current_post += 1

                # Skip already processed posts
                if post_id <= last_post_id:
                    elem.clear()
                    pbar.update(1)
                    continue

                post_data = process_post(elem)
                if post_data:
                    batch.append(post_data)

                if len(batch) >= BATCH_SIZE:
                    # Process batch and get vectors
                    processed_batch = process_batch(batch)
                    if processed_batch:
                        # Save to XML file
                        save_batch_to_xml(processed_batch, OUTPUT_XML_PATH)

                    save_checkpoint(post_id)
                    pbar.update(len(batch))
                    batch = []

                elem.clear()

        # Process any remaining items
        if batch:
            processed_batch = process_batch(batch)
            if processed_batch:
                save_batch_to_xml(processed_batch, OUTPUT_XML_PATH)
            save_checkpoint(post_id)
            pbar.update(len(batch))

        pbar.close()
        print(f"Processing complete. Total posts processed: {current_post}")


def main():
    process_vectors_from_xml()


if __name__ == "__main__":
    main()
