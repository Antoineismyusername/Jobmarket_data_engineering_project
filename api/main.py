import base64
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from api.recommendation_api import recommend_from_database
from scripts.offers.load.load_mongodb import get_collection


PROJECT_ROOT = Path(__file__).resolve().parents[1]

load_dotenv(PROJECT_ROOT / ".env")

app = FastAPI(
    title="JobMarket API",
    description="API de consultation et de recommandation d'offres d'emploi.",
)

# ----- Modèles des requêtes

class CityRequest(BaseModel):
    city: str
    limit: int = 10


class CategoryRequest(BaseModel):
    category: str
    limit: int = 10


class RecommendationRequest(BaseModel):
    keywords: str
    city: Optional[str] = None
    department: Optional[str] = None
    category: Optional[str] = None
    top_n: int = 10


# ----- Authentification BasicAuth

def authenticate(authorization):

    try:
        credentials = authorization.split(" ")[1]

        decoded = base64.b64decode(credentials).decode("utf-8")

        username, password = decoded.split(":", 1)

    except:
        raise HTTPException(
            status_code=422,
            detail="Authentification incorrecte."
        )

    if (
        username != os.getenv("API_USERNAME")
        or password != os.getenv("API_PASSWORD")
    ):
        raise HTTPException(
            status_code=422,
            detail="Identifiants incorrects."
        )


# ----- Accueil

@app.get("/")
def home():
    return {
        "message": "JobMarket API"
    }


# ----- Offres par ville

@app.post("/offers/city")
def get_offers_by_city(city_request: CityRequest, authorization: str = Header(None)):

    authenticate(authorization)

    collection = get_collection()

    offers = list(
        collection.find(
            {},
            {"_id": 0}
        )
    )

    matching_offers = []

    for offer in offers:

        city = offer.get("locationCity")

        if city.lower() == city_request.city.lower():
            matching_offers.append(offer)

        if len(matching_offers) >= city_request.limit:
            break

    return {
        "city": city_request.city,
        "count": len(matching_offers),
        "offers": matching_offers
    }


# ----- Offres par catégorie

@app.post("/offers/category")
def get_offers_by_category(category_request: CategoryRequest, authorization: str = Header(None)):

    authenticate(authorization)

    collection = get_collection()

    offers = list(
        collection.find(
            {},
            {"_id": 0}
        )
    )

    matching_offers = []

    for offer in offers:

        category = offer.get("category")
        category_label = offer.get("categoryLabel")

        if category.lower() == category_request.category.lower():
            matching_offers.append(offer)

        if len(matching_offers) >= category_request.limit:
            break

    return {
        "category": category_request.category,
        "count": len(matching_offers),
        "offers": matching_offers
    }


# ----- Recommandations

@app.post("/recommendations")
def get_recommendations(recommendation_request: RecommendationRequest, authorization: str = Header(None)):

    authenticate(authorization)

    collection = get_collection()

    try:
        recommendations = recommend_from_database(
            collection=collection,
            recommendation_request=recommendation_request
        )

    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail=str(error)
        )

    return {
        "count": len(recommendations),
        "recommendations": recommendations
    }