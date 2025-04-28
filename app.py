# Application Streamlit 
import streamlit as st
import pandas as pd
import requests
import folium
from streamlit_folium import st_folium
import matplotlib.pyplot as plt
import folium
from folium.plugins import MarkerCluster
import pandas as pd
import base64
import branca
import urllib.parse  

# --- Récupération du token d'authentification France Travail
def get_token():
    client_id = "PAR_cityfighting_4168d464ef7e276ef2adb567c9bf4ea8c96d81d393b2510b2c15dfd354aa98cd"
    client_secret = "7d029ed409f381d146b2311e2e5e363b90479f3a4a48d3a8435d73dea8244eb6"
    
    credentials = f"{client_id}:{client_secret}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()

    headers = {
        "Authorization": f"Basic {encoded_credentials}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {"grant_type": "client_credentials", "scope": "api_offresdemploiv2 o2dsoffre"}
    
    response = requests.post(
        "https://entreprise.pole-emploi.fr/connexion/oauth2/access_token?realm=/partenaire",
        headers=headers,
        data=data
    )

    if response.status_code == 200:
        return response.json().get("access_token")
    else:
        return None

# Puis on génère ton token une fois pour tout ton Streamlit :
token = get_token()

# Fonction pour charger les villes depuis l'API
@st.cache_data
def load_villes():
    url = "https://geo.api.gouv.fr/communes?fields=nom,population,codesPostaux,centre,departement,region&format=json&geometry=centre"
    response = requests.get(url)
    data = response.json()
    df = pd.DataFrame(data)

    df = df.rename(columns={'nom': 'label'})
    df["code_postal"] = df["codesPostaux"].apply(lambda x: x[0] if isinstance(x, list) and len(x) > 0 else None)
    df["latitude"] = df["centre"].apply(lambda x: x["coordinates"][1] if x else None)
    df["longitude"] = df["centre"].apply(lambda x: x["coordinates"][0] if x else None)
    df["departement_nom"] = df["departement"].apply(lambda x: x["nom"] if x else None)
    df["departement_code"] = df["departement"].apply(lambda x: x["code"] if x else None)
    df["region_nom"] = df["region"].apply(lambda x: x["nom"] if x else None)

    df = df[df["population"] > 20000]
    df = df.sort_values("label")
    return df

# Fonction pour récupérer la météo
def get_weather(city):
    api_key = 'd65d53776c1555b1a0c023355fe4c645'
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric&lang=fr"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return {
            "temp": data["main"]["temp"],
            "desc": data["weather"][0]["description"].capitalize(),
            "icon": data["weather"][0]["icon"],
            "humidity": data["main"]["humidity"],
            "wind": data["wind"]["speed"]
        }
    return None

# Page config
st.set_page_config(page_title="City Fighting", layout="wide")

# Chargement des données
villes_df = load_villes()

# Garder uniquement les villes de France métropolitaine (départements de 01 à 95)
villes_df = villes_df[villes_df["departement_code"].astype(str).isin(
    [f"{i:02}" for i in range(1, 96)]
)]


# Chargement des données enrichies depuis CSV local
@st.cache_data
def load_ville_info():
    df_info = pd.read_csv("ville_info_enrichi_massif_corrige.csv")  # Ton nouveau fichier corrigé
    df_info["insee_code"] = df_info["insee_code"].astype(str).str.zfill(5)  # Bien formater sur 5 caractères
    return df_info


@st.cache_data
def load_loyers_departement():
    df_loyers = pd.read_csv("loyers_par_departement.csv")
    return df_loyers

@st.cache_data
def load_etabs_sup():
    return pd.read_csv("villes_etabs_sup.csv")

@st.cache_data
def load_culture_transport():
    return pd.read_csv("villes_culture_transport_.csv")



etabs_sup_df = load_etabs_sup()
ville_info_df = load_ville_info()
culture_transport_df = load_culture_transport()


# Fusion des deux DataFrames
loyers_df = load_loyers_departement()
loyers_df["departement_code"] = loyers_df["departement_code"].astype(str)
villes_df["departement_code"] = villes_df["departement_code"].astype(str)

