import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import BulkWriteError


PROJECT_ROOT = Path(__file__).resolve().parents[3]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=LOG_DIR / "jobmarket.log",
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    encoding="utf-8"
)

logger = logging.getLogger("load_mongodb")

load_dotenv(PROJECT_ROOT / ".env")


def get_collection():
    client = MongoClient(
        host=os.getenv("MONGO_HOST"),
        port=int(os.getenv("MONGO_PORT")),
    )

    db_name = os.getenv("MONGO_DB")
    db = client[db_name]

    logger.info("Collection MongoDB sélectionnée : %s.offers", db_name)

    return db["offers"]


def load_json(file_path):
    """Charge un fichier JSON normalisé."""
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


def process_file(file_path, collection):
    """Insère dans MongoDB les offres contenues dans un fichier JSON."""

    offers = load_json(file_path)

    if not offers:
        print(f"{file_path} : aucune offre.")
        logger.warning("%s : aucune offre à insérer.", file_path)
        return

    try:
        result = collection.insert_many(
            offers,
            ordered=False,
        )

        inserted = len(result.inserted_ids)

        print(
            f"{file_path} : "
            f"{inserted} offre(s) insérée(s)."
        )

        logger.info(
            "%s : %s offre(s) insérée(s).",
            file_path,
            inserted
        )

    except BulkWriteError as error:
        write_errors = error.details.get("writeErrors", [])

        duplicate_errors = [
            err for err in write_errors
            if err.get("code") == 11000
        ]

        other_errors = [
            err for err in write_errors
            if err.get("code") != 11000
        ]

        inserted = error.details.get("nInserted", 0)

        print(f"{inserted} offres insérées")
        print(f"{len(duplicate_errors)} doublons ignorés")

        logger.info("%s offres insérées depuis %s.", inserted, file_path)
        logger.warning(
            "%s doublon(s) ignoré(s) dans %s.",
            len(duplicate_errors),
            file_path
        )

        if other_errors:
            print("Erreurs MongoDB inattendues :", other_errors)

            logger.error(
                "%s erreur(s) MongoDB inattendue(s) dans %s.",
                len(other_errors),
                file_path
            )

            raise


def main():

    logger.info("Début du chargement des données dans MongoDB.")

    collection = get_collection()

    processed_files = sorted(PROCESSED_DIR.rglob("*.json"))

    if not processed_files:
        print(f"Aucun fichier JSON trouvé dans {PROCESSED_DIR}")
        logger.warning("Aucun fichier JSON trouvé dans %s.", PROCESSED_DIR)
        return

    logger.info("%s fichier(s) JSON à traiter.", len(processed_files))

    for file_path in processed_files:
        process_file(file_path, collection)

    logger.info("Chargement MongoDB terminé.")


if __name__ == "__main__":
    main()

