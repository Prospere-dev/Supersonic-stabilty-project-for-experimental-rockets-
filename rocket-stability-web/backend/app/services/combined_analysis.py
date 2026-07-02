import pandas as pd

from app.services.stability_analysis import compute_stability
from app.services.mach_analysis import analyze_mach_regime


def analyze_stability_vs_mach(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # On commence par calculer la stabilité
    df = compute_stability(df)

    # Puis on ajoute le régime Mach
    df = analyze_mach_regime(df)

    return df


def summarize_stability_vs_mach(df: pd.DataFrame) -> dict:
    summary = {}

    regimes = ["Subsonique", "Transsonique", "Supersonique"]
    states = ["Instable", "Sous-stable", "Stable", "Surstable"]

    for regime in regimes:
        df_regime = df[df["Régime Mach"] == regime]

        summary[regime] = {
            "count_total": int(len(df_regime)),
            "count_instable": int((df_regime["État de stabilité"] == "Instable").sum()),
            "count_sous_stable": int((df_regime["État de stabilité"] == "Sous-stable").sum()),
            "count_stable": int((df_regime["État de stabilité"] == "Stable").sum()),
            "count_surstable": int((df_regime["État de stabilité"] == "Surstable").sum()),
        }

    return summary