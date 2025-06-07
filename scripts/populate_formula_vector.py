#!/usr/bin/env python3
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import csv
import glob
import numpy as np
from services.elasticsearch_service import ElasticsearchService
from enum import Enum
from app.modules.embedding.use_cases.encode_formula_tuples import (
    make_encode_formula_tuples_use_case,
)
from app.modules.embedding.use_cases.parse_formula_to_tuples import (
    make_parse_formula_to_tuples_use_case,
)
from lib.tangentCFT.touple_encoder.encoder import TupleTokenizationMode
from app.modules.embedding.use_cases.get_formula_vector_by_formula_encoded_tuples import (
    make_get_formula_vector_by_formula_encoded_tuples_use_case,
)

from typing import Dict, List, TypedDict


class Formula(TypedDict):
    formula: str
    id: str


class PostFormulas(TypedDict):
    formulas: List[Formula]


# Batch sizes
SEARCH_BATCH_SIZE = 1000
UPDATE_BATCH_SIZE = 500


class EncodeFormulaTuplesUseCaseParams(Enum):
    SLT = {
        "encoder_type": "SLT",
        "embedding_type": TupleTokenizationMode.Both_Separated,
        "tokenize_numbers": True,
    }

    SLT_TYPE = {
        "encoder_type": "SLT_TYPE",
        "embedding_type": TupleTokenizationMode.Type,
        "tokenize_numbers": False,
    }

    OPT = {
        "encoder_type": "OPT",
        "embedding_type": TupleTokenizationMode.Both_Separated,
        "tokenize_numbers": False,
    }


def get_formula_files(directory):
    """Get all TSV files in the given directory."""
    return glob.glob(os.path.join(directory, "*.tsv"))


def process_formulas(file_path, elastic_service, graph_type: str):
    """Process formulas from a TSV file using bulk search and update."""
    try:
        print(f"Processing formulas from a file, {file_path}...")
        with open(file_path, "r", encoding="utf-8") as file:
            reader = csv.DictReader(file, delimiter="\t")

            formulas = list(reader)
            total_formulas = len(formulas)
            processed = 0
            hits = 0

            formula_map: Dict[str, PostFormulas] = {}
            for row in formulas:
                if row.get("post_id"):
                    post_id = row["post_id"]
                    if post_id not in formula_map:
                        formula_map[post_id] = {"formulas": []}
                    formula_map[post_id]["formulas"].append(
                        {"formula": row["formula"], "id": row["id"]}
                    )

            # Collect all found post_ids for later bulk update
            all_found_post_ids = set()

            print(f"Total formulas in this file to process: {total_formulas}")

            # Process in batches for bulk search
            for i in range(0, total_formulas, SEARCH_BATCH_SIZE):
                batch = formulas[i : i + SEARCH_BATCH_SIZE]
                post_ids = [row.get("post_id") for row in batch if row.get("post_id")]
                if not post_ids:
                    continue

                # Construct bulk search query
                body = {
                    "query": {"terms": {"post_id": post_ids}},
                    "size": len(post_ids),  # Get all matching documents
                }

                try:
                    # Execute bulk search
                    result = elastic_service.es.search(
                        index=elastic_service.index_name, body=body
                    )

                    # Process results - get found post_ids
                    found_post_ids = set()
                    if result["hits"]["total"]["value"] > 0:
                        for hit in result["hits"]["hits"]:
                            found_post_ids.add(hit["_source"]["post_id"])

                    # Add to the collection of all found post_ids
                    all_found_post_ids.update(found_post_ids)

                    # Count hits
                    batch_hits = len(found_post_ids)
                    hits += batch_hits

                    # Print progress
                    processed += len(batch)

                except Exception as e:
                    print(f"Error in bulk search: {str(e)}")

            print(f"file processed: {processed}/{total_formulas} - Total hits: {hits}")

            # Convert to list for batching
            all_found_post_ids = list(all_found_post_ids)

            # Perform bulk updates in batches
            if all_found_post_ids:
                print(
                    f"Updating founded {len(all_found_post_ids)} posts with formula data..."
                )
                total_updated = 0

                for i in range(0, len(all_found_post_ids), UPDATE_BATCH_SIZE):
                    batch_ids = all_found_post_ids[i : i + UPDATE_BATCH_SIZE]
                    # Create a subset of the formula map for this batch
                    batch_formula_data: Dict[str, PostFormulas] = {
                        post_id: formula_map[str(post_id)]
                        for post_id in batch_ids
                        if str(post_id) in formula_map
                    }

                    # Update posts with all embedding types at once
                    updated = update_formula_vectors_in_posts(
                        batch_ids, batch_formula_data, elastic_service, graph_type
                    )

                    if updated is not None:
                        total_updated += updated

                print(f"Completed updating {total_updated} posts with formula data")

    except Exception as e:
        import traceback

        print(f"Error processing file {file_path}: {str(e)}")
        print("Stacktrace:")
        print(traceback.format_exc())


