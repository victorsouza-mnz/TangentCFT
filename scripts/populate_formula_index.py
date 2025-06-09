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

from typing import Dict, List, TypedDict, Set

# Increase CSV field size limit to handle large formulas
csv.field_size_limit(sys.maxsize)

# Batch sizes
BATCH_SIZE = 500
SEARCH_BATCH_SIZE = 1000


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


def get_existing_post_ids(elastic_service, post_ids_to_check: List[str]) -> Set[str]:
    """
    Check which post_ids exist in the posts index.

    Args:
        elastic_service: Elasticsearch service instance
        post_ids_to_check: List of post IDs to verify

    Returns:
        Set of post IDs that exist in the index
    """
    existing_post_ids = set()

    # Process in batches for bulk search
    for i in range(0, len(post_ids_to_check), SEARCH_BATCH_SIZE):
        batch_post_ids = post_ids_to_check[i : i + SEARCH_BATCH_SIZE]

        # Construct bulk search query
        body = {
            "query": {"terms": {"post_id": batch_post_ids}},
            "size": len(batch_post_ids),  # Get all matching documents
            "_source": ["post_id"],  # Only get post_id field
        }

        try:
            # Execute bulk search
            result = elastic_service.es.search(
                index=elastic_service.posts_index_name, body=body
            )

            # Process results - get found post_ids
            if result["hits"]["total"]["value"] > 0:
                for hit in result["hits"]["hits"]:
                    # Ensure post_id is converted to string for consistent comparison
                    post_id_from_es = str(hit["_source"]["post_id"])
                    existing_post_ids.add(post_id_from_es)

        except Exception as e:
            print(f"Error checking existing post IDs: {str(e)}")
            continue

    return existing_post_ids


def process_formulas_to_index(file_path, elastic_service, graph_type: str):
    """Process formulas from a TSV file and index them individually."""
    try:
        print(
            f"Processing formulas from file: {file_path} with graph_type: {graph_type}..."
        )

        # Inicializar os UseCases necessários
        parse_formula_to_tuples_use_case = make_parse_formula_to_tuples_use_case()
        encode_formula_tuples_use_case = make_encode_formula_tuples_use_case()
        get_formulas_vectors_use_case = (
            make_get_formula_vector_by_formula_encoded_tuples_use_case(graph_type)
        )

        with open(file_path, "r", encoding="utf-8") as file:
            reader = csv.DictReader(file, delimiter="\t")

            # Step 1: Collect all rows and unique post_ids from this file
            formulas = []
            post_ids_in_file = set()

            print("Reading and parsing CSV file...")
            for row_num, row in enumerate(reader, 1):
                try:
                    formulas.append(row)
                    post_id = row.get("post_id")
                    if post_id:
                        post_ids_in_file.add(str(post_id))

                except Exception as e:
                    print(f"Error reading row {row_num}: {str(e)}")
                    continue

            total_formulas = len(formulas)
            print(f"Total formulas in file: {total_formulas}")
            print(f"Unique post IDs in file: {len(post_ids_in_file)}")

            # Step 2: Check which post_ids exist in the posts index
            existing_post_ids = get_existing_post_ids(
                elastic_service, list(post_ids_in_file)
            )
            print(f"Post IDs that exist in posts index: {len(existing_post_ids)}")

            if not existing_post_ids:
                print("No existing posts found for this file, skipping...")
                return

            # Step 3: Process only formulas from existing posts
            processed = 0
            successful = 0
            skipped = 0
            formula_documents = []
            count = 0

            for row in formulas:
                try:
                    count += 1
                    formula_id = row.get("id")
                    formula_text = row.get("formula")
                    post_id = row.get("post_id")
                    formula_type = row.get("type")

                    if not formula_id or not formula_text or not post_id:
                        skipped += 1
                        continue

                    # Ensure post_id is string for comparison
                    post_id = str(post_id)

                    # Check if formula type is "question"
                    if formula_type != "question":
                        skipped += 1
                        continue

                    # Check if post exists in the posts index
                    if post_id not in existing_post_ids:
                        skipped += 1
                        continue

                    # Preparar documento base
                    formula_document = {
                        "formula_id": formula_id,
                        "post_id": post_id,
                    }

                    # Gerar tuplas baseado no tipo de grafo
                    if graph_type == "SLT" or graph_type == "SLT_TYPE":
                        tuples = parse_formula_to_tuples_use_case.execute(
                            formula_text, operator=False
                        )
                    elif graph_type == "OPT":
                        tuples = parse_formula_to_tuples_use_case.execute(
                            formula_text, operator=True
                        )

                    if not tuples:
                        print(
                            f"No tuples generated for formula {formula_id}, with graph type {graph_type}, skipping..."
                        )
                        skipped += 1
                        continue

                    # Codificar tuplas baseado no tipo de grafo
                    if graph_type == "SLT":
                        encoded_tuples = encode_formula_tuples_use_case.execute(
                            tuples, **EncodeFormulaTuplesUseCaseParams.SLT.value
                        )
                    elif graph_type == "SLT_TYPE":
                        encoded_tuples = encode_formula_tuples_use_case.execute(
                            tuples, **EncodeFormulaTuplesUseCaseParams.SLT_TYPE.value
                        )
                    elif graph_type == "OPT":
                        encoded_tuples = encode_formula_tuples_use_case.execute(
                            tuples, **EncodeFormulaTuplesUseCaseParams.OPT.value
                        )

                    # Gerar vetor
                    formula_vector = get_formulas_vectors_use_case.execute(
                        encoded_tuples
                    )

                    # Adicionar vetor específico ao documento baseado no tipo
                    if graph_type == "SLT":
                        formula_document["slt_vector"] = formula_vector
                        formula_document["slt_text"] = formula_text
                    elif graph_type == "SLT_TYPE":
                        formula_document["slt_type_vector"] = formula_vector
                    elif graph_type == "OPT":
                        formula_document["opt_vector"] = formula_vector
                        formula_document["opt_text"] = formula_text

                    formula_documents.append(formula_document)
                    successful += 1

                    # Processar em lotes
                    if len(formula_documents) >= BATCH_SIZE:
                        if graph_type == "SLT":
                            # Para SLT, fazemos index (primeira vez)
                            success = elastic_service.bulk_index_formulas(
                                formula_documents
                            )
                        else:
                            # Para SLT_TYPE e OPT, fazemos update
                            success = bulk_update_formulas(
                                elastic_service, formula_documents, graph_type
                            )

                        if success:
                            print(
                                f"Successfully processed batch of {len(formula_documents)} formulas for {graph_type}"
                            )
                        else:
                            print(
                                f"Error processing batch of {len(formula_documents)} formulas for {graph_type}"
                            )

                        formula_documents = []

                    processed += 1
                    if processed % 100 == 0:
                        print(
                            f"Processed {processed}/{total_formulas} formulas, {successful} successful, {skipped} skipped"
                        )

                except Exception as e:
                    print(
                        f"Error processing formula {row.get('id', 'unknown')}: {str(e)}"
                    )
                    skipped += 1
                    continue

            # Processar último lote
            if formula_documents:
                if graph_type == "SLT":
                    success = elastic_service.bulk_index_formulas(formula_documents)
                else:
                    success = bulk_update_formulas(
                        elastic_service, formula_documents, graph_type
                    )

                if success:
                    print(
                        f"Successfully processed final batch of {len(formula_documents)} formulas for {graph_type}"
                    )
                else:
                    print(
                        f"Error processing final batch of {len(formula_documents)} formulas for {graph_type}"
                    )

            print(
                f"File processing completed for {graph_type}: {processed}/{total_formulas} processed, {successful} successful, {skipped} skipped"
            )

    except Exception as e:
        print(f"Error processing formulas from file {file_path}: {str(e)}")
        import traceback

        print("Stacktrace:")
        print(traceback.format_exc())