villes_df = pd.merge(villes_df, ville_info_df, on="label", how="left")
villes_df = pd.merge(villes_df, loyers_df, on="departement_code", how="left", suffixes=("", "_dept"))
villes_df = pd.merge(villes_df, etabs_sup_df, on="label", how="left")
villes_df = pd.merge(villes_df, culture_transport_df, on="label", how="left")


# Remplacer uniquement pour les départements franciliens si valeur dispo
idf_codes = ["75", "77", "78", "91", "92", "93", "94", "95"]
villes_df.loc[
    (villes_df["departement_code"].isin(idf_codes)) & (villes_df["loyer_m2_dept"].notna()),
    "loyer_m2"
] = villes_df["loyer_m2_dept"]
villes_df["loyer_m2"] = villes_df["loyer_m2"]  # reset
villes_df.loc[villes_df["departement_code"].isin(["75", "77", "78", "91", "92", "93", "94", "95"]), "loyer_m2"] = villes_df["loyer_m2_dept"]

# Sélection villes
st.sidebar.title("🔎 Comparaison de villes")
ville1 = st.sidebar.selectbox("Choisissez la première ville :", villes_df["label"])
ville2 = st.sidebar.selectbox("Choisissez la deuxième ville :", villes_df["label"], index=1)

# Titre
st.title("🏙️ City Fighting - Comparateur de Villes")
st.header("Explorez les villes pour vos études ou stages")

# Onglets selon votre plan
onglet1, onglet2, onglet3, onglet4, onglet5, onglet6 = st.tabs(["Données générales", "Données complémentaires", "Trouver ma ville idéale", "Classement", "Offres d'emploi", "À propos"])

# --- Onglet 1 ---
with onglet1:
    if ville1 == ville2:
        st.warning("Veuillez choisir deux villes différentes.")
    else:
        v1 = villes_df[villes_df["label"] == ville1].iloc[0]
        v2 = villes_df[villes_df["label"] == ville2].iloc[0]

        st.markdown("## 📊 Informations générales")
        col1, col2 = st.columns(2)

        for col, ville, data in zip([col1, col2], [ville1, ville2], [v1, v2]):
            weather = get_weather(ville)
            with col:
                st.markdown(f"""
                <div style='padding: 20px; background-color: #ffffff; border: 1px solid #ccc; border-radius: 15px; box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.05);'>
                    <h3 style='color:#333; margin-bottom: 15px;'>{ville}</h3>
                    <p><strong>👥 Population :</strong> {int(data['population']):,}</p>
                    <p><strong>📮 Code postal :</strong> {data['code_postal']}</p>
                    <p><strong>🏛️ Département :</strong> {data['departement_nom']} ({data['departement_code']})</p>
                    <p><strong>🗺️ Région :</strong> {data['region_nom']}</p>
                </div>
                """, unsafe_allow_html=True)

                # Carte Folium avec popup cliquable
                map_ = folium.Map(location=[data["latitude"], data["longitude"]], zoom_start=11, width='100%', height='100%')
                if weather:
                    popup_html = f"""
                    <div style='font-size:14px;'>
                    <b>{ville}</b><br>
                    🌡️ <b>Température</b> : {weather['temp']}°C<br>
                    🌤️ <b>Conditions</b> : {weather['desc']}<br>
                    💧 <b>Humidité</b> : {weather['humidity']}%<br>
                    💨 <b>Vent</b> : {weather['wind']} m/s
                    </div>
                    """
                    folium.CircleMarker(
                        location=[data["latitude"], data["longitude"]],
                        radius=10,
                        color='crimson',
                        fill=True,
                        fill_color='crimson',
                        fill_opacity=0.8,
                        popup=folium.Popup(popup_html, max_width=300)
                    ).add_to(map_)

                st_folium(map_, use_container_width=True, height=500)