def update_formula_vectors_in_posts(
    post_ids, formulas_data: Dict[str, PostFormulas], elastic_service, graph_type: str
):
    """
    Bulk update posts with formula vector types (SLT, SLT_TYPE, OPT).

    Args:
        post_ids: List of post IDs to update
        formulas_data: Dictionary mapping post_id to formula information
        elastic_service: Elasticsearch service instance
        graph_type: The type of graph to process (SLT, SLT_TYPE, OPT)
    """
    print("Updating formula vectors in posts")

    # Inicializar os UseCases necessários
    parse_formula_to_tuples_use_case = make_parse_formula_to_tuples_use_case()
    encode_formula_tuples_use_case = make_encode_formula_tuples_use_case()
    get_formulas_vectors_use_case = (
        make_get_formula_vector_by_formula_encoded_tuples_use_case(graph_type)
    )

    # Preparar as operações de bulk update
    bulk_updates = []
    successful_updates = 0

    for post_id in post_ids:
        if post_id not in formulas_data:
            print(f"No formula data for post {post_id}, skipping...")
            continue

        post_formulas = formulas_data[post_id].get("formulas", [])

        # Armazenar os vetores de cada tipo
        formula_vectors = []

        for formula in post_formulas:
            formula_tuples = []
            try:
                # 1. Converter para tuplas
                if graph_type == "SLT" or graph_type == "SLT_TYPE":
                    formula_tuples = parse_formula_to_tuples_use_case.execute(
                        formula["formula"], operator=False
                    )

                elif graph_type == "OPT":
                    formula_tuples = parse_formula_to_tuples_use_case.execute(
                        formula["formula"], operator=True
                    )

                if not formula_tuples:
                    print(
                        f"No tuples generated for formula {formula['id']}, with graph type {graph_type}, skipping..."
                    )
                    continue

                # 2. Gerar os três tipos de encodings
                # SLT
                if graph_type == "SLT":
                    formula_encoded_tuples = encode_formula_tuples_use_case.execute(
                        formula_tuples, **EncodeFormulaTuplesUseCaseParams.SLT.value
                    )
                # SLT_TYPE
                if graph_type == "SLT_TYPE":
                    formula_encoded_tuples = encode_formula_tuples_use_case.execute(
                        formula_tuples,
                        **EncodeFormulaTuplesUseCaseParams.SLT_TYPE.value,
                    )
                # OPT
                if graph_type == "OPT":
                    formula_encoded_tuples = encode_formula_tuples_use_case.execute(
                        formula_tuples, **EncodeFormulaTuplesUseCaseParams.OPT.value
                    )

                formula_vector = get_formulas_vectors_use_case.execute(
                    formula_encoded_tuples
                )

                # Store vector and formula ID together in a dictionary
                formula_vectors.append(
                    {
                        "vector": formula_vector,
                        "id": formula["id"],
                        "text": formula["formula"],
                    }
                )

            except Exception as e:
                print(f"Error processing formula for post {post_id}: {str(e)}")
                continue

        # Preparar documento para atualização
        update_doc = {}
        if graph_type == "SLT":
            processed_vectors = []
            for vector_data in formula_vectors:
                processed_vector = {
                    "vector": vector_data["vector"],
                    "formula_index": vector_data["id"],
                    "formula_text": vector_data["text"],
                }
                processed_vectors.append(processed_vector)
            update_doc = {
                "slt_vectors": processed_vectors,
            }
        elif graph_type == "OPT":
            processed_vectors = []
            for vector_data in formula_vectors:
                processed_vector = {
                    "vector": vector_data["vector"],
                    "formula_index": vector_data["id"],
                    "formula_text": vector_data["text"],
                }
                processed_vectors.append(processed_vector)
            update_doc = {
                "opt_vectors": processed_vectors,
            }
        elif graph_type == "SLT_TYPE":
            processed_vectors = []
            for vector_data in formula_vectors:
                processed_vector = {
                    "vector": vector_data["vector"],
                    "formula_index": vector_data["id"],
                    "formula_text": vector_data["text"],
                }
                processed_vectors.append(processed_vector)
            update_doc = {
                "slt_type_vectors": processed_vectors,
            }

        # Adicionar à lista para o método bulk_update_posts
        bulk_updates.append({"post_id": post_id, **update_doc})
        successful_updates += 1

    # Executar atualização em massa
    if bulk_updates:
        try:
            print(f"Updating bulk of {len(bulk_updates)} posts in database...")

            success = elastic_service.bulk_update_posts(bulk_updates)
            print(f"Update completed, success: {success}")
        except Exception as e:
            print(f"Error updating posts: {e}")
    else:
        print("No update operations to execute")

    return successful_updates