def bulk_update_formulas(elastic_service, formula_documents, graph_type):
    """
    Bulk update formulas with specific vector type.

    Args:
        elastic_service: Elasticsearch service instance
        formula_documents: List of formula documents with vectors
        graph_type: Type of vector being updated (SLT_TYPE, OPT)
    """
    if not formula_documents:
        return True

    try:
        bulk_data = []

        for formula_doc in formula_documents:
            formula_id = formula_doc["formula_id"]

            # Preparar documento de update
            update_doc = {}
            if graph_type == "SLT_TYPE" and "slt_type_vector" in formula_doc:
                update_doc["slt_type_vector"] = formula_doc["slt_type_vector"]
            elif graph_type == "OPT" and "opt_vector" in formula_doc:
                update_doc["opt_vector"] = formula_doc["opt_vector"]
                # Adicionar opt_text se existir
                if "opt_text" in formula_doc:
                    update_doc["opt_text"] = formula_doc["opt_text"]

            if not update_doc:
                continue

            # Processar numpy arrays se necessário
            for vector_field in ["slt_type_vector", "opt_vector"]:
                if vector_field in update_doc and isinstance(
                    update_doc[vector_field], np.ndarray
                ):
                    update_doc[vector_field] = update_doc[vector_field].tolist()

            # Construir operação de update
            action = {
                "update": {
                    "_index": elastic_service.formulas_index_name,
                    "_id": formula_id,
                }
            }
            doc = {"doc": update_doc}

            bulk_data.append(action)
            bulk_data.append(doc)

        # Executar bulk update
        response = elastic_service.es.bulk(operations=bulk_data, refresh=True)
        return not response.get("errors", False)

    except Exception as e:
        print(f"Error bulk updating formulas: {str(e)}")
        return False


