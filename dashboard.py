"""Lancer depuis la racine : python -m streamlit run dashboard.py"""
import os
import time
from pathlib import Path

import pandas as pd
import requests
import streamlit as st
from dotenv import load_dotenv
from nltk.corpus import stopwords
from wordcloud import WordCloud

load_dotenv(Path(__file__).resolve().parent / ".env")
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000").rstrip("/")
AUTH = (os.getenv("API_USERNAME", ""), os.getenv("API_PASSWORD", ""))

CATEGORIES = {
    "A": "Agriculture / Pêche / Espaces verts et naturels / Soins aux animaux",
    "B": "Arts / Artisanat d’art",
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
    "M14": "Conseil / Etudes",
    "M15": "Ressources Humaines",
    "M16": "Secrétariat / Assistanat",
    "M17": "Marketing / Stratégie commerciale",
    "M18": "Informatique / Télécommunication",
    "N": "Transport / Logistique",
}

st.set_page_config(page_title="JobMarket", page_icon="🔎", layout="wide")
st.title("JobMarket")
st.caption("Explorer les offres d’emploi et trouver celles qui correspondent à tes recherches.")


def call_api(method, endpoint, payload=None, auth=AUTH):
    """Conserver aussi les informations utiles pour comprendre la requête."""
    result = {"method": method, "endpoint": endpoint, "payload": payload}
    start = time.perf_counter()
    try:
        response = requests.request(
            method, API_URL + endpoint, json=payload,
            auth=auth, timeout=120, allow_redirects=False
        )
        result["status"] = response.status_code
        try:
            result["data"] = response.json()
        except ValueError:
            result["data"] = {"detail": "La réponse reçue n’est pas du JSON."}
        result["ok"] = 200 <= response.status_code < 300
    except requests.exceptions.Timeout:
        result.update(ok=False, data={"detail": "Délai dépassé (120 secondes)."})
    except requests.exceptions.RequestException:
        result.update(ok=False, data={"detail": "API inaccessible. Vérifie son lancement et API_URL."})
    result["seconds"] = round(time.perf_counter() - start, 2)
    return result


def show_response(result):
    """Afficher le résultat technique, sans jamais afficher les identifiants."""
    st.caption(
        f'{result["method"]} {result["endpoint"]} · '
        f'HTTP {result.get("status", "—")} · {result["seconds"]} s'
    )
    with st.expander("Requête et réponse JSON"):
        if result["payload"] is not None:
            st.write("Paramètres envoyés")
            st.json(result["payload"])
        st.write("Réponse reçue")
        st.json(result["data"])
    if not result["ok"]:
        st.error("La requête a échoué. Consulte le détail de la réponse ci-dessus.")


def show_offers(offers):
    if not offers:
        st.info("Aucune offre trouvée.")
        return
    df = pd.DataFrame(offers)
    columns = ["title", "company", "locationCity", "categoryLabel", "score"]
    st.write(f"**{len(offers)} offre(s) retournée(s)**")
    st.dataframe(df[[c for c in columns if c in df.columns]], hide_index=True)
    with st.expander("Lire les descriptions"):
        for offer in offers:
            st.write(f'**{offer.get("title") or "Sans titre"}**')
            st.text(offer.get("description") or "Description non renseignée.")


def show_wordcloud(offers):
    text = " ".join(
        str(offer.get(field) or "")
        for offer in offers for field in ("title", "description")
    )
    if not text.strip():
        st.info("Aucun texte disponible pour le nuage de mots.")
        return
    try:
        french_stopwords = set(stopwords.words("french"))
    except LookupError:
        st.warning("Installe les mots vides : python -m nltk.downloader stopwords")
        return
    try:
        cloud = WordCloud(
            width=1200, height=500, background_color="white",
            stopwords=french_stopwords, collocations=False,
            min_word_length=3, random_state=42
        ).generate(text)
    except ValueError:
        st.info("Pas assez de mots exploitables pour créer le nuage.")
        return
    st.image(cloud.to_array())
    st.caption("Mots fréquents dans les titres et descriptions des offres retournées ; ce nuage n’explique pas le score de similarité.")


with st.sidebar:
    st.header("Connexion à l’API")
    st.code(API_URL)
    if not all(AUTH):
        st.warning("Renseigne API_USERNAME et API_PASSWORD dans le fichier .env ou le terminal.")
    if st.button("Tester l’accueil"):
        st.session_state["health"] = call_api("GET", "/")
    if "health" in st.session_state:
        show_response(st.session_state["health"])
    if st.button("Tester une mauvaise authentification"):
        # Suffixe ajouté au mot de passe : nécessairement différent de celui configuré.
        st.session_state["bad_auth"] = call_api(
            "GET", "/stats", auth=(AUTH[0], AUTH[1] + "_incorrect")
        )
    if "bad_auth" in st.session_state:
        st.caption("Avec cette API, le code attendu est 422.")
        show_response(st.session_state["bad_auth"])

