import pandas as pd

from app.services.theoretical_stability_analysis import (
    FUSEX_CRITERIA,
    build_theoretical_stability,
    check_interval,
)
from app.services.interpretation_engine import build_scientific_interpretation


def _to_float_or_none(value):
    # Conversion locale pour les valeurs extraites des tableaux pandas.
    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except Exception:
        pass

    try:
        return float(value)
    except Exception:
        return None


def _extract_interval(df: pd.DataFrame, column_name: str, positive_only: bool = False):
    # Renvoie le minimum et le maximum exploitables d'une colonne.
    if column_name not in df.columns:
        return None, None

    series = pd.to_numeric(df[column_name], errors="coerce").dropna()

    if positive_only:
        series = series[series > 0]

    if series.empty:
        return None, None

    return _to_float_or_none(series.min()), _to_float_or_none(series.max())


def _extract_start_end(df: pd.DataFrame, column_name: str, divider: float = 1.0):
    # Récupère la première et la dernière valeur positive d'une colonne de vol.
    if column_name not in df.columns:
        return None, None

    series = pd.to_numeric(df[column_name], errors="coerce").dropna()
    series = series[series > 0]

    if series.empty:
        return None, None

    return _to_float_or_none(series.iloc[0] / divider), _to_float_or_none(series.iloc[-1] / divider)


def _extract_first_significant_speed(df: pd.DataFrame):
    # Approximation utilisée lorsque la longueur de rampe n'est pas fournie par le CSV.
    # On prend le premier point où la fusée a "clairement" on va dire quitté l'état immobile.
    speed_col = "Vitesse totale (m/s)"
    time_col = "Temps (s)"

    if speed_col not in df.columns:
        return None, None

    if time_col not in df.columns:
        speed_series = pd.to_numeric(df[speed_col], errors="coerce").dropna()
        speed_series = speed_series[speed_series >= 0]

        if speed_series.empty:
            return None, None

        return _to_float_or_none(speed_series.iloc[0]), None

    launch_df = df[[time_col, speed_col]].copy()
    launch_df[time_col] = pd.to_numeric(launch_df[time_col], errors="coerce")
    launch_df[speed_col] = pd.to_numeric(launch_df[speed_col], errors="coerce")
    launch_df = launch_df.dropna()
    launch_df = launch_df[launch_df[speed_col] >= 0]
    launch_df = launch_df.sort_values(by=time_col)

    if launch_df.empty:
        return None, None

    significant = launch_df[launch_df[speed_col] > 1.0]
    chosen = significant.iloc[0] if not significant.empty else launch_df.iloc[0]

    return _to_float_or_none(chosen[speed_col]), _to_float_or_none(chosen[time_col])


def _check_minimum(value, expected_min, unit=""):
    # Vérifie un critère de minimum strict, utilisé pour la vitesse en sortie de rampe.
    if value is None:
        return {"value": None, "expected": f"> {expected_min}{unit}", "status": "Indisponible"}

    ok = value > expected_min

    return {
        "value": value,
        "expected": f"> {expected_min}{unit}",
        "status": "Conforme" if ok else "Non conforme",
    }


