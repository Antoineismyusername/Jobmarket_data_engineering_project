import json
import logging
import os
from datetime import datetime
from pathlib import Path
import time

import requests
from dotenv import load_dotenv


# ----- Configuration

TOKEN_URL = (
    "https://entreprise.francetravail.fr/"
    "connexion/oauth2/access_token?realm=/partenaire"
)

SEARCH_URL = (
    "https://api.francetravail.io/"
    "partenaire/offresdemploi/v2/offres/search"
)

RAW_DIR = Path("data/raw/france_travail")

RANGE_SIZE = 150
DELAY = 0.25
# Limite de sécurité conservée du script initial (pas une garantie de l'API).
MAX_RANGE_END = 12000

GRANDS_DOMAINES = [
    "A", "B", "C", "C15", "D", "E", "F", "G", "H", "I", "J", "K",
    "L", "L14", "M", "M13", "M14", "M15", "M16", "M17", "M18", "N"
]

LOG_DIR = Path("logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=LOG_DIR / "jobmarket.log",
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    encoding="utf-8"
)

logger = logging.getLogger("extraction_france_travail")


# ----- Récupération des identifiants France Travail sous forme de variables d'environnement

load_dotenv()

CLIENT_ID = os.getenv("FRANCE_TRAVAIL_CLIENT_ID")
CLIENT_SECRET = os.getenv("FRANCE_TRAVAIL_CLIENT_SECRET")


# ----- Authentification

def get_access_token():
    """
    Obtient un token d'accès à l'API France Travail.
    """
    data = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": "api_offresdemploiv2 o2dsoffre"
    }

    response = requests.post(TOKEN_URL, data=data)
    response.raise_for_status()

    logger.info("Authentification France Travail réussie.")

    return response.json()["access_token"]


# ----- Première récupération d'offres d'emploi

def get_offers(token, querystring):
    """
    Récupère les offres d'emploi depuis l'API France Travail.
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }

    response = requests.get(
        SEARCH_URL,
        headers=headers,
        params=querystring
    )

    response.raise_for_status()

    return response


# ----- Enregistrement des données brutes

def save_raw_response(response, timestamp, grand_domaine, start, end):
    """
    Enregistre une tranche de résultats de l'API France Travail.
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    file_path = (
        RAW_DIR
        / f"france_travail_{timestamp}_{grand_domaine}_range_{start:04d}_{end:04d}.json"
    )

    data = response.json()

    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

    logger.info("Range %s-%s enregistrée dans %s.", start, end, file_path)

    return file_path

# ----- Cartographier les clés de premier niveau des données

#offers = data["resultats"]

#all_keys = set()

#for offer in offers:
#    all_keys.update(offer.keys())

#for key in sorted(all_keys):
#    print(key)


# ----- Cartographier l'ensemble des clés du JSON

def get_json_keys(data, prefix=""):
    """
    Récupère de manière récursive les chemins des clés d'un objet JSON.
    """
    keys = set()

    if isinstance(data, dict):
        for key, value in data.items():
            full_key = f"{prefix}.{key}" if prefix else key
            keys.add(full_key)
            keys.update(get_json_keys(value, full_key))

    elif isinstance(data, list):
        for item in data:
            keys.update(get_json_keys(item, prefix))

    return keys


# ----- Programme principal

def main():

    logger.info("Début de l'extraction France Travail, tous domaines.")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    all_keys = set()
    total_downloaded = 0
    incomplete_domains = []

    for grand_domaine in GRANDS_DOMAINES:

        print(f"\nExtraction du domaine {grand_domaine}")
        logger.info("Début du domaine %s.", grand_domaine)

        querystring = {
            "grandDomaine": grand_domaine,
            "departement": "34"
        }

        # Un token récent pour chaque domaine.
        token = get_access_token()
        domain_downloaded = 0

        # La pagination recommence à zéro pour chaque domaine.
        for start in range(0, MAX_RANGE_END + 1, RANGE_SIZE):

            end = min(start + RANGE_SIZE - 1, MAX_RANGE_END)
            querystring["range"] = f"{start}-{end}"

            response = get_offers(token, querystring)
            time.sleep(DELAY)

            if response.status_code == 204:
                logger.info("Domaine %s : aucune offre restante (204).", grand_domaine)
                break

            data = response.json()
            offers = data.get("resultats", [])

            if not offers:
                logger.info("Domaine %s : page vide, fin du parcours.", grand_domaine)
                break

            domain_downloaded += len(offers)
            total_downloaded += len(offers)
            all_keys.update(get_json_keys(offers))

            save_raw_response(
                response,
                timestamp,
                grand_domaine,
                start,
                end
            )

            print(
                f"Domaine {grand_domaine} | Range {start}-{end} : "
                f"{len(offers)} offres | "
                f"Total du domaine : {domain_downloaded}"
            )

            logger.info(
                "Domaine %s | Range %s-%s : %s offres | Total domaine : %s.",
                grand_domaine, start, end, len(offers), domain_downloaded
            )

            content_range = response.headers.get("Content-Range", "")
            total_text = content_range.rsplit("/", 1)[-1]

            if total_text.isdigit():
                total_results = int(total_text)

                if domain_downloaded >= total_results:
                    break

            # Sans total exploitable, HTTP 200 signale une réponse complète.
            elif response.status_code == 200:
                break

        else:
            # Ce bloc s'exécute seulement si la limite est atteinte sans break.
            incomplete_domains.append(grand_domaine)
            logger.warning(
                "Domaine %s : limite MAX_RANGE_END atteinte, extraction incomplète.",
                grand_domaine
            )

        print(f"Domaine {grand_domaine} terminé : {domain_downloaded} offres.")
        logger.info("Fin du domaine %s : %s offres.", grand_domaine, domain_downloaded)

    # Ne pas présenter comme réussie une extraction arrêtée par notre limite.
    if incomplete_domains:
        raise RuntimeError(
            "Extraction incomplète : limite de pagination atteinte pour "
            + ", ".join(incomplete_domains)
        )

    print(f"\nExtraction terminée : {total_downloaded} offres récupérées au total.")
    logger.info("Extraction terminée : %s offres au total.", total_downloaded)

    # Le total compte les résultats reçus, pas les identifiants uniques.
    # Les éventuels doublons sont traités par le chargeur MongoDB.

    # Optionnel : affichage de toutes les clés rencontrées.
    # for key in sorted(all_keys):
    #     print(key)


if __name__ == "__main__":
    main()