# --- Onglet 2 : Complémentaire ---
with onglet2:
    st.markdown("## 🏠 Données sur le logement")

    col1, col2 = st.columns(2)
    for col, ville in zip([col1, col2], [ville1, ville2]):
        data = villes_df[villes_df["label"] == ville].iloc[0]
        if pd.isna(data.get("loyer_m2")):
            with col:
                st.warning(f"⚠️ Données logement non disponibles pour {ville}.")
        else:
            with col:
                st.markdown(f"""
                <div style='padding: 20px; background-color: #fefefe; border: 1px solid #ddd; border-radius: 10px; box-shadow: 2px 2px 8px rgba(0,0,0,0.03);'>
                    <h4 style='color:#333;'>{ville}</h4>
                    <p><strong>💰 Prix moyen au m² :</strong> {data['loyer_m2']} €/m²<br><small style='color:#888;'>📍 Source : {"départementale" if not pd.isna(data.get('loyer_m2_dept')) and data['departement_code'] in ["75", "77", "78", "91", "92", "93", "94", "95"] else "régionale"}</small></p>
                    <p><strong>🏠 Logements étudiants :</strong> {int(data['logements_etudiants']):,}</p>
                    <p><strong>🏙️ Logements sociaux :</strong> {int(data['logements_sociaux']):,}</p>
                </div>
                """, unsafe_allow_html=True)


    with st.expander("📈 Voir la comparaison du prix au m² entre les villes"):
        if not (pd.isna(villes_df[villes_df["label"] == ville1].iloc[0]["loyer_m2"]) or pd.isna(villes_df[villes_df["label"] == ville2].iloc[0]["loyer_m2"])):
            st.markdown("### 📊 Comparaison du prix au m² entre les villes")

            import matplotlib.pyplot as plt

            villes = [ville1, ville2]
            loyers = [
                villes_df[villes_df["label"] == ville1].iloc[0]["loyer_m2"],
                villes_df[villes_df["label"] == ville2].iloc[0]["loyer_m2"]
            ]

            fig, ax = plt.subplots(figsize=(3, 2))  # ➔ réduit un peu la taille
            colors = ['#5D5FEC', '#13C4A3']

            ax.bar(villes, loyers, color=colors, width=0.4)
            ax.set_ylabel('€/m²', fontsize=9)
            ax.grid(axis='y', linestyle='--', alpha=0.5)
            ax.set_xticks(range(len(villes)))
            ax.set_xticklabels(villes, fontsize=9)

            for i, v in enumerate(loyers):
                ax.text(i, v + 0.2, f"{v:.1f} €", ha='center', va='bottom', fontsize=7)

            plt.tight_layout()
            st.pyplot(fig, use_container_width=True)  # ➔ ajouté ici !
            plt.close(fig)




    with st.expander("📈 Voir la répartition des types de logements (en %) pour chaque ville"):
        import matplotlib.pyplot as plt

        col1, col2 = st.columns(2)

        for i, ville in enumerate([ville1, ville2]):
            data_ville = villes_df[villes_df["label"] == ville].iloc[0]
            
            etudiants = data_ville["logements_etudiants"]
            sociaux = data_ville["logements_sociaux"]

            if pd.isna(etudiants) or pd.isna(sociaux):
                continue
            
            autres = 100000 - (etudiants + sociaux)
            sizes = [etudiants, sociaux, autres] if autres > 0 else [etudiants, sociaux]
            labels = ['Logements étudiants', 'Logements sociaux'] + (['Autres logements'] if autres > 0 else [])
            colors = ['#5D5FEC', '#13C4A3', '#FFD700']

            fig, ax = plt.subplots(figsize=(2.8, 2.8))  # ➔ plus petit
            wedges, texts, autotexts = ax.pie(
                sizes,
                labels=labels,
                autopct='%1.1f%%',
                startangle=90,
                colors=colors,
                textprops={'fontsize': 8}
            )
            ax.set_title(f"Répartition des logements à {ville}", fontsize=10)
            ax.axis('equal')

            if i == 0:
                with col1:
                    st.pyplot(fig, use_container_width=True)  # ➔ ajouté
            else:
                with col2:
                    st.pyplot(fig, use_container_width=True)  # ➔ ajouté

            plt.close(fig)


    # Créer une carte centrée sur la France
    map_center = [46.603354, 1.888334]  # Coordonnées approximatives du centre de la France
    m = folium.Map(location=map_center, zoom_start=6)

    # Ajouter un MarkerCluster pour gérer les marqueurs
    marker_cluster = MarkerCluster().add_to(m)

    # Ajouter les marqueurs pour chaque ville
    for index, row in villes_df.iterrows():
        city = row["label"]
        lat = row["latitude"]
        lon = row["longitude"]
        loyer = row["loyer_m2"]
        
        # Créer une popup avec les informations de la ville
        popup_text = f"<strong>{city}</strong><br>Prix moyen au m²: {loyer} €/m²"
        
        # Ajouter un marqueur à la carte
        folium.Marker(
            location=[lat, lon],
            popup=popup_text,
            icon=folium.Icon(color="blue", icon="info-sign")
        ).add_to(marker_cluster)

    # Afficher la carte dans Streamlit
    with st.expander("🗺️ Carte des loyers", expanded=True):
        st.markdown("### Carte des loyers moyens au m² des villes")
        st.write("Vous pouvez zoomer et explorer les prix des loyers par ville.")
        # Afficher la carte dans Streamlit
        st.components.v1.html(m._repr_html_(), height=500)

    

    st.markdown("## 💼 Données sur l'emploi")

    st.markdown("""
    <style>
    .emploi-box {
        background-color: #f8f9fa;
        border: 1px solid #ccc;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 2px 2px 6px rgba(0,0,0,0.05);
        text-align: center;
    }
    .secteurs {
        margin-top: 10px;
        display: flex;
        justify-content: center;
        gap: 8px;
    }
    .tag {
        background-color: #e1ecf4;
        color: #0366d6;
        padding: 5px 10px;
        border-radius: 15px;
        font-size: 13px;
    }
    </style>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    for col, ville in zip([col1, col2], [ville1, ville2]):
        d = villes_df[villes_df["label"] == ville].iloc[0]
        if pd.isna(d.get("secteurs_dominants")):
            with col:
                st.warning(f"⚠️ Données emploi non disponibles pour {ville}.")
        else:
            secteurs = [sect.strip() for sect in d["secteurs_dominants"].split(",")]
            secteurs_html = ''.join([f"<span class='tag'>{sect}</span>" for sect in secteurs])
            with col:
                st.markdown(f"""
                <div class='emploi-box'>
                    <h4>{ville}</h4>
                    <p><strong>🔍 Secteurs dominants :</strong></p>
                    <div class='secteurs'>{secteurs_html}</div>
                </div>
                """, unsafe_allow_html=True)

    st.markdown("## 🎓 Données sur l’enseignement supérieur")

    col1, col2 = st.columns(2)
    for col, ville in zip([col1, col2], [ville1, ville2]):
        # Récupère toutes les villes commençant par la sélection (ex: Paris → Paris 1er, Paris 5e...)
        matched_rows = etabs_sup_df[etabs_sup_df["label"].str.contains(f"^{ville}( |$)", case=False, na=False)]

        with col:
            if matched_rows.empty or matched_rows["nb_etabs_sup"].isna().all():
                st.warning(f"⚠️ Aucun établissement d'enseignement supérieur recensé à {ville}.")
            else:
                if len(matched_rows) > 1:
                    selected_label = st.selectbox(
                        f"Choisissez un arrondissement de {ville} :",
                        options=matched_rows["label"].unique(),
                        key=f"arr_{ville}"
                    )
                    selected_row = matched_rows[matched_rows["label"] == selected_label].iloc[0]
                else:
                    selected_row = matched_rows.iloc[0]

                st.markdown(f"""
                    <div style='padding: 20px; background-color: #fefefe; border: 1px solid #ddd; border-radius: 10px; box-shadow: 2px 2px 8px rgba(0,0,0,0.03);'>
                        <h4 style='color:#333;'>{selected_row["label"]}</h4>
                        <p><strong>🎓 Nombre d'établissements :</strong> {int(selected_row['nb_etabs_sup'])}</p>
                        <p><strong>🏫 Types :</strong> {selected_row['types_etabs']}</p>
                    </div>
                """, unsafe_allow_html=True)

                if pd.notna(selected_row.get("etabs_noms")):
                    with st.expander("📚 Voir les établissements présents"):
                        st.markdown("".join([f"- {e.strip()}\n" for e in selected_row["etabs_noms"].split(",")]))

    st.markdown("## 🚊 Transport étudiant")
    col1, col2 = st.columns(2)
    for col, ville in zip([col1, col2], [ville1, ville2]):
        data = villes_df[villes_df["label"] == ville].iloc[0]
        with col:
            if pd.notna(data.get("tarif_transport_etudiant")):
                st.markdown(f"""
                    <div style='padding: 20px; background-color: #fff8f0; border: 1px solid #ddd; border-radius: 10px;'>
                        <h5>🎫 Tarif étudiant : <strong>{data["tarif_transport_etudiant"]} € / mois</strong></h5>
                        <p style='color:#888;'>📍 Source : {data["source"]}</p>
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.warning(f"⚠️ Tarif étudiant non disponible pour {ville}.")

    st.markdown("## 🎭 Données sur la culture")

    col1, col2 = st.columns(2)
    for col, ville in zip([col1, col2], [ville1, ville2]):
        data = villes_df[villes_df["label"] == ville].iloc[0]
        with col:
            if pd.isna(data.get("nb_events_culture")) or data["nb_events_culture"] == 0:
                st.warning(f"Aucun événement culturel recensé à {ville}.")
            else:
                st.success(f"🎉 {int(data['nb_events_culture'])} événements culturels recensés à {ville}.")
                if pd.notna(data.get("titres_events_culture")) and data["titres_events_culture"] != "Aucun événement recensé":
                    with st.expander("📚 Voir les événements culturels"):
                        for titre in data["titres_events_culture"].split(","):
                            st.markdown(f"- {titre.strip()}")



# --- Onglet 3 : Trouver ma ville idéale ---
with onglet3:
    st.markdown("## 🎯 Trouver ma ville idéale")

    budget = st.slider("Quel est votre budget logement mensuel maximum (en €) ?", 300, 1200, 700)
    meteo = st.selectbox("Quel type de météo préférez-vous ?", ["Ensoleillée", "Tempérée", "Froide", "Montagne", "Océanique"])
    emploi = st.selectbox("Quel domaine d'emploi visez-vous ?", ["Santé", "Informatique", "Tourisme", "BTP", "Commerce", "Finance", "Enseignement", "Agro"])
    logement_etudiant = st.radio("Préférez-vous une ville avec beaucoup de logements étudiants ?", ["Oui", "Peu importe"])

    # Scoring basé sur les vraies colonnes de villes_df enrichi
    filtered = villes_df.dropna(subset=["loyer_m2", "logements_etudiants", "meteo_type", "secteurs_dominants"])

    def score_ville(row):
        score = 0
        if row["loyer_m2"] <= budget / 25: score += 1
        if meteo in row["meteo_type"]: score += 1
        if emploi.lower() in row["secteurs_dominants"].lower(): score += 1
        if logement_etudiant == "Oui" and row["logements_etudiants"] > 3000: score += 1
        return score

    filtered["score"] = filtered.apply(score_ville, axis=1)
    top = filtered.sort_values("score", ascending=False).head(5)

    st.markdown("### ✨ Villes recommandées :")
    st.markdown("<small style='color:#888;'>📍 Les loyers affichés proviennent de sources départementales (IDF) ou régionales ailleurs.</small>", unsafe_allow_html=True)
    for _, row in top.iterrows():
        st.markdown(f"- 🌆 **{row['label']}** — Score : {int(row['score'])}/5")
    
    st.markdown("""
    <small style="color:#888;">
    📊 Chaque ville peut obtenir jusqu’à 5 points selon ces critères :<br>
    💰 Loyer ≤ budget • ☀️ Météo préférée • 💼 Domaine d’emploi dominant • 🏠 > 3 000 logements étudiants • 🎓 Présence d'établissements supérieurs<br>
    Score final sur 100 = (points / 5) × 100
    </small>
    """, unsafe_allow_html=True)

# --- Onglet 4 : Classement des villes étudiantes ---
with onglet4:
    st.markdown("## 🏆 Classement des villes étudiantes")

    # Exemple de données réelles (à compléter)
    classement_data = {
        "Montpellier": {"rang": 1, "score": 99, "loyer_m2": 13.0},
        "Rennes": {"rang": 2, "score": 94, "loyer_m2": 11.2},
        "Caen": {"rang": 3, "score": 90, "loyer_m2": 9.3},
        "Toulouse": {"rang": 3, "score": 90, "loyer_m2": 12.5},
        "Grenoble": {"rang": 5, "score": 87, "loyer_m2": 11.0},
        "Paris": {"rang": 6, "score": 85, "loyer_m2": 25.7}
    }

    classement_df = pd.DataFrame.from_dict(classement_data, orient='index')
    classement_df = classement_df.reset_index().rename(columns={"index": "Ville", "rang": "Classement", "score": "Score", "loyer_m2": "Prix moyen au m²"})
    classement_df = classement_df.sort_values("Classement")
    st.dataframe(classement_df, use_container_width=True)

    
    st.markdown("""
    <small style="color:#888;">
    📊 Le score est calculé selon plusieurs critères : loyer abordable, secteurs d’emploi dominants, nombre de logements étudiants, et présence d’au moins deux établissements d’enseignement supérieur.  
    Chaque critère rapporte un point, pour un total sur 5, transformé ici en score sur 100.
    </small>
    """, unsafe_allow_html=True)

# --- Onglet Offres d'emploi ---
with onglet5:
    st.markdown("## 💼 Offres d'emploi disponibles")

    keyword = st.text_input("🔎 Entrez un mot-clé pour rechercher des offres (ex : Data, Marketing...)")

    lancer_recherche = st.button("🔄 Rechercher")

    if lancer_recherche:
        if not keyword.strip():
            st.warning("⚠️ Veuillez entrer un mot-clé pour effectuer la recherche.")
        else:
            col1, col2 = st.columns(2)

            for col, ville in zip([col1, col2], [ville1, ville2]):
                data_ville = villes_df[villes_df["label"] == ville]

                with col:
                    st.markdown(f"### 📍 {ville}")

                    if data_ville.empty:
                        st.error(f"Impossible de trouver les informations pour {ville}.")
                        continue

                    try:
                        # Recherche par département, plus fiable
                        departement = data_ville.iloc[0]['departement_code']
                        url = f"https://api.pole-emploi.io/partenaire/offresdemploi/v2/offres/search?departement={departement}&motsCles={keyword}&distance=30"

                        headers = {
                            "Authorization": f"Bearer {token}"
                        }
                        r = requests.get(url, headers=headers)
                        
                        if r.status_code == 200:
                            offres = r.json().get("resultats", [])
                            if offres:
                                for offre in offres:
                                    st.markdown(f"🔹 **{offre['intitule']}**")
                                    st.markdown(f"📍 {offre['lieuTravail']['libelle']}")
                                    st.markdown(f"[Voir l'offre ➔]({offre['origineOffre']['urlOrigine']})")
                                    st.markdown("---")
                            else:
                                st.warning(f"Aucune offre trouvée pour {ville} avec '{keyword}'.")
                                st.markdown(f"👉 [Voir toutes les offres sur France Travail ➔](https://candidat.francetravail.fr/offres/recherche)")
                        else:
                            st.error(f"Erreur {r.status_code} lors de la récupération des offres pour {ville} 🚨")
                            st.markdown(f"👉 [Voir toutes les offres sur France Travail ➔](https://candidat.francetravail.fr/offres/recherche)")

                    except Exception as e:
                        st.error(f"Erreur lors de la récupération des offres pour {ville} 🚨")
                        st.markdown(f"👉 [Voir toutes les offres sur France Travail ➔](https://candidat.francetravail.fr/offres/recherche)")

# --- Onglet 6 : À propos ---
with onglet6:
    st.markdown("""
    ### ℹ️ À propos du projet
    Cette application a été développée dans le cadre de la SAE Outils Décisionnels.

    - Sujet : **"Où étudier ou faire un stage ?"**
    - Objectif : Aider un étudiant à choisir sa ville idéale selon plusieurs critères
    - Données issues de : [data.gouv.fr](https://www.data.gouv.fr/), [geo.api.gouv.fr](https://geo.api.gouv.fr), [OpenWeatherMap](https://openweathermap.org)
    - Projet développé avec **Streamlit**
    - Développé par : 
        - Ekta Mistry : https://www.linkedin.com/in/ekta-mistry-756896268/
        - Angelikia Kavuansiko : https://www.linkedin.com/in/angelikia-kavuansiko/


    🔗 [Lien GitHub](https://github.com/lovecookie93/City-Fighting)
    """)

