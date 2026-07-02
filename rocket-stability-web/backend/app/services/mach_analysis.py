import pandas as pd


def analyze_mach_regime(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # On garde uniquement les lignes où Mach existe
    df_valid = df.dropna(subset=["Mach number (​)"]).copy()

    # Classification des régimes
    def classify_mach(mach):
        if mach < 0.8:
            return "Subsonique"
        elif 0.8 <= mach <= 1.2:
            return "Transsonique"
        else:
            return "Supersonique"

    df_valid["Régime Mach"] = df_valid["Mach number (​)"].apply(classify_mach)

    return df_valid


def summarize_mach(df: pd.DataFrame) -> dict:
    return {
        "Mach_min": float(df["Mach number (​)"].min()),
        "Mach_max": float(df["Mach number (​)"].max()),
        "count_subsonique": int((df["Régime Mach"] == "Subsonique").sum()),
        "count_transsonique": int((df["Régime Mach"] == "Transsonique").sum()),
        "count_supersonique": int((df["Régime Mach"] == "Supersonique").sum()),
    }