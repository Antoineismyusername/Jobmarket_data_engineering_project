import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from pymongo import MongoClient


PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(PROJECT_ROOT / ".env")


def get_mongo_client():
    """Crée et retourne un client MongoDB."""

    return MongoClient(
        host=os.getenv("MONGO_HOST"),
        port=int(os.getenv("MONGO_PORT")),
        username=os.getenv("MONGO_USER"),
        password=os.getenv("MONGO_PASSWORD"),
        authSource=os.getenv("MONGO_DB"),
    )


def load_offers():
    """Charge les offres MongoDB dans un DataFrame pandas."""

    client = get_mongo_client()

    try:
        db = client[os.getenv("MONGO_DB")]
        collection = db["offers"]

        projection = {
            "_id": 1,
            "title": 1,
            "company": 1,
            "description": 1,
            "locationCity": 1,
            "locationDepartment": 1,
            "category": 1,
            "categoryLabel": 1,
        }

        offers = list(
            collection.find({}, projection)
        )

    finally:
        client.close()

    return pd.DataFrame(offers)

# test du script
if __name__ == "__main__":
    print("Longueur du DataFrame : ", len(load_offers()))