def combine_all_vectors(elastic_service, batch_size=100):
    """
    Process all documents in the index and combine their formula vectors.

    Args:
        elastic_service: Elasticsearch service instance
        batch_size: Number of documents to process in each batch
    """
    print("Starting to combine all formula vectors...")

    # Get total count of documents
    count_query = {"query": {"match_all": {}}}
    count_result = elastic_service.es.count(
        index=elastic_service.index_name, body=count_query
    )
    total_docs = count_result["count"]

    print(f"Total documents to process: {total_docs}")

    # Process documents in batches
    processed = 0
    scroll_time = "5m"  # Keep the search context alive for 5 minutes

    # Initialize the scroll
    search_query = {
        "query": {
            "bool": {
                "should": [
                    {"exists": {"field": "slt_vectors"}},
                    {"exists": {"field": "slt_type_vectors"}},
                    {"exists": {"field": "opt_vectors"}},
                ],
                "minimum_should_match": 1,
            }
        },
        "size": batch_size,
    }

    # Start the initial scroll
    result = elastic_service.es.search(
        index=elastic_service.index_name, body=search_query, scroll=scroll_time
    )

    print(f"Initial scroll result: {result['hits']}")

    # Get the scroll_id
    scroll_id = result["_scroll_id"]
    hits = result["hits"]["hits"]

    bulk_updates = []

    while len(hits) > 0:
        for hit in hits:
            post_id = hit["_id"]
            source = hit["_source"]

            try:
                # Get all vector types
                slt_vectors = source.get("slt_vectors", [])
                slt_type_vectors = source.get("slt_type_vectors", [])
                opt_vectors = source.get("opt_vectors", [])

                # Create a dictionary to hold combined vectors by formula_index
                combined_vectors = {}

                # Process SLT vectors
                for vec in slt_vectors:
                    idx = vec.get("formula_index")
                    if idx is not None:
                        if idx not in combined_vectors:
                            combined_vectors[idx] = {
                                "vector": np.array(vec.get("vector", [])),
                                "formula_text": vec.get("formula_text", ""),
                                "formula_index": idx,
                            }
                        else:
                            combined_vectors[idx]["vector"] = np.array(
                                vec.get("vector", [])
                            )

                # Process SLT_TYPE vectors and add to existing
                for vec in slt_type_vectors:
                    idx = vec.get("formula_index")
                    if idx is not None:
                        if idx not in combined_vectors:
                            combined_vectors[idx] = {
                                "vector": np.array(vec.get("vector", [])),
                                "formula_text": vec.get("formula_text", ""),
                                "formula_index": idx,
                            }
                        else:
                            combined_vectors[idx]["vector"] += np.array(
                                vec.get("vector", [])
                            )

                # Process OPT vectors and add to existing
                for vec in opt_vectors:
                    idx = vec.get("formula_index")
                    if idx is not None:
                        if idx not in combined_vectors:
                            combined_vectors[idx] = {
                                "vector": np.array(vec.get("vector", [])),
                                "formula_text": vec.get("formula_text", ""),
                                "formula_index": idx,
                            }
                        else:
                            combined_vectors[idx]["vector"] += np.array(
                                vec.get("vector", [])
                            )

                # Convert back to list format
                result_vectors = []
                for idx, data in combined_vectors.items():
                    result_vectors.append(
                        {
                            "vector": data["vector"].tolist(),
                            "formula_index": idx,
                            "formula_text": data["formula_text"],
                        }
                    )

                if result_vectors:
                    bulk_updates.append(
                        {"post_id": post_id, "formula_vectors": result_vectors}
                    )

            except Exception as e:
                print(f"Error processing document {post_id}: {str(e)}")

            processed += 1
            if processed % 100 == 0:
                print(f"Processed {processed} documents")

        # Perform bulk update for this batch
        if bulk_updates:
            try:
                print(
                    f"Updating {len(bulk_updates)} documents with combined vectors..."
                )
                success = elastic_service.bulk_update_posts(bulk_updates)
                print(f"Combined vectors update completed: {success}")
                bulk_updates = []  # Reset for next batch
            except Exception as e:
                print(f"Error updating documents with combined vectors: {e}")

        # Get the next batch
        result = elastic_service.es.scroll(scroll_id=scroll_id, scroll=scroll_time)
        scroll_id = result["_scroll_id"]
        hits = result["hits"]["hits"]

    # Clear the scroll context
    elastic_service.es.clear_scroll(scroll_id=scroll_id)

    print(f"Completed processing {processed} documents with combined vectors")


