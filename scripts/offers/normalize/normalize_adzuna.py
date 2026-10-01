import json
from pathlib import Path

from scripts.offers.normalize.mappings.departments import get_department_code

RAW_DIR = Path("data/raw/adzuna")
PROCESSED_DIR = Path("data/processed/adzuna")


CATEGORY_LABELS = {
    "A": "Agriculture / Pêche / Espaces verts et naturels / Soins aux animaux",
    "B": "Arts / Artisanat d'art",
    "C": "Banque / Assurance",
    "C15": "Immobilier",
    "D": "Commerce / Vente",
    "E": "Communication / Multimédia",
    "F": "Bâtiment / Travaux Publics",
    "G": "Hôtellerie - Restauration / Tourisme / Animation",
    "H": "Industrie",
    "I": "Installation / Maintenance",
    "J": "Santé",
    "K": "Services à la personne / à la collectivité",
    "L": "Spectacle",
    "L14": "Sport",
    "M": "Achats / Comptabilité / Gestion",
    "M13": "Direction d'entreprise",
    "M14": "Conseil / Études",
    "M15": "Ressources Humaines",
    "M16": "Secrétariat / Assistanat",
    "M17": "Marketing / Stratégie commerciale",
    "M18": "Informatique / Télécommunication",
    "N": "Transport / Logistique",
    "UNKNOWN": "Non classé / Domaine inconnu",
}


ADZUNA_CATEGORY_MAPPING = {
    "creative-design-jobs": "B",
    "property-jobs": "C15",
    "sales-jobs": "D",
    "retail-jobs": "D",
    "trade-construction-jobs": "F",
    "travel-jobs": "G",
    "hospitality-catering-jobs": "G",
    "manufacturing-jobs": "H",
    "energy-oil-gas-jobs": "H",
    "maintenance-jobs": "I",
    "healthcare-nursing-jobs": "J",
    "social-work-jobs": "K",
    "charity-voluntary-jobs": "K",
    "domestic-help-cleaning-jobs": "K",
    "teaching-jobs": "K",
    "accounting-finance-jobs": "M",
    "admin-jobs": "M",
    "consultancy-jobs": "M14",
    "engineering-jobs": "M14",
    "scientific-qa-jobs": "M14",
    "customer-services-jobs": "M14",
    "legal-jobs": "M14",
    "hr-jobs": "M15",
    "pr-advertising-marketing-jobs": "M17",
    "it-jobs": "M18",
    "logistics-warehouse-jobs": "N",
    "other-general-jobs": "UNKNOWN",
    "graduate-jobs": "UNKNOWN",
    "part-time-jobs": "UNKNOWN",
}


def load_json(file_path: Path):
    """Charge un fichier JSON."""
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


def save_json(data, file_path: Path):
    """Enregistre les données normalisées au format JSON."""
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=4,
        )


def to_float(value):
    """Convertit une valeur numérique en float si possible."""
    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_salary(salary_min, salary_max):
    """
    Produit une valeur unique à partir de salary_min et salary_max.

    - si les deux valeurs existent : moyenne ;
    - si une seule existe : cette valeur ;
    - sinon : None.
    """
    minimum = to_float(salary_min)
    maximum = to_float(salary_max)

    if minimum is not None and maximum is not None:
        return (minimum + maximum) / 2

    if minimum is not None:
        return minimum

    if maximum is not None:
        return maximum

    return None


def normalize_category(category_tag):
    """
    Traduit un category.tag Adzuna vers la catégorie ROME normalisée.

    Si le tag est absent ou inconnu, la catégorie UNKNOWN est utilisée.
    """
    if not isinstance(category_tag, str) or not category_tag.strip():
        return "UNKNOWN", CATEGORY_LABELS["UNKNOWN"]

    normalized_tag = category_tag.strip().lower()
    category = ADZUNA_CATEGORY_MAPPING.get(normalized_tag, "UNKNOWN")

    return category, CATEGORY_LABELS[category]


def normalize_offer(offer):
    """
    Transforme une offre Adzuna vers le schéma normalisé du projet.
    """
    company = offer.get("company") or {}
    source_category = offer.get("category") or {}
    location = offer.get("location") or {}
    area = location.get("area") or []

    department_name = area[2] if len(area) > 2 else None
    location_department = get_department_code(department_name)

    category, category_label = normalize_category(source_category.get("tag"))

    return {
        "source": "adzuna",
        "source_id": offer.get("id"),
        "title": offer.get("title"),
        "company": company.get("display_name").lower() if company.get("display_name") else None,
        "description": offer.get("description"),
        "creationDate": offer.get("created"),
        "contractType": offer.get("contract_type"),
        "contractTime": offer.get("contract_time"),
        "locationZipCode": None,
        "locationDepartment": location_department,
        "locationCity": area[3] if len(area) > 3 else None,
        "locationLatitude": to_float(offer.get("latitude")),
        "locationLongitude": to_float(offer.get("longitude")),
        "salary": normalize_salary(
            offer.get("salary_min"),
            offer.get("salary_max"),
        ),
        "url": offer.get("redirect_url"),
        "codeNAF": None,
        "category": category,        
        "categoryLabel": category_label,
        "romeCode": None,
        "romeLibelle": None,
        "skills": [],
        "education": None,
        "educationField": None,
    }


def process_file(raw_file: Path):
    """
    Normalise un fichier RAW Adzuna.

    La réponse Adzuna contient les offres dans la clé 'results'.
    Le fichier PROCESSED conserve le même nom que le fichier RAW.
    """
    raw_data = load_json(raw_file)

    offers = raw_data.get("results", [])

    if not isinstance(offers, list):
        raise ValueError(
            f"La clé 'results' de {raw_file} ne contient pas une liste."
        )

    normalized_offers = [normalize_offer(offer) for offer in offers]

    processed_file = PROCESSED_DIR / raw_file.name
    save_json(normalized_offers, processed_file)

    print(
        f"{raw_file.name} : "
        f"{len(normalized_offers)} offre(s) normalisée(s) "
        f"-> {processed_file}"
    )


def main():
    """
    Normalise tous les fichiers JSON présents dans data/raw/adzuna.
    """
    raw_files = sorted(RAW_DIR.glob("*.json"))

    if not raw_files:
        print(f"Aucun fichier JSON trouvé dans {RAW_DIR}")
        return

    for raw_file in raw_files:
        process_file(raw_file)


if __name__ == "__main__":
    main()
