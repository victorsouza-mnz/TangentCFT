from elasticsearch import Elasticsearch
import numpy as np
import json


class ElasticsearchService:
    def __init__(self, host="localhost", port=9200, index_name="posts"):
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
        self.index_name = index_name

        # Create index if it doesn't exist
        if not self.index_exists():
            self.create_index()

    def index_exists(self):
        """Check if the index exists"""
        return self.es.indices.exists(index=self.index_name)

    def index_post(
        self,
        post_id,
        text,
        text_without_formula=None,
        text_without_formula_vector=None,
        formula_vectors=None,
        slt_vectors=None,
        slt_type_vectors=None,
        opt_vectors=None,
        formulas=None,
        formulas_ids=None,
        formulas_mathml=None,
        formulas_latex=None,
    ):
        """
        Index a post in Elasticsearch.

        Args:
            post_id: Unique identifier for the post
            text: The full post text
            text_without_formula: Text with formulas removed
            text_without_formula_vector: Vector of text without formulas
            formula_vectors: List of formula vectors
            slt_vectors: List of SLT vectors
            slt_type_vectors: List of SLT type vectors
            opt_vectors: List of OPT vectors
            formulas: List of formula strings
            formulas_ids: List of formula IDs
            formulas_mathml: List of MathML formula strings
            formulas_latex: List of LaTeX formula strings
        """
        document = {"post_id": post_id, "text": text}

        if text_without_formula:
            document["text_without_formula"] = text_without_formula

        if text_without_formula_vector is not None:
            document["text_without_formula_vector"] = (
                text_without_formula_vector.tolist()
                if isinstance(text_without_formula_vector, np.ndarray)
                else text_without_formula_vector
            )

        # Process formula vectors
        if formula_vectors is not None:
            processed_vectors = []
            for vector in formula_vectors:
                processed_vector = {
                    "vector": (
                        vector.tolist() if isinstance(vector, np.ndarray) else vector
                    )
                }
                processed_vectors.append(processed_vector)
            document["formula_vectors"] = processed_vectors

        # Process SLT vectors
        if slt_vectors is not None:
            processed_vectors = []
            for vector in slt_vectors:
                processed_vector = {
                    "vector": (
                        vector.tolist() if isinstance(vector, np.ndarray) else vector
                    )
                }
                processed_vectors.append(processed_vector)
            document["slt_vectors"] = processed_vectors

        # Process SLT type vectors
        if slt_type_vectors is not None:
            processed_vectors = []
            for vector in slt_type_vectors:
                processed_vector = {
                    "vector": (
                        vector.tolist() if isinstance(vector, np.ndarray) else vector
                    )
                }
                processed_vectors.append(processed_vector)
            document["slt_type_vectors"] = processed_vectors

        # Process OPT vectors
        if opt_vectors is not None:
            processed_vectors = []
            for vector in opt_vectors:
                processed_vector = {
                    "vector": (
                        vector.tolist() if isinstance(vector, np.ndarray) else vector
                    )
                }
                processed_vectors.append(processed_vector)
            document["opt_vectors"] = processed_vectors

        if formulas:
            document["formulas"] = formulas

        if formulas_ids:
            document["formulas_ids"] = formulas_ids

        if formulas_mathml:
            document["formulas_mathml"] = formulas_mathml

        if formulas_latex:
            document["formulas_latex"] = formulas_latex

        try:
            self.es.index(index=self.index_name, id=post_id, document=document)
            return True
        except Exception as e:
            print(f"Error indexing post {post_id}: {str(e)}")
            return False

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
            action = {"index": {"_index": self.index_name, "_id": post["post_id"]}}

            # Process text_without_formula_vector if present
            if "text_without_formula_vector" in post and isinstance(
                post["text_without_formula_vector"], np.ndarray
            ):
                post["text_without_formula_vector"] = post[
                    "text_without_formula_vector"
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

    def update_post(self, post_id, update_data):
        """
        Update specific fields of a post.

        Args:
            post_id: ID of the post to update
            update_data: Dictionary of fields to update
        """
        try:
            # Process text_without_formula_vector if present
            if "text_without_formula_vector" in update_data and isinstance(
                update_data["text_without_formula_vector"], np.ndarray
            ):
                update_data["text_without_formula_vector"] = update_data[
                    "text_without_formula_vector"
                ].tolist()

            # Process formula vectors if present
            if "formula_vectors" in update_data:
                processed_vectors = []
                for vector in update_data["formula_vectors"]:
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
                update_data["formula_vectors"] = processed_vectors

            # Process SLT vectors if present
            if "slt_vectors" in update_data:
                processed_vectors = []
                for vector in update_data["slt_vectors"]:
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
                update_data["slt_vectors"] = processed_vectors

            # Process SLT type vectors if present
            if "slt_type_vectors" in update_data:
                processed_vectors = []
                for vector in update_data["slt_type_vectors"]:
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
                update_data["slt_type_vectors"] = processed_vectors

            # Process OPT vectors if present
            if "opt_vectors" in update_data:
                processed_vectors = []
                for vector in update_data["opt_vectors"]:
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
                update_data["opt_vectors"] = processed_vectors

            self.es.update(index=self.index_name, id=post_id, doc=update_data)
            return True
        except Exception as e:
            print(f"Error updating post {post_id}: {str(e)}")
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
                action = {"update": {"_index": self.index_name, "_id": post_id}}
                doc = {"doc": update}

                bulk_data.append(action)
                bulk_data.append(doc)

            # 🔥 Execute bulk OUTSIDE the loop
            response = self.es.bulk(operations=bulk_data, refresh=True)

            return not response.get("errors", False)

        except Exception as e:
            print(f"Error bulk updating posts: {str(e)}")
            return False

    def create_index(self):
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
            if self.index_exists():
                self.es.indices.delete(index=self.index_name)
                print(f"Deleted existing index {self.index_name}")

            self.es.indices.create(index=self.index_name, body=mapping)
            print(f"Created index {self.index_name} with new mapping")
        except Exception as e:
            print(f"Error creating index: {str(e)}")

    def bulk_update_text_vector(self, posts: list):
        from elasticsearch.helpers import bulk

        actions = [
            {
                "_op_type": "update",
                "_index": self.index_name,
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