def main():
    # Initialize Elasticsearch service
    elastic_service = ElasticsearchService()

    # Define directories with formula files
    slt_dir = "data/arqmath/slt_representation_v3"
    opt_dir = "data/arqmath/opt_representation_v3"

    # Process SLT formulas
    print(f"Getting SLT formula files from {slt_dir}...")
    slt_files = get_formula_files(slt_dir)

    # Process OPT formulas
    print(f"Getting OPT formula files from {opt_dir}...")
    opt_files = get_formula_files(opt_dir)

    # Step 1: Process all vector types separately
    file_counter = 0
    print("Processing SLT_TYPE formulas...")
    file_counter = 0
    for file_path in slt_files:
        process_formulas(file_path, elastic_service, graph_type="SLT_TYPE")
        file_counter += 1
        print(f"Processed SLT_TYPE: {file_counter} of {len(slt_files)} files")

    print("Processing SLT formulas...")
    file_counter = 0
    for file_path in slt_files:
        process_formulas(file_path, elastic_service, graph_type="SLT")
        file_counter += 1
        print(f"Processed SLT: {file_counter} of {len(slt_files)} files")

    print("Processing OPT formulas...")
    file_counter = 0
    for file_path in opt_files:
        process_formulas(file_path, elastic_service, graph_type="OPT")
        file_counter += 1
        print(f"Processed OPT: {file_counter} of {len(opt_files)} files")

    # Step 2: After all vector types are processed, combine them
    print("\nAll vector types processed. Now combining vectors...")
    combine_all_vectors(elastic_service)


if __name__ == "__main__":
    main()


# TODO INVESTIGAR PQ ESSE NAO TA CRIANDO O COMBINED VECTOR
