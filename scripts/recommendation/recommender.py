import pandas as pd

from nltk.corpus import stopwords
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

import matplotlib.pyplot as plt
from wordcloud import WordCloud


french_stopwords = stopwords.words("french")


def build_tfidf_matrix(df: pd.DataFrame):
    """
    Transforme le texte des offres en matrice TF-IDF.
    """

    vectorizer = TfidfVectorizer(
        lowercase=True,
        strip_accents="unicode",
        stop_words=french_stopwords,
        max_features=5000,
    )

    tfidf_matrix = vectorizer.fit_transform(
        df["text"]
    )

    return vectorizer, tfidf_matrix


def recommend(
    df: pd.DataFrame,
    vectorizer,
    tfidf_matrix,
    keywords: str,
    locationCity: str | None = None,
    locationDepartment: str | None = None,
    category: str | None = None,
    top_n: int = 10,
):
    """
    Recommande les offres les plus proches
    des préférences de l'utilisateur.
    """

    if not keywords.strip():
        raise ValueError(
            "Les mots-clés utilisateur ne peuvent pas être vides."
        )

    # Transformation des préférences utilisateur
    user_vector = vectorizer.transform([keywords])

    # Calcul de la similarité
    similarities = cosine_similarity(
        user_vector,
        tfidf_matrix,
    )[0]

    results = df.copy()

    results["score"] = similarities

    # Filtre sur la ville
    if locationCity is not None:

        results = results[results["locationCity"].str.lower()== locationCity.lower()]


    # Filtre sur le département
    if locationDepartment is not None:

        results = results[results["locationDepartment"]== locationDepartment]


    # Filtre sur le grand domaine
    if category is not None:

        results = results[results["category"]== category]


    # Classement du score le plus élevé au plus faible
    results = results.sort_values(
        by="score",
        ascending=False,
    )

    return results.head(top_n)


def show_wordcloud(df):

    text = " ".join(df["text"].dropna())

    wordcloud = WordCloud(
        width=1200,
        height=600,
        background_color="white",
        stopwords=set(french_stopwords),
        collocations=False,
        min_word_length=3
    ).generate(text)

    plt.imshow(
        wordcloud,
        interpolation="bilinear"
    )

    plt.axis("off")

    plt.savefig(
        "wordcloud.png",
        bbox_inches="tight"
    )