def build_fusex_compliance_report(
    df: pd.DataFrame,
    rocket_length_m: float | None = None,
    rocket_diameter_m: float | None = None,
    mass_reference_kg: float | None = None,
    mass_reference_type: str | None = None,
    cg_reference_m: float | None = None,
    cg_reference_type: str | None = None,
    motor_type: str | None = None,
    motor_rear_position_m: float | None = None,
    nose_profile: str | None = None,
    nose_height_m: float | None = None,
    nose_diameter_m: float | None = None,
    fin_position_m: float | None = None,
    fin_root_chord_m: float | None = None,
    fin_tip_chord_m: float | None = None,
    fin_sweep_m: float | None = None,
    fin_span_m: float | None = None,
    fin_thickness_m: float | None = None,
    fin_count: float | None = None,
) -> dict:
    # Construit le rapport de conformité.
    # La partie théorique vient des paramètres saisis et de  la base propulseur interne.
    # La partie simulée  vient uniquement du  CSV OpenRocket.
    df = df.copy()

    ms_min_openrocket, ms_max_openrocket = _extract_interval(df, "Marge statique (calibres)", positive_only=True)
    cn_min_openrocket, cn_max_openrocket = _extract_interval(df, "Coefficient de force normale (​)", positive_only=False)
    mach_min, mach_max = _extract_interval(df, "Mach number (​)", positive_only=False)
    altitude_min, altitude_max = _extract_interval(df, "Altitude (m)", positive_only=False)
    speed_min, speed_max = _extract_interval(df, "Vitesse totale (m/s)", positive_only=False)
    cg_start_m, cg_end_m = _extract_start_end(df, "Emplacement du CG (cm)", divider=100.0)
    cp_start_m, cp_end_m = _extract_start_end(df, "Emplacement du CP (cm)", divider=100.0)
    rail_speed, rail_speed_time = _extract_first_significant_speed(df)

    theoretical = build_theoretical_stability(
        rocket_length_m=rocket_length_m,
        rocket_diameter_m=rocket_diameter_m,
        mass_reference_kg=mass_reference_kg,
        mass_reference_type=mass_reference_type,
        cg_reference_m=cg_reference_m,
        cg_reference_type=cg_reference_type,
        motor_type=motor_type,
        motor_rear_position_m=motor_rear_position_m,
        nose_profile=nose_profile,
        nose_height_m=nose_height_m,
        nose_diameter_m=nose_diameter_m,
        fin_position_m=fin_position_m,
        fin_root_chord_m=fin_root_chord_m,
        fin_tip_chord_m=fin_tip_chord_m,
        fin_sweep_m=fin_sweep_m,
        fin_span_m=fin_span_m,
        fin_thickness_m=fin_thickness_m,
        fin_count=fin_count,
    )

    cna_theoretical = theoretical.get("cna_theoretical") if theoretical.get("available") else None

    moment_sim_min = ms_min_openrocket * cna_theoretical if ms_min_openrocket is not None and cna_theoretical is not None else None
    moment_sim_max = ms_max_openrocket * cna_theoretical if ms_max_openrocket is not None and cna_theoretical is not None else None

    simulated = {
        "ms_min_openrocket": ms_min_openrocket,
        "ms_max_openrocket": ms_max_openrocket,
        "cn_min_openrocket": cn_min_openrocket,
        "cn_max_openrocket": cn_max_openrocket,
        "moment_min": moment_sim_min,
        "moment_max": moment_sim_max,
        "rail_speed_m_s": rail_speed,
        "rail_speed_time_s": rail_speed_time,
        "mach_min": mach_min,
        "mach_max": mach_max,
        "altitude_min_m": altitude_min,
        "altitude_max_m": altitude_max,
        "speed_min_m_s": speed_min,
        "speed_max_m_s": speed_max,
        "cg_start_m": cg_start_m,
        "cg_end_m": cg_end_m,
        "cp_start_m": cp_start_m,
        "cp_end_m": cp_end_m,
    }

    simulated_checks = {
        "marge_statique_simulee": check_interval(ms_min_openrocket, ms_max_openrocket, FUSEX_CRITERIA["ms_min"], FUSEX_CRITERIA["ms_max"]),
        "moment_simule": check_interval(moment_sim_min, moment_sim_max, FUSEX_CRITERIA["moment_min"], FUSEX_CRITERIA["moment_max"]),
        "vitesse_sortie_rampe": _check_minimum(rail_speed, FUSEX_CRITERIA["rail_speed_min_m_s"], " m/s"),
    }

    theoretical_checks = theoretical.get("checks", {}) if theoretical.get("available") else {}
    all_checks = {**theoretical_checks, **simulated_checks}

    statuses = [check["status"] for check in all_checks.values() if check.get("status") != "Indisponible"]

    if statuses and all(status == "Conforme" for status in statuses):
        global_verdict = "Conforme FUSEX"
    elif any(status == "Non conforme" for status in statuses):
        global_verdict = "Non conforme FUSEX"
    else:
        global_verdict = "Partiellement déterminé"

    interpretation = build_scientific_interpretation(theoretical, simulated)
    mass_states = theoretical.get("mass_states", {})

    return {
        "criteria_reference": "FUSEX",
        "criteria": FUSEX_CRITERIA,
        "geometry": {
            "rocket_length_m": rocket_length_m,
            "rocket_diameter_m": rocket_diameter_m,
            "mass_reference_kg": mass_reference_kg,
            "mass_reference_type": mass_reference_type,
            "cg_reference_m": cg_reference_m,
            "cg_reference_type": cg_reference_type,
            "motor_type": motor_type,
            "motor_rear_position_m": motor_rear_position_m,
            "motor_label": mass_states.get("motor_label"),
            "center_of_mass_full_m": mass_states.get("cg_full_m"),
            "center_of_mass_empty_m": mass_states.get("cg_empty_m"),
            "nose_profile": nose_profile,
            "nose_height_m": nose_height_m,
            "nose_diameter_m": nose_diameter_m,
            "fin_position_m": fin_position_m,
            "fin_root_chord_m": fin_root_chord_m,
            "fin_tip_chord_m": fin_tip_chord_m,
            "fin_sweep_m": fin_sweep_m,
            "fin_span_m": fin_span_m,
            "fin_thickness_m": fin_thickness_m,
            "fin_count": fin_count,
        },
        "theoretical": theoretical,
        "simulated": simulated,
        "measured": {
            "ms_min_openrocket": ms_min_openrocket,
            "ms_max_openrocket": ms_max_openrocket,
            "cn_min_openrocket": cn_min_openrocket,
            "cn_max_openrocket": cn_max_openrocket,
            "cna_theoretical": cna_theoretical,
            "moment_min": moment_sim_min,
            "moment_max": moment_sim_max,
            "rail_speed_m_s": rail_speed,
            "rail_speed_time_s": rail_speed_time,
            "fineness": theoretical.get("fineness") if theoretical.get("available") else None,
        },
        "checks": all_checks,
        "interpretation": interpretation,
        "global_verdict": global_verdict,
        "diagnosis": interpretation["sections"][-2]["text"] if interpretation.get("sections") else "",
    }