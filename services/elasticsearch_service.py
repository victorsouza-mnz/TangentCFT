from elasticsearch import Elasticsearch
import logging
import numpy as np
import json


class ElasticsearchService:
    def __init__(self, host="localhost", port=9200, index_name="questions"):
        """
        Initialize Elasticsearch service.

        Args:
            host: Elasticsearch host
            port: Elasticsearch port
            index_name: Name of the index to use
        """
        self.es = Elasticsearch([f"http://{host}:{port}"])
        self.index_name = index_name
        self.logger = logging.getLogger(__name__)

        # Create index if it doesn't exist
        if not self.es.indices.exists(index=self.index_name):
            self.create_index()

    def create_index(self):
        """Create the Elasticsearch index with appropriate mappings for formula vectors."""
        mapping = {
            "mappings": {
                "properties": {
                    "formula_id": {"type": "keyword"},
                    "title": {"type": "text"},
                    "content": {"type": "text"},
                    "formula_vector": {
                        "type": "dense_vector",
                        "dims": 300,  # Assuming 300 dimensions based on your model
                        "index": True,
                        "similarity": "cosine",
                    },
                }
            }
        }

        try:
            self.es.indices.create(index=self.index_name, body=mapping)
            self.logger.info(f"Created index {self.index_name}")
        except Exception as e:
            self.logger.error(f"Error creating index: {str(e)}")

    def index_formula(self, formula_id, title, content, vector):
        """
        Index a formula in Elasticsearch.

        Args:
            formula_id: Unique identifier for the formula
            title: Title or name of the document containing the formula
            content: The actual formula content
            vector: Vector representation of the formula (numpy array)
        """
        document = {
            "formula_id": formula_id,
            "title": title,
            "content": content,
            "formula_vector": (
                vector.tolist() if isinstance(vector, np.ndarray) else vector
            ),
        }

        try:
            self.es.index(index=self.index_name, id=formula_id, document=document)
            return True
        except Exception as e:
            self.logger.error(f"Error indexing formula {formula_id}: {str(e)}")
            return False

    def bulk_index_formulas(self, formulas_data):
        """
        Bulk index formulas for better performance.

        Args:
            formulas_data: List of dictionaries with formula_id, title, content, and vector
        """
        if not formulas_data:
            return True

        bulk_data = []
        for formula in formulas_data:
            # Action description
            action = {
                "index": {"_index": self.index_name, "_id": formula["formula_id"]}
            }
            # Convert numpy array to list if needed
            if isinstance(formula.get("vector"), np.ndarray):
                formula["formula_vector"] = formula["vector"].tolist()
            else:
                formula["formula_vector"] = formula["vector"]

            # Remove the original vector field
            if "vector" in formula:
                del formula["vector"]

            bulk_data.append(action)
            bulk_data.append(formula)

        try:
            response = self.es.bulk(operations=bulk_data, refresh=True)
            return not response.get("errors", False)
        except Exception as e:
            self.logger.error(f"Error bulk indexing formulas: {str(e)}")
            return False

    def search_formulas(self, query_vector, size=10):
        """
        Search for similar formulas using vector similarity.

        Args:
            query_vector: Vector representation of the query formula
            size: Number of results to return

        Returns:
            List of formula documents sorted by similarity
        """
        if isinstance(query_vector, np.ndarray):
            query_vector = query_vector.tolist()

        query = {
            "knn": {
                "field": "formula_vector",
                "query_vector": query_vector,
                "k": size,
                "num_candidates": size * 2,
            },
            "_source": ["formula_id", "title", "content"],
        }

        try:
            response = self.es.search(index=self.index_name, knn=query)
            return response["hits"]["hits"]
        except Exception as e:
            self.logger.error(f"Error searching formulas: {str(e)}")
            return []

    def delete_index(self):
        """Delete the Elasticsearch index."""
        try:
            self.es.indices.delete(index=self.index_name)
            return True
        except Exception as e:
            self.logger.error(f"Error deleting index: {str(e)}")
            return False
