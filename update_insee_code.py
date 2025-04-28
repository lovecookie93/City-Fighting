import pandas as pd
import requests
import time

# Charger ton CSV
df = pd.read_csv('ville_info_enrichi_massif.csv')

# Fonction pour récupérer le code INSEE depuis l'API
def get_insee_code(city_name):
    try:
        url = f"https://geo.api.gouv.fr/communes?nom={city_name}&fields=nom,code,codesPostaux&boost=population&limit=1"
        response = requests.get(url)
        if response.status_code == 200:
            results = response.json()
            if results:
                return results[0]['code']
    except Exception as e:
        print(f"Erreur pour {city_name}: {e}")
    return None

# Remplir la colonne insee_code
new_insee_codes = []
for ville in df['label']:
    code = get_insee_code(ville)
    new_insee_codes.append(code)
    time.sleep(0.5)  # Pause pour respecter l'API

# Mettre à jour la colonne
df['insee_code'] = new_insee_codes

# Sauvegarder le fichier corrigé
df.to_csv('ville_info_enrichi_massif_corrige.csv', index=False)

print("✅ Fichier corrigé généré : ville_info_enrichi_massif_corrige.csv")
