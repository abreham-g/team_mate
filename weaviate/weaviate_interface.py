from weaviate import Client
from weaviate.exceptions import WeaviateException  # Import general exception

def setup_weaviate_interface():
    try:
        client = Client("http://localhost:8080")
        return WeaviateInterface(client)
    except WeaviateException as e:  # Catching general Weaviate exception
        print(f"An error occurred: {e}")
        return None

class WeaviateInterface:
    def __init__(self, client):
        self.client = client

    async def create_schema(self, schema_dict):
        try:
            self.client.schema.create(schema_dict)
            return True
        except WeaviateException as e:  # Catching general Weaviate exception
            print(f"Failed to create schema: {e}")
            return False

    async def load_data_from_csv(self, csv_path, class_name):
        try:
            self.client.batch.import_csv(csv_path, class_name)
            return True
        except WeaviateException as e:  # Catching general Weaviate exception
            print(f"Failed to load data from CSV: {e}")
            return False

    async def semantic_search(self, query, class_name):
        try:
            result = self.client.query.get(class_name).with_near_text({"concepts": [query]}).do()
            return result
        except WeaviateException as e:  # Catching general Weaviate exception
            print(f"Failed to perform semantic search: {e}")
            return None
