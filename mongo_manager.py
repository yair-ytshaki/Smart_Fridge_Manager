import os
import urllib.parse
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.server_api import ServerApi

# Load environment variables from .env
load_dotenv()

MONGODB_USERNAME = os.getenv("MONGODB_USERNAME")
MONGODB_PASSWORD = os.getenv("MONGODB_PASSWORD")
MONGODB_URI = os.getenv("MONGODB_URI")


class MongoManager:
    def __init__(self, db_name="smart_fridge_raw"):
        if not MONGODB_URI:
            raise ValueError("MONGODB_URI is not defined in the environment variables.")

        # Construct the authenticated connection URI
        formatted_uri = MONGODB_URI
        if MONGODB_USERNAME and MONGODB_PASSWORD:
            # URL-encode credentials to safely handle special characters (e.g., '@', ':', '/')
            encoded_user = urllib.parse.quote_plus(MONGODB_USERNAME)
            encoded_pass = urllib.parse.quote_plus(MONGODB_PASSWORD)

            if "://" in formatted_uri and "@" not in formatted_uri:
                protocol, rest = formatted_uri.split("://", 1)
                formatted_uri = f"{protocol}://{encoded_user}:{encoded_pass}@{rest}"

        self.client = MongoClient(formatted_uri, server_api=ServerApi("1"))
        self.db = self.client[db_name]

    def test_connection(self):
        """Sends a ping to confirm successful authentication with Atlas."""
        try:
            self.client.admin.command("ping")
            print("Connected successfully to MongoDB Atlas!")
            return True
        except Exception as e:
            print(f"MongoDB Connection Failed: {e}")
            return False

    def get_raw_collection(self, collection_name="raw_supermarket_feeds"):
        """Returns target collection for raw market feed persistence."""
        return self.db[collection_name]


if __name__ == "__main__":
    mongo = MongoManager()
    mongo.test_connection()