explore_tab, recommend_tab, stats_tab = st.tabs([
    "Explorer les offres", "Recommandations", "Statistiques"
])

def select_filter(selected, other):
    # Un seul filtre actif : l'API propose un endpoint par type de recherche.
    if st.session_state[selected]:
        st.session_state[other] = False
    st.session_state.pop("explore_result", None)


with explore_tab:
    if "explore_by_city" not in st.session_state:
        st.session_state["explore_by_city"] = True
    # Hors du formulaire pour afficher le bon champ dès le clic.
    by_city = st.checkbox(
        "Ville", key="explore_by_city",
        on_change=select_filter, args=("explore_by_city", "explore_by_category")
    )
    by_category = st.checkbox(
        "Grand domaine", key="explore_by_category",
        on_change=select_filter, args=("explore_by_category", "explore_by_city")
    )

    if by_city or by_category:
        with st.form("explore"):
            if by_city:
                city = st.text_input("Ville", value="Montpellier")
            if by_category:
                category = st.selectbox(
                    "Grand domaine", list(CATEGORIES),
                    format_func=lambda code: f"{code} — {CATEGORIES[code]}"
                )
            limit = st.number_input("Nombre maximal d’offres", 1, 100, 10)
            submitted = st.form_submit_button("Rechercher")

        if submitted:
            if by_city and not city.strip():
                st.session_state.pop("explore_result", None)
                st.warning("Saisis une ville.")
            else:
                endpoint = "/offers/city" if by_city else "/offers/category"
                payload = {"city": city.strip()} if by_city else {"category": category}
                payload["limit"] = int(limit)
                with st.spinner("Recherche des offres…"):
                    st.session_state["explore_result"] = call_api("POST", endpoint, payload)
    else:
        st.info("Coche Ville ou Grand domaine pour effectuer une recherche.")

    if "explore_result" in st.session_state:
        result = st.session_state["explore_result"]
        show_response(result)
        if result["ok"]:
            show_offers(result["data"].get("offers", []))

with recommend_tab:
    with st.form("recommend"):
        keywords = st.text_input("Mots-clés", value="data engineer python sql")
        city = st.text_input("Ville (facultatif)")
        department = st.text_input("Département (facultatif)", value="34")
        category = st.selectbox(
            "Domaine (facultatif)", [""] + list(CATEGORIES),
            format_func=lambda code: f"{code} — {CATEGORIES[code]}" if code else "Tous les domaines"
        )
        top_n = st.number_input("Nombre de recommandations", 1, 100, 10)
        submitted = st.form_submit_button("Obtenir des recommandations")
    if submitted:
        if not keywords.strip():
            st.session_state.pop("recommend_result", None)
            st.warning("Saisis au moins un mot-clé.")
        else:
            payload = {
                "keywords": keywords.strip(), "city": city.strip() or None,
                "department": department.strip() or None,
                "category": category or None, "top_n": int(top_n)
            }
            with st.spinner("Calcul des recommandations…"):
                st.session_state["recommend_result"] = call_api("POST", "/recommendations", payload)
    if "recommend_result" in st.session_state:
        result = st.session_state["recommend_result"]
        show_response(result)
        if result["ok"]:
            offers = result["data"].get("recommendations", [])
            show_offers(offers)
            if offers:
                st.subheader("Nuage de mots de cette recherche")
                show_wordcloud(offers)

with stats_tab:
    st.write("Statistiques sur l’ensemble de la collection, indépendamment des recherches.")
    if st.button("Charger / actualiser les statistiques"):
        with st.spinner("Calcul des statistiques…"):
            st.session_state["stats_result"] = call_api("GET", "/stats")
    if "stats_result" in st.session_state:
        result = st.session_state["stats_result"]
        show_response(result)
        if result["ok"]:
            data = result["data"]
            st.metric("Nombre total d’offres", data["total_offers"])
            if data["total_offers"] == 0:
                st.info("La base ne contient aucune offre.")
            for key, title in [
                ("categories", "Grands domaines"),
                ("companies", "Entreprises : 10 groupes les plus représentés"),
                ("cities", "Villes : 10 groupes les plus représentés"),
                ("sources", "Sources")
            ]:
                if data[key]:
                    st.subheader(title)
                    df = pd.DataFrame(data[key]).rename(columns={"name": "Nom", "count": "Offres"})
                    st.bar_chart(df, x="Nom", y="Offres", horizontal=True, sort="-Offres")
                    with st.expander("Voir les chiffres : " + title):
                        st.dataframe(df, hide_index=True)
            st.caption("Noms regroupés en minuscules. Les valeurs absentes ou vides sont comptées dans « Non renseigné ». Les agences de recrutement peuvent figurer parmi les entreprises.")
    else:
        st.info("Clique sur le bouton pour charger les statistiques.")
