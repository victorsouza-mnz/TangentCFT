from elasticsearch import Elasticsearch
import numpy as np
import json


class ElasticsearchService:
    def __init__(
        self,
        host="localhost",
        port=9200,
        posts_index_name="posts",
        formulas_index_name="formulas",
    ):
        """
        Initialize Elasticsearch service.

        Args:
            host: Elasticsearch host
            port: Elasticsearch port
            index_name: Name of the index to use
        """
        self.es = Elasticsearch(
            [f"http://{host}:{port}"],
            timeout=60,  # Increase timeout to 60 seconds
            retry_on_timeout=True,
            max_retries=3,
        )
        self.posts_index_name = posts_index_name
        self.formulas_index_name = formulas_index_name

        # Create index if it doesn't exist
        if not self.posts_index_exists():
            print("Creating posts index")
            self.create_posts_index()

        if not self.formulas_index_exists():
            print("Creating formulas index")
            self.create_formulas_index()

    def posts_index_exists(self):
        """Check if the posts index exists"""
        return self.es.indices.exists(index=self.posts_index_name)

    def formulas_index_exists(self):
        """Check if the formulas index exists"""
        return self.es.indices.exists(index=self.formulas_index_name)

    def bulk_index_posts(self, posts_data):
        """
        Bulk index posts for better performance.

        Args:
            posts_data: List of post dictionaries
        """
        if not posts_data:
            return True

        bulk_data = []
        for post in posts_data:
            # Action description
            action = {
                "index": {"_index": self.posts_index_name, "_id": post["post_id"]}
            }

            # Process text_without_formula_vector if present
            if "text_without_formula_vector" in post and isinstance(
                post["text_without_formula_vector"], np.ndarray
            ):
                post["text_without_formula_vector"] = post[
                    "text_without_formula_vector"
                ].tolist()

            # Process text_without_html_vector if present
            if "text_without_html_vector" in post and isinstance(
                post["text_without_html_vector"], np.ndarray
            ):
                post["text_without_html_vector"] = post[
                    "text_without_html_vector"
                ].tolist()

            # Process formula vectors if present
            if "formula_vectors" in post:
                processed_vectors = []
                for vector in post["formula_vectors"]:
                    if isinstance(vector, np.ndarray):
                        processed_vector = {"vector": vector.tolist()}
                    elif (
                        isinstance(vector, dict)
                        and "vector" in vector
                        and isinstance(vector["vector"], np.ndarray)
                    ):
                        processed_vector = {"vector": vector["vector"].tolist()}
                    else:
                        # Assuming vector is already in the correct format or a raw list/vector
                        processed_vector = {"vector": vector}
                    processed_vectors.append(processed_vector)
                post["formula_vectors"] = processed_vectors

            # Process SLT vectors if present
            if "slt_vectors" in post:
                processed_vectors = []
                for vector in post["slt_vectors"]:
                    if isinstance(vector, np.ndarray):
                        processed_vector = {"vector": vector.tolist()}
                    elif (
                        isinstance(vector, dict)
                        and "vector" in vector
                        and isinstance(vector["vector"], np.ndarray)
                    ):
                        processed_vector = {"vector": vector["vector"].tolist()}
                    else:
                        # Assuming vector is already in the correct format or a raw list/vector
                        processed_vector = {"vector": vector}
                    processed_vectors.append(processed_vector)
                post["slt_vectors"] = processed_vectors

            # Process SLT type vectors if present
            if "slt_type_vectors" in post:
                processed_vectors = []
                for vector in post["slt_type_vectors"]:
                    if isinstance(vector, np.ndarray):
                        processed_vector = {"vector": vector.tolist()}
                    elif (
                        isinstance(vector, dict)
                        and "vector" in vector
                        and isinstance(vector["vector"], np.ndarray)
                    ):
                        processed_vector = {"vector": vector["vector"].tolist()}
                    else:
                        # Assuming vector is already in the correct format or a raw list/vector
                        processed_vector = {"vector": vector}
                    processed_vectors.append(processed_vector)
                post["slt_type_vectors"] = processed_vectors

            # Process OPT vectors if present
            if "opt_vectors" in post:
                processed_vectors = []
                for vector in post["opt_vectors"]:
                    if isinstance(vector, np.ndarray):
                        processed_vector = {"vector": vector.tolist()}
                    elif (
                        isinstance(vector, dict)
                        and "vector" in vector
                        and isinstance(vector["vector"], np.ndarray)
                    ):
                        processed_vector = {"vector": vector["vector"].tolist()}
                    else:
                        # Assuming vector is already in the correct format or a raw list/vector
                        processed_vector = {"vector": vector}
                    processed_vectors.append(processed_vector)
                post["opt_vectors"] = processed_vectors

            bulk_data.append(action)
            bulk_data.append(post)

        try:
            response = self.es.bulk(operations=bulk_data, refresh=True)
            return not response.get("errors", False)
        except Exception as e:
            print(f"Error bulk indexing posts: {str(e)}")
            return False

    def bulk_update_posts(self, updates):
        """
        Bulk update posts.

        Args:
            updates: List of dictionaries with post_id and fields to update
        """
        if not updates:
            return True

        try:
            bulk_data = []

            for update in updates:
                post_id = update.pop("post_id")

                # Process text_without_formula_vector if present
                if "text_without_formula_vector" in update and isinstance(
                    update["text_without_formula_vector"], np.ndarray
                ):
                    update["text_without_formula_vector"] = update[
                        "text_without_formula_vector"
                    ].tolist()

                # Process text_without_html_vector if present
                if "text_without_html_vector" in update and isinstance(
                    update["text_without_html_vector"], np.ndarray
                ):
                    update["text_without_html_vector"] = update[
                        "text_without_html_vector"
                    ].tolist()

                # Process formula vectors if present
                if "formula_vectors" in update:
                    processed_vectors = []
                    for vector in update["formula_vectors"]:
                        if isinstance(vector, np.ndarray):
                            processed_vector = {"vector": vector.tolist()}
                        elif isinstance(vector, dict):
                            processed_vector = {}
                            if "vector" in vector:
                                processed_vector["vector"] = (
                                    vector["vector"].tolist()
                                    if isinstance(vector["vector"], np.ndarray)
                                    else vector["vector"]
                                )
                            if "formula_index" in vector:
                                processed_vector["formula_index"] = vector[
                                    "formula_index"
                                ]
                            if "formula_text" in vector:
                                processed_vector["formula_text"] = vector[
                                    "formula_text"
                                ]
                        else:
                            # Assuming vector is already in the correct format (list)
                            processed_vector = {"vector": vector}
                        processed_vectors.append(processed_vector)
                    update["formula_vectors"] = processed_vectors

                # Process SLT vectors if present
                if "slt_vectors" in update:
                    processed_vectors = []
                    for vector in update["slt_vectors"]:
                        if isinstance(vector, np.ndarray):
                            processed_vector = {"vector": vector.tolist()}
                        elif isinstance(vector, dict):
                            processed_vector = {}
                            if "vector" in vector:
                                processed_vector["vector"] = (
                                    vector["vector"].tolist()
                                    if isinstance(vector["vector"], np.ndarray)
                                    else vector["vector"]
                                )
                            if "formula_index" in vector:
                                processed_vector["formula_index"] = vector[
                                    "formula_index"
                                ]
                            if "formula_text" in vector:
                                processed_vector["formula_text"] = vector[
                                    "formula_text"
                                ]
                        else:
                            # Assuming vector is already in the correct format (list)
                            processed_vector = {"vector": vector}
                        processed_vectors.append(processed_vector)
                    update["slt_vectors"] = processed_vectors

                # Process SLT type vectors if present
                if "slt_type_vectors" in update:
                    processed_vectors = []
                    for vector in update["slt_type_vectors"]:
                        if isinstance(vector, np.ndarray):
                            processed_vector = {"vector": vector.tolist()}
                        elif isinstance(vector, dict):
                            processed_vector = {}
                            if "vector" in vector:
                                processed_vector["vector"] = (
                                    vector["vector"].tolist()
                                    if isinstance(vector["vector"], np.ndarray)
                                    else vector["vector"]
                                )
                            if "formula_index" in vector:
                                processed_vector["formula_index"] = vector[
                                    "formula_index"
                                ]
                            if "formula_text" in vector:
                                processed_vector["formula_text"] = vector[
                                    "formula_text"
                                ]
                        else:
                            # Assuming vector is already in the correct format (list)
                            processed_vector = {"vector": vector}
                        processed_vectors.append(processed_vector)
                    update["slt_type_vectors"] = processed_vectors

                # Process OPT vectors if present
                if "opt_vectors" in update:
                    processed_vectors = []
                    for vector in update["opt_vectors"]:
                        if isinstance(vector, np.ndarray):
                            processed_vector = {"vector": vector.tolist()}
                        elif isinstance(vector, dict):
                            processed_vector = {}
                            if "vector" in vector:
                                processed_vector["vector"] = (
                                    vector["vector"].tolist()
                                    if isinstance(vector["vector"], np.ndarray)
                                    else vector["vector"]
                                )
                            if "formula_index" in vector:
                                processed_vector["formula_index"] = vector[
                                    "formula_index"
                                ]
                            if "formula_text" in vector:
                                processed_vector["formula_text"] = vector[
                                    "formula_text"
                                ]
                        else:
                            # Assuming vector is already in the correct format (list)
                            processed_vector = {"vector": vector}
                        processed_vectors.append(processed_vector)
                    update["opt_vectors"] = processed_vectors

                # Build bulk actions
                action = {"update": {"_index": self.posts_index_name, "_id": post_id}}
                doc = {"doc": update}

                bulk_data.append(action)
                bulk_data.append(doc)

            # 🔥 Execute bulk OUTSIDE the loop
            response = self.es.bulk(operations=bulk_data, refresh=True)

            return not response.get("errors", False)

        except Exception as e:
            print(f"Error bulk updating posts: {str(e)}")
            return False

    def create_posts_index(self):
        """Create the Elasticsearch index with appropriate mappings for posts and formulas."""
        mapping = {
            "settings": {
                "analysis": {
                    "filter": {
                        "english_stop": {"type": "stop", "stopwords": "_english_"},
                        "english_stemmer": {"type": "stemmer", "language": "english"},
                        "keep_latex": {
                            "type": "pattern_replace",
                            "pattern": r"\\\\(\(|\[).*?\\\\(\)|\])",
                            "replacement": "$0",
                        },
                    },
                    "analyzer": {
                        "post_with_formula_analyser": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": [
                                "lowercase",
                                "asciifolding",
                                "trim",
                                "english_stop",
                                "english_stemmer",
                                "keep_latex",
                            ],
                        },
                        "post_without_formula_analyser": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": [
                                "lowercase",
                                "asciifolding",
                                "trim",
                                "english_stop",
                                "english_stemmer",
                            ],
                        },
                    },
                }
            },
            "mappings": {
                "properties": {
                    "post_id": {"type": "keyword"},
                    "text": {"type": "text"},
                    "text_latex_search": {
                        "type": "text",
                        "analyzer": "post_with_formula_analyser",
                    },
                    "text_without_html": {
                        "type": "text",
                        "analyzer": "post_without_formula_analyser",
                    },
                    "text_without_formula": {
                        "type": "text",
                        "analyzer": "post_without_formula_analyser",
                    },
                    "text_without_formula_vector": {
                        "type": "dense_vector",
                        "dims": 384,
                        "index": True,
                        "similarity": "cosine",
                    },
                    "text_without_html_vector": {
                        "type": "dense_vector",
                        "dims": 384,
                        "index": True,
                        "similarity": "cosine",
                    },
                    "formulas_count": {"type": "integer"},
                    "formula_vectors": {
                        "type": "nested",
                        "properties": {
                            "vector": {
                                "type": "dense_vector",
                                "dims": 300,
                                "index": True,
                                "similarity": "cosine",
                            },
                            "formula_index": {"type": "integer"},
                            "formula_text": {"type": "text", "index": True},
                        },
                    },
                    "slt_vectors": {
                        "type": "nested",
                        "properties": {
                            "vector": {
                                "type": "dense_vector",
                                "dims": 300,
                                "index": True,
                                "similarity": "cosine",
                            },
                            "formula_index": {"type": "integer"},
                            "formula_text": {"type": "text", "index": True},
                        },
                    },
                    "slt_type_vectors": {
                        "type": "nested",
                        "properties": {
                            "vector": {
                                "type": "dense_vector",
                                "dims": 300,
                                "index": True,
                                "similarity": "cosine",
                            },
                            "formula_index": {"type": "integer"},
                            "formula_text": {"type": "text", "index": True},
                        },
                    },
                    "opt_vectors": {
                        "type": "nested",
                        "properties": {
                            "vector": {
                                "type": "dense_vector",
                                "dims": 300,
                                "index": True,
                                "similarity": "cosine",
                            },
                            "formula_index": {"type": "integer"},
                            "formula_text": {"type": "text", "index": True},
                        },
                    },
                    "formulas": {"type": "text", "index": True},
                    "formulas_ids": {"type": "integer"},
                    "formulas_mathml": {"type": "text", "index": True},
                    "formulas_latex": {"type": "text", "index": True},
                }
            },
        }

        try:
            # Se o índice já existir, precisamos excluí-lo primeiro
            if self.posts_index_exists():
                self.es.indices.delete(index=self.posts_index_name)
                print(f"Deleted existing index {self.posts_index_name}")

            self.es.indices.create(index=self.posts_index_name, body=mapping)
            print(f"Created index {self.posts_index_name} with new mapping")
        except Exception as e:
            print(f"Error creating index: {str(e)}")

    def create_formulas_index(self):
        """Create the Elasticsearch index specifically for formulas."""
        mapping = {
            "settings": {
                "analysis": {
                    "filter": {
                        "english_stop": {"type": "stop", "stopwords": "_english_"},
                        "english_stemmer": {"type": "stemmer", "language": "english"},
                    },
                    "analyzer": {
                        "formula_analyser": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": [
                                "lowercase",
                                "asciifolding",
                                "trim",
                                "english_stop",
                                "english_stemmer",
                            ],
                        },
                    },
                }
            },
            "mappings": {
                "properties": {
                    "formula_id": {"type": "keyword"},
                    "slt_text": {
                        "type": "text",
                        "analyzer": "formula_analyser",
                    },
                    "opt_text": {
                        "type": "text",
                        "analyzer": "formula_analyser",
                    },
                    "post_id": {"type": "keyword"},
                    "formula_vector": {
                        "type": "dense_vector",
                        "dims": 300,
                        "index": True,
                        "similarity": "cosine",
                    },
                    "slt_vector": {
                        "type": "dense_vector",
                        "dims": 300,
                        "index": True,
                        "similarity": "cosine",
                    },
                    "slt_type_vector": {
                        "type": "dense_vector",
                        "dims": 300,
                        "index": True,
                        "similarity": "cosine",
                    },
                    "opt_vector": {
                        "type": "dense_vector",
                        "dims": 300,
                        "index": True,
                        "similarity": "cosine",
                    },
                }
            },
        }

        try:
            # Se o índice já existir, precisamos excluí-lo primeiro
            if self.formulas_index_exists():
                self.es.indices.delete(index=self.formulas_index_name)
                print(f"Deleted existing index {self.formulas_index_name}")

            self.es.indices.create(index=self.formulas_index_name, body=mapping)
            print(f"Created index {self.formulas_index_name} with mapping")
        except Exception as e:
            print(f"Error creating formulas index: {str(e)}")

    def bulk_index_formulas(self, formulas_data):
        """
        Bulk index formulas for better performance.

        Args:
            formulas_data: List of formula dictionaries
        """
        if not formulas_data:
            return True

        bulk_data = []
        for formula in formulas_data:
            # Action description
            action = {
                "index": {
                    "_index": self.formulas_index_name,
                    "_id": formula.get(
                        "formula_id", f"{formula['post_id']}_{len(bulk_data)//2}"
                    ),
                }
            }

            # Process vectors if they are numpy arrays
            processed_formula = formula.copy()

            for vector_field in [
                "formula_vector",
                "slt_vector",
                "slt_type_vector",
                "opt_vector",
            ]:
                if vector_field in processed_formula and isinstance(
                    processed_formula[vector_field], np.ndarray
                ):
                    processed_formula[vector_field] = processed_formula[
                        vector_field
                    ].tolist()

            bulk_data.append(action)
            bulk_data.append(processed_formula)

        try:
            response = self.es.bulk(operations=bulk_data, refresh=True)
            return not response.get("errors", False)
        except Exception as e:
            print(f"Error bulk indexing formulas: {str(e)}")
            return False

    def bulk_update_text_vector(self, posts: list):
        from elasticsearch.helpers import bulk

        actions = [
            {
                "_op_type": "update",
                "_index": self.posts_index_name,
                "_id": post["post_id"],
                "doc": {
                    "text_without_formula_vector": post["text_without_formula_vector"]
                },
            }
            for post in posts
        ]

        success, errors = bulk(self.es, actions, raise_on_error=False)

        if errors:
            print(f"{len(errors)} document(s) failed to index.")
            for error in errors[:5]:  # mostra só os 5 primeiros
                print(error)
