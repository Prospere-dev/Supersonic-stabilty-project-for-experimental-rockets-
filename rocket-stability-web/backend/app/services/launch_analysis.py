import pandas as pd


def analyze_launch_phase(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Phase de lancement (premières secondes)
    df_launch = df[df["Temps (s)"] <= 0.5].copy()

    return df_launch


def summarize_launch(df: pd.DataFrame) -> dict:
    return {
        "count_total": int(len(df)),
        "count_instable": int((df["État de stabilité"] == "Instable").sum()),
        "count_sous_stable": int((df["État de stabilité"] == "Sous-stable").sum()),
        "count_stable": int((df["État de stabilité"] == "Stable").sum()),
        "count_surstable": int((df["État de stabilité"] == "Surstable").sum()),
        "vitesse_max": float(df["Vitesse totale (m/s)"].max())
    }