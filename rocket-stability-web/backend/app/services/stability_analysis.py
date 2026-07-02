import pandas as pd






def compute_stability(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # On garde uniquement les lignes où les infos utiles existent vraiment (à cause des valeurs manquantes)
    df_valid = df.dropna(subset=[
        "Emplacement du CP (cm)",
        "Emplacement du CG (cm)",
        "Calibres marge de stabilité (​)"
    ]).copy()


    # Marge brute en cm  : qui est utile comme grandeur  intermédiaire
    df_valid["Marge brute (cm)"] = (
        df_valid["Emplacement du CP (cm)"] -
        df_valid["Emplacement du CG (cm)"]
    )

    # La vraie grandeur principale pour la stabilité, c'est la marge statique en calibres
    df_valid["Marge statique (calibres)"] = df_valid["Calibres marge de stabilité (​)"]

    # Classification inspirée des critères fusex
    def classify_static_margin(ms):
        if ms <= 0:
            return "Instable"
        elif ms < 2:
            return "Sous-stable"
        elif ms <= 6:
            return "Stable"
        else:
            return "Surstable"

    df_valid["État de stabilité"] = df_valid["Marge statique (calibres)"].apply(classify_static_margin)

    return df_valid


def summarize_stability(df: pd.DataFrame) -> dict:
    return {
        "ms_min": float(df["Marge statique (calibres)"].min()),
        "ms_max": float(df["Marge statique (calibres)"].max()),
        "marge_brute_min_cm": float(df["Marge brute (cm)"].min()),
        "marge_brute_max_cm": float(df["Marge brute (cm)"].max()),
        "count_instable": int((df["État de stabilité"] == "Instable").sum()),
        "count_sous_stable": int((df["État de stabilité"] == "Sous-stable").sum()),
        "count_stable": int((df["État de stabilité"] == "Stable").sum()),
        "count_surstable": int((df["État de stabilité"] == "Surstable").sum()),
    }