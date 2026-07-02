import pandas as pd


# Ici on relie chaque colonne utile à ses deux noms exacts possibles.
# On ne devine rien. On ne prend que les noms vus dans les deux CSV.
COLONNES_EQUIVALENTES = {
    "Temps (s)": [
        "Temps (s)",
        "Time (s)",
    ],
    "Altitude (m)": [
        "Altitude (m)",
    ],
    "Vitesse totale (m/s)": [
        "Vitesse totale (m/s)",
        "Total velocity (m/s)",
    ],
    "Masse (g)": [
        "Masse (g)",
        "Mass (g)",
    ],
    "Emplacement du CP (cm)": [
        "Emplacement du CP (cm)",
        "CP location (cm)",
    ],
    "Emplacement du CG (cm)": [
        "Emplacement du CG (cm)",
        "CG location (cm)",
    ],
    "Calibres marge de stabilité (​)": [
        "Calibres marge de stabilité (​)",
        "Stability margin calibers (​)",
    ],
    "Coefficient de force normale (​)": [
        "Coefficient de force normale (​)",
        "Normal force coefficient (​)",
    ],
    "Température de l'air (°C)": [
        "Température de l'air (°C)",
        "Air temperature (°C)",
    ],
    "Pression atmosphérique (mbar)": [
        "Pression atmosphérique (mbar)",
        "Air pressure (mbar)",
    ],
    "Densité de l'air (g/cm³)": [
        "Air density (g/cm³)",
        "Air density (g/cm³)",
    ],
    "Mach number (​)": [
        "Mach number (​)",
        "Mach number (​)",
    ],
    "Distance latérale (m)": [
        "Distance latérale (m)",
        "Lateral distance (m)",
    ],
    "Position à l'est du lancement (m)": [
        "Position à l'est du lancement (m)",
        "Position East of launch (m)",
    ],
    "Position au nord du lancement (m)": [
        "Position au nord du lancement (m)",
        "Position North of launch (m)",
    ],
}


def extract_useful_columns(df: pd.DataFrame) -> pd.DataFrame:
    # Cette fonction garde seulement les colonnes utiles.
    # Elle accepte le CSV français et le CSV anglais.
    colonnes_reelles = {}

    for nom_interne, noms_possibles in COLONNES_EQUIVALENTES.items():
        colonne_trouvee = None

        for nom_exact in noms_possibles:
            if nom_exact in df.columns:
                colonne_trouvee = nom_exact
                break

        if colonne_trouvee is not None:
            colonnes_reelles[nom_interne] = colonne_trouvee

    colonnes_a_garder = list(colonnes_reelles.values())

    if not colonnes_a_garder:
        raise ValueError("Aucune colonne utile attendue n'a été trouvée dans le CSV.")

    df_filtre = df[colonnes_a_garder].copy()

    # Ici on renomme vers les noms internes qu'on garde partout.
    df_filtre = df_filtre.rename(
        columns={nom_reel: nom_interne for nom_interne, nom_reel in colonnes_reelles.items()}
    )

    return df_filtre