import pandas as pd


def evaluate_performance(df: pd.DataFrame) -> dict:
    # Cette fonction donne une lecture rapide des données OpenRocket.

    df = df.copy()

    needed = [
        "Marge statique (calibres)",
        "Vitesse totale (m/s)",
    ]

    df = df.dropna(subset=needed)

    ms_ok = df["Marge statique (calibres)"].between(2, 6).mean()

    df_launch = df[df["Temps (s)"] <= 0.5] if "Temps (s)" in df.columns else df
    vitesse_ok = (df_launch["Vitesse totale (m/s)"] > 20).mean() if not df_launch.empty else 0.0

    result = {
        "ratio_ms_ok": float(ms_ok),
        "ratio_vitesse_ok": float(vitesse_ok),
        "ms_min": float(df["Marge statique (calibres)"].min()) if not df.empty else None,
        "ms_max": float(df["Marge statique (calibres)"].max()) if not df.empty else None,
        "global_verdict": verdict(ms_ok, vitesse_ok),
        "note": "Cnα n'est pas évalué ici : il doit être calculé par Barrowman avec la géométrie.",
    }

    if "Coefficient de force normale (​)" in df.columns:
        cn_series = pd.to_numeric(df["Coefficient de force normale (​)"], errors="coerce").dropna()
        if not cn_series.empty:
            result["cn_openrocket_min"] = float(cn_series.min())
            result["cn_openrocket_max"] = float(cn_series.max())

    return result


def verdict(ms_ok, vitesse_ok):
    # Cette fonction donne un verdict partiel basé uniquement sur les grandeurs fiables ici.
    if ms_ok > 0.7 and vitesse_ok > 0.7:
        return "Marge statique et vitesse globalement correctes"
    return "Marge statique ou vitesse non conforme sur certaines phases"