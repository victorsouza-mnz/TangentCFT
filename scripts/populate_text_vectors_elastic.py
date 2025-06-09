import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tqdm import tqdm
from services.elasticsearch_service import ElasticsearchService
from app.modules.embedding.use_cases.get_text_vector import (
    make_get_text_vector_use_case,
)


CHECKPOINT_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "update_text_vector_checkpoint.txt"
)
# Increased batch size for faster processing
BATCH_SIZE = 1000
# Increased number of workers
MAX_WORKERS = 4

lock = threading.Lock()

elastic_service = ElasticsearchService()
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


def fetch_posts_from_elastic(last_post_id, size=BATCH_SIZE):
    """
    Busca posts do Elasticsearch com post_id maior que o last_post_id
    e que não possuem text_without_formula_vector populado.
    """
    body = {
        "size": size,
        "query": {
            "bool": {
                "must": [{"range": {"post_id": {"gt": last_post_id}}}],
                "must_not": [{"exists": {"field": "text_without_formula_vector"}}],
            }
        },
        "sort": [{"post_id": "asc"}],
    }

    res = elastic_service.es.search(index=elastic_service.posts_index_name, body=body)
    return [hit["_source"] for hit in res["hits"]["hits"]]


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
        # Batch encode all texts at once (much faster than one by one)
        vectors = text_vector_use_case.model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            batch_size=32,
            show_progress_bar=False,
        )

        # Create update objects
        updates = []
        for i, post_id in enumerate(post_ids):
            updates.append(
                {"post_id": post_id, "text_without_formula_vector": vectors[i].tolist()}
            )

        return updates
    except Exception as e:
        print(f"Error batch processing vectors: {e}")
        return []


def update_batch(elastic_service, batch):
    try:
        elastic_service.bulk_update_text_vector(batch)
    except Exception as e:
        print(f"Erro ao atualizar batch: {e}")


def count_total_posts():
    """Get approximate total count of posts without text vectors"""
    query = {
        "track_total_hits": True,
        "size": 0,
        "query": {
            "bool": {"must_not": [{"exists": {"field": "text_without_formula_vector"}}]}
        },
    }

    try:
        result = elastic_service.es.search(
            index=elastic_service.posts_index_name, body=query
        )
        return result["hits"]["total"]["value"]
    except Exception as e:
        print(f"Error getting post count: {e}")
        return 1000000  # Use a large default number


def update_vectors():
    last_post_id = load_last_checkpoint()

    print(f"Último post processado: {last_post_id}")

    # Get approximate total for progress bar
    total_posts = count_total_posts()
    print(f"Total posts estimado: {total_posts}")

    total_processed = 0
    pbar = tqdm(total=total_posts, desc="Atualizando vetores")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = []

        while True:
            print(f"Fetching posts from {last_post_id} to {last_post_id + BATCH_SIZE}")
            posts = fetch_posts_from_elastic(last_post_id, BATCH_SIZE)

            if not posts:
                break

            print("processing batch ")
            # Process vectors in batches
            sub_batches = [posts[i : i + 100] for i in range(0, len(posts), 100)]
            batch_futures = [
                executor.submit(process_batch, sub_batch) for sub_batch in sub_batches
            ]

            # Collect all updates
            all_updates = []
            for future in batch_futures:
                updates = future.result()
                all_updates.extend(updates)

            if all_updates:
                # Submit updates in chunks to avoid overwhelming Elasticsearch
                for i in range(0, len(all_updates), 100):
                    chunk = all_updates[i : i + 100]
                    futures.append(
                        executor.submit(update_batch, elastic_service, chunk)
                    )

                last_post_id = max([update["post_id"] for update in all_updates])
                save_checkpoint(last_post_id)

                # Update progress
                chunk_size = len(all_updates)
                total_processed += chunk_size
                pbar.update(chunk_size)
                pbar.set_postfix({"Último ID": last_post_id})

        # Wait for all futures to complete
        for future in futures:
            future.result()

    pbar.close()
    print(f"Atualização finalizada: {total_processed} posts processados")


def main():
    update_vectors()


if __name__ == "__main__":
    main()