def combine_formula_vectors(elastic_service, batch_size=1000):
    """
    Combine all formula vectors (SLT + SLT_TYPE + OPT) into formula_vector.
    """
    print("Starting to combine formula vectors...")

    scroll_time = "5m"

    # Query para encontrar documentos que têm todos os 3 tipos de vetores
    search_query = {
        "query": {
            "bool": {
                "must": [
                    {"exists": {"field": "slt_vector"}},
                    {"exists": {"field": "slt_type_vector"}},
                    {"exists": {"field": "opt_vector"}},
                ]
            }
        },
        "size": batch_size,
    }

    result = elastic_service.es.search(
        index=elastic_service.formulas_index_name, body=search_query, scroll=scroll_time
    )

    print(f"Found {result['hits']['total']['value']} formulas to combine vectors")

    scroll_id = result["_scroll_id"]
    hits = result["hits"]["hits"]

    processed = 0
    bulk_updates = []

    while hits:
        for hit in hits:
            try:
                formula_id = hit["_id"]
                source = hit["_source"]

                slt_vector = np.array(source.get("slt_vector", []))
                slt_type_vector = np.array(source.get("slt_type_vector", []))
                opt_vector = np.array(source.get("opt_vector", []))

                if (
                    slt_vector.size == 0
                    or slt_type_vector.size == 0
                    or opt_vector.size == 0
                ):
                    print(f"Missing vectors for formula {formula_id}, skipping...")
                    continue

                # Combinar vetores (soma)
                combined_vector = slt_vector + slt_type_vector + opt_vector

                bulk_updates.append(
                    {
                        "formula_id": formula_id,
                        "formula_vector": combined_vector.tolist(),
                    }
                )

                processed += 1

                # Processar em lotes
                if len(bulk_updates) >= batch_size:
                    success = bulk_update_combined_vectors(
                        elastic_service, bulk_updates
                    )
                    if success:
                        print(
                            f"Successfully combined vectors for batch of {len(bulk_updates)} formulas"
                        )
                    else:
                        print(
                            f"Error combining vectors for batch of {len(bulk_updates)} formulas"
                        )
                    bulk_updates = []

                if processed % 1000 == 0:
                    print(f"Combined vectors for {processed} formulas")

            except Exception as e:
                print(f"Error combining vectors for formula {hit['_id']}: {str(e)}")
                continue

        # Próximo lote
        result = elastic_service.es.scroll(scroll_id=scroll_id, scroll=scroll_time)
        scroll_id = result["_scroll_id"]
        hits = result["hits"]["hits"]

    # Processar último lote
    if bulk_updates:
        success = bulk_update_combined_vectors(elastic_service, bulk_updates)
        if success:
            print(
                f"Successfully combined vectors for final batch of {len(bulk_updates)} formulas"
            )

    elastic_service.es.clear_scroll(scroll_id=scroll_id)
    print(f"✅ Completed combining vectors for {processed} formulas")


def bulk_update_combined_vectors(elastic_service, updates):
    """Update formulas with combined vectors."""
    if not updates:
        return True

    try:
        bulk_data = []

        for update in updates:
            formula_id = update["formula_id"]
            formula_vector = update["formula_vector"]

            action = {
                "update": {
                    "_index": elastic_service.formulas_index_name,
                    "_id": formula_id,
                }
            }
            doc = {"doc": {"formula_vector": formula_vector}}

            bulk_data.append(action)
            bulk_data.append(doc)

        response = elastic_service.es.bulk(operations=bulk_data, refresh=True)
        return not response.get("errors", False)

    except Exception as e:
        print(f"Error bulk updating combined vectors: {str(e)}")
        return False


def main():
    # Initialize Elasticsearch service
    elastic_service = ElasticsearchService()

    # Define directories with formula files
    slt_dir = "data/arqmath/slt_representation_v3"
    opt_dir = "data/arqmath/opt_representation_v3"

    # Get all files from both directories (they should contain the same formulas)
    print(f"Getting formula files from {slt_dir}...")
    slt_files = get_formula_files(slt_dir)

    print(f"Getting formula files from {opt_dir}...")
    opt_files = get_formula_files(opt_dir)

    # Step 1: Process SLT first (creates documents)
    print("Processing SLT formulas...")
    file_counter = 0
    for file_path in slt_files:
        process_formulas_to_index(file_path, elastic_service, graph_type="SLT")
        file_counter += 1
        print(f"Processed SLT: {file_counter} of {len(slt_files)} files")

    # Step 2: Process SLT_TYPE (updates existing documents)
    print("Processing SLT_TYPE formulas...")
    file_counter = 0
    for file_path in slt_files:
        process_formulas_to_index(file_path, elastic_service, graph_type="SLT_TYPE")
        file_counter += 1
        print(f"Processed SLT_TYPE: {file_counter} of {len(slt_files)} files")

    # Step 3: Process OPT (updates existing documents)
    print("Processing OPT formulas...")
    file_counter = 0
    for file_path in opt_files:
        process_formulas_to_index(file_path, elastic_service, graph_type="OPT")
        file_counter += 1
        print(f"Processed OPT: {file_counter} of {len(opt_files)} files")

    # Step 4: Combine all vectors
    print("\nCombining all formula vectors...")
    combine_formula_vectors(elastic_service)

    print("✅ All formula processing completed!")


if __name__ == "__main__":
    main()


# TODO:
# popular o slt_text e o opt_text
# investigar pq opt_vector não está sendo populado
# popular o formula_vector com os 3 vetores combinados
