import pandas as pd

from scripts.recommendation.preprocessing import prepare_offer_text
from scripts.recommendation.recommender import (
    build_tfidf_matrix,
    recommend
)


def recommend_from_database(
    collection,
    recommendation_request
):

    # Récupération des offres depuis MongoDB
    offers = list(
        collection.find(
            {},
            {"_id": 0}
        )
    )

    if not offers:
        return []

    # Création du DataFrame
    df = pd.DataFrame(offers)

    # Conservation de l'offre complète
    # pour la réponse finale
    df["offer"] = offers

    # Création de la colonne text
    df = prepare_offer_text(df)

    # Construction du TF-IDF
    vectorizer, tfidf_matrix = build_tfidf_matrix(df)

    # Recommandation
    results = recommend(
        df=df,
        vectorizer=vectorizer,
        tfidf_matrix=tfidf_matrix,
        keywords=recommendation_request.keywords,
        locationCity=recommendation_request.city,
        locationDepartment=recommendation_request.department,
        category=recommendation_request.category,
        top_n=recommendation_request.top_n
    )

    # Préparation de la réponse
    recommendations = []

    for _, row in results.iterrows():

        # offer est un dictionnaire
        offer = row["offer"]

        # on ajoute à offer le score        
        offer["score"] = round(float(row["score"]),4)

        recommendations.append(offer)

    return recommendations