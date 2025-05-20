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

    def get_last_indexed_post(self):
        """Get the last indexed post to resume indexing"""
        try:
            query = {"sort": [{"post_id": {"order": "desc"}}], "size": 1}
            result = self.es.search(index=self.index_name, body=query)
            if result["hits"]["total"]["value"] > 0:
                return result["hits"]["hits"][0]["_source"]
            return None
        except Exception as e:
            print(f"Error getting last indexed post: {str(e)}")
            return None

    def create_index_with_checkpoint(self):
        """Create the index with the same mappings as create_index"""
        self.create_index()

    def index_post(
        self,
        post_id,
        text,
        text_without_formula=None,
        text_without_formula_vector=None,
        formulas_slt_vectors=None,
        formulas_slt_type_vectors=None,
        formulas_opt_vectors=None,
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
            formulas_slt_vectors: List of SLT formula vectors
            formulas_slt_type_vectors: List of SLT type formula vectors
            formulas_opt_vectors: List of OPT formula vectors
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

        for field_name, field_value in [
            ("formulas_slt_vectors", formulas_slt_vectors),
            ("formulas_slt_type_vectors", formulas_slt_type_vectors),
            ("formulas_opt_vectors", formulas_opt_vectors),
        ]:
            if field_value is not None:
                processed_vectors = []
                for vector in field_value:
                    processed_vector = {
                        "vector": (
                            vector.tolist()
                            if isinstance(vector, np.ndarray)
                            else vector
                        )
                    }
                    processed_vectors.append(processed_vector)
                document[field_name] = processed_vectors

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
            for field_name in [
                "formulas_slt_vectors",
                "formulas_slt_type_vectors",
                "formulas_opt_vectors",
            ]:
                if field_name in post:
                    processed_vectors = []
                    for vector in post[field_name]:
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
                    post[field_name] = processed_vectors

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
            for field_name in [
                "formulas_slt_vectors",
                "formulas_slt_type_vectors",
                "formulas_opt_vectors",
            ]:
                if field_name in update:
                    processed_vectors = []
                    for vector in update[field_name]:
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
                    update_data[field_name] = processed_vectors

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
            for field_name in [
                "formulas_slt_vectors",
                "formulas_slt_type_vectors",
                "formulas_opt_vectors",
            ]:
                if field_name in update:
                    processed_vectors = []
                    for vector in update[field_name]:
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
                    update[field_name] = processed_vectors

            action = {"update": {"_index": self.index_name, "_id": post_id}}
            doc = {"doc": update}

            bulk_data.append(action)
            bulk_data.append(doc)

        try:
            response = self.es.bulk(operations=bulk_data, refresh=True)
            return not response.get("errors", False)
        except Exception as e:
            print(f"Error bulk updating posts: {str(e)}")
            return False

    def search_posts(self, query_vector, field="text_without_formula_vector", size=10):
        """
        Search for similar posts using vector similarity.

        Args:
            query_vector: Vector for similarity search
            field: Vector field to search on
            size: Number of results to return

        Returns:
            List of posts sorted by similarity
        """
        if isinstance(query_vector, np.ndarray):
            query_vector = query_vector.tolist()

        query = {
            "knn": {
                "field": field,
                "query_vector": query_vector,
                "k": size,
                "num_candidates": size * 2,
            }
        }

        try:
            response = self.es.search(index=self.index_name, knn=query)
            return response["hits"]["hits"]
        except Exception as e:
            print(f"Error searching posts: {str(e)}")
            return []

    def delete_index(self):
        """Delete the Elasticsearch index."""
        try:
            self.es.indices.delete(index=self.index_name)
            return True
        except Exception as e:
            print(f"Error deleting index: {str(e)}")
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
                        "exercise_analyser": {
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
                        }
                    },
                }
            },
            "mappings": {
                "properties": {
                    "post_id": {"type": "keyword"},
                    "text": {"type": "text"},
                    "text_latex_search": {
                        "type": "text",
                        "analyzer": "exercise_analyser",
                    },
                    "text_without_formula": {"type": "text"},
                    "text_without_formula_vector": {
                        "type": "dense_vector",
                        "dims": 384,
                        "index": True,
                        "similarity": "cosine",
                    },
                    "formulas_slt_vectors": {
                        "type": "nested",
                        "properties": {
                            "vector": {
                                "type": "dense_vector",
                                "dims": 300,
                                "index": True,
                                "similarity": "cosine",
                            }
                        },
                    },
                    "formulas_slt_type_vectors": {
                        "type": "nested",
                        "properties": {
                            "vector": {
                                "type": "dense_vector",
                                "dims": 300,
                                "index": True,
                                "similarity": "cosine",
                            }
                        },
                    },
                    "formulas_opt_vectors": {
                        "type": "nested",
                        "properties": {
                            "vector": {
                                "type": "dense_vector",
                                "dims": 300,
                                "index": True,
                                "similarity": "cosine",
                            }
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
            self.es.indices.create(index=self.index_name, body=mapping)
            print(f"Created index {self.index_name}")
        except Exception as e:
            print(f"Error creating index: {str(e)}")

    def search_posts_after_id(self, last_post_id: int, size: int = 100):
        body = {
            "size": size,
            "query": {"range": {"post_id": {"gt": last_post_id}}},
            "sort": [{"post_id": "asc"}],
        }

        res = self.es.search(index=self.index_name, body=body)
        return [hit["_source"] for hit in res["hits"]["hits"]]

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
