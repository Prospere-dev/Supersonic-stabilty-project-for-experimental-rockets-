import pandas as pd

from app.services.combined_analysis import analyze_stability_vs_mach


def _finite_float(value):
    # Convertit une valeur pandas en float JSON propre.
    try:
        number = float(value)
    except Exception:
        return None

    if pd.isna(number):
        return None

    return number


def _sample_dataframe(df: pd.DataFrame, max_points: int = 900) -> pd.DataFrame:
    # Limite le nombre de points envoyés au navigateur.
    # Les graphes restent lisibles et l'interface ne bloque pas sur les gros CSV.
    if len(df) <= max_points:
        return df

    step = max(1, len(df) // max_points)
    return df.iloc[::step].copy()


def build_plot_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    # Prépare le tableau commun utilisé par les graphes du frontend.
    df_plot = analyze_stability_vs_mach(df).copy()

    columns_to_keep = [
        "Temps (s)",
        "Altitude (m)",
        "Vitesse totale (m/s)",
        "Mach number (\u200b)",
        "Emplacement du CP (cm)",
        "Emplacement du CG (cm)",
        "Marge statique (calibres)",
        "Marge brute (cm)",
        "Coefficient de force normale (\u200b)",
        "Distance latérale (m)",
        "Position à l'est du lancement (m)",
        "Position au nord du lancement (m)",
        "État de stabilité",
        "Régime Mach",
    ]

    existing_columns = [column for column in columns_to_keep if column in df_plot.columns]
    df_plot = df_plot[existing_columns].copy()

    numeric_columns = [
        "Temps (s)",
        "Altitude (m)",
        "Vitesse totale (m/s)",
        "Mach number (\u200b)",
        "Emplacement du CP (cm)",
        "Emplacement du CG (cm)",
        "Marge statique (calibres)",
        "Marge brute (cm)",
        "Coefficient de force normale (\u200b)",
        "Distance latérale (m)",
        "Position à l'est du lancement (m)",
        "Position au nord du lancement (m)",
    ]

    for column in numeric_columns:
        if column in df_plot.columns:
            df_plot[column] = pd.to_numeric(df_plot[column], errors="coerce")

    return df_plot


def build_cp_cg_vs_time(df: pd.DataFrame) -> list[dict]:
    # Prépare l'évolution du CP et du CG issue du CSV OpenRocket.
    needed = ["Temps (s)", "Emplacement du CP (cm)", "Emplacement du CG (cm)"]

    if not all(column in df.columns for column in needed):
        return []

    df_graph = df.dropna(subset=needed).copy()
    df_graph = df_graph[
        (df_graph["Emplacement du CP (cm)"] > 0)
        & (df_graph["Emplacement du CG (cm)"] > 0)
    ].copy()
    df_graph = _sample_dataframe(df_graph)

    points = []
    for _, row in df_graph.iterrows():
        time = _finite_float(row["Temps (s)"])
        cp = _finite_float(row["Emplacement du CP (cm)"])
        cg = _finite_float(row["Emplacement du CG (cm)"])
        if time is not None and cp is not None and cg is not None:
            points.append({"time": time, "cp": cp, "cg": cg})

    return points


def build_static_margin_vs_time(df: pd.DataFrame) -> list[dict]:
    # Prépare la marge statique simulée en fonction du temps.
    needed = ["Temps (s)", "Marge statique (calibres)"]

    if not all(column in df.columns for column in needed):
        return []

    df_graph = df.dropna(subset=needed).copy()
    df_graph = df_graph[df_graph["Marge statique (calibres)"] > 0].copy()
    df_graph = _sample_dataframe(df_graph)

    points = []
    for _, row in df_graph.iterrows():
        time = _finite_float(row["Temps (s)"])
        static_margin = _finite_float(row["Marge statique (calibres)"])
        if time is not None and static_margin is not None:
            points.append(
                {
                    "time": time,
                    "static_margin": static_margin,
                    "state": row["État de stabilité"] if "État de stabilité" in df_graph.columns else "Indéterminé",
                }
            )

    return points


def build_static_margin_vs_mach(df: pd.DataFrame) -> list[dict]:
    # Prépare la marge statique simulée selon le nombre de Mach.
    needed = ["Mach number (\u200b)", "Marge statique (calibres)"]

    if not all(column in df.columns for column in needed):
        return []

    df_graph = df.dropna(subset=needed).copy()
    df_graph = df_graph[
        (df_graph["Mach number (\u200b)"] >= 0)
        & (df_graph["Marge statique (calibres)"] > 0)
    ].copy()
    df_graph = _sample_dataframe(df_graph)

    points = []
    for _, row in df_graph.iterrows():
        mach = _finite_float(row["Mach number (\u200b)"])
        static_margin = _finite_float(row["Marge statique (calibres)"])
        if mach is not None and static_margin is not None:
            points.append(
                {
                    "mach": mach,
                    "static_margin": static_margin,
                    "state": row["État de stabilité"] if "État de stabilité" in df_graph.columns else "Indéterminé",
                    "regime": row["Régime Mach"] if "Régime Mach" in df_graph.columns else "Indéterminé",
                }
            )

    return points


def build_cn_vs_time(df: pd.DataFrame) -> list[dict]:
    # Prépare le coefficient de force normale Cn provenant du CSV OpenRocket.
    # Ce n'est pas Cnα : le gradient Cnα est calculé séparément avec la géométrie.
    needed = ["Temps (s)", "Coefficient de force normale (\u200b)"]

    if not all(column in df.columns for column in needed):
        return []

    df_graph = df.dropna(subset=needed).copy()
    df_graph = _sample_dataframe(df_graph)

    points = []
    for _, row in df_graph.iterrows():
        time = _finite_float(row["Temps (s)"])
        cn = _finite_float(row["Coefficient de force normale (\u200b)"])
        if time is not None and cn is not None:
            points.append({"time": time, "cn": cn})

    return points


def build_cna_vs_time(df: pd.DataFrame) -> list[dict]:
    # Le CSV OpenRocket exporte Cn, pas Cnα.
    # On laisse donc cette courbe vide pour éviter de mélanger deux grandeurs différentes.
    return []


def build_ms_times_cna_vs_time(df: pd.DataFrame) -> list[dict]:
    # Le produit MS × Cnα demande le Cnα théorique de la géométrie.
    # Il est traité dans le rapport de conformité, pas directement depuis le CSV brut.
    return []


def build_stability_criteria_diagram(df: pd.DataFrame) -> list[dict]:
    # Diagramme simulé MS / Cn. Il sert à visualiser la simulation sans renommer Cn en Cnα.
    needed = ["Temps (s)", "Marge statique (calibres)", "Coefficient de force normale (\u200b)"]

    if not all(column in df.columns for column in needed):
        return []

    df_graph = df.dropna(subset=needed).copy()
    df_graph = df_graph[df_graph["Marge statique (calibres)"] > 0].copy()
    df_graph = _sample_dataframe(df_graph)

    points = []
    for _, row in df_graph.iterrows():
        time = _finite_float(row["Temps (s)"])
        ms = _finite_float(row["Marge statique (calibres)"])
        cn = _finite_float(row["Coefficient de force normale (\u200b)"])
        if time is not None and ms is not None and cn is not None:
            points.append(
                {
                    "time": time,
                    "ms": ms,
                    "cn": cn,
                    "state": row["État de stabilité"] if "État de stabilité" in df_graph.columns else "Indéterminé",
                    "regime": row["Régime Mach"] if "Régime Mach" in df_graph.columns else "Indéterminé",
                }
            )

    return points


def build_speed_vs_time(df: pd.DataFrame) -> list[dict]:
    # Prépare la vitesse totale en fonction du temps.
    needed = ["Temps (s)", "Vitesse totale (m/s)"]

    if not all(column in df.columns for column in needed):
        return []

    df_graph = df.dropna(subset=needed).copy()
    df_graph = df_graph[df_graph["Vitesse totale (m/s)"] >= 0].copy()
    df_graph = _sample_dataframe(df_graph)

    points = []
    for _, row in df_graph.iterrows():
        time = _finite_float(row["Temps (s)"])
        speed = _finite_float(row["Vitesse totale (m/s)"])
        if time is not None and speed is not None:
            points.append({"time": time, "speed": speed})

    return points


def build_altitude_vs_time(df: pd.DataFrame) -> list[dict]:
    # Prépare l'altitude en fonction du temps.
    needed = ["Temps (s)", "Altitude (m)"]

    if not all(column in df.columns for column in needed):
        return []

    df_graph = df.dropna(subset=needed).copy()
    df_graph = _sample_dataframe(df_graph)

    points = []
    for _, row in df_graph.iterrows():
        time = _finite_float(row["Temps (s)"])
        altitude = _finite_float(row["Altitude (m)"])
        if time is not None and altitude is not None:
            points.append({"time": time, "altitude": altitude})

    return points


def build_altitude_vs_range(df: pd.DataFrame) -> list[dict]:
    # Prépare une vue altitude / distance latérale quand OpenRocket fournit les positions horizontales.
    altitude_col = "Altitude (m)"
    east_col = "Position à l'est du lancement (m)"
    north_col = "Position au nord du lancement (m)"
    lateral_col = "Distance latérale (m)"

    if altitude_col not in df.columns:
        return []

    df_graph = df.copy()

    if lateral_col in df_graph.columns:
        df_graph["range_m"] = pd.to_numeric(df_graph[lateral_col], errors="coerce")
    elif east_col in df_graph.columns and north_col in df_graph.columns:
        east = pd.to_numeric(df_graph[east_col], errors="coerce")
        north = pd.to_numeric(df_graph[north_col], errors="coerce")
        df_graph["range_m"] = (east**2 + north**2) ** 0.5
    else:
        return []

    df_graph[altitude_col] = pd.to_numeric(df_graph[altitude_col], errors="coerce")
    df_graph = df_graph.dropna(subset=["range_m", altitude_col]).copy()
    df_graph = _sample_dataframe(df_graph)

    points = []
    for _, row in df_graph.iterrows():
        range_m = _finite_float(row["range_m"])
        altitude = _finite_float(row[altitude_col])
        if range_m is not None and altitude is not None:
            points.append({"range": range_m, "altitude": altitude})

    return points