import pandas as pd


def build_flight_summary(df: pd.DataFrame) -> dict:
    df = df.copy()

    summary = {}

    if "Temps (s)" in df.columns and not df["Temps (s)"].dropna().empty:
        summary["time_start_s"] = float(df["Temps (s)"].dropna().iloc[0])
        summary["time_end_s"] = float(df["Temps (s)"].dropna().iloc[-1])

    if "Altitude (m)" in df.columns and not df["Altitude (m)"].dropna().empty:
        summary["altitude_min_m"] = float(df["Altitude (m)"].min())
        summary["altitude_max_m"] = float(df["Altitude (m)"].max())

    if "Vitesse totale (m/s)" in df.columns and not df["Vitesse totale (m/s)"].dropna().empty:
        summary["speed_min_m_s"] = float(df["Vitesse totale (m/s)"].min())
        summary["speed_max_m_s"] = float(df["Vitesse totale (m/s)"].max())

    if "Mach number (​)" in df.columns and not df["Mach number (​)"].dropna().empty:
        mach_series = df["Mach number (​)"].dropna()
        summary["mach_min"] = float(mach_series.min())
        summary["mach_max"] = float(mach_series.max())

        mach_max = float(mach_series.max())
        if mach_max < 0.8:
            summary["max_regime_reached"] = "Subsonique"
        elif mach_max <= 1.2:
            summary["max_regime_reached"] = "Transsonique"
        else:
            summary["max_regime_reached"] = "Supersonique"

    if "Masse (g)" in df.columns and not df["Masse (g)"].dropna().empty:
        mass_series = df["Masse (g)"].dropna()
        summary["mass_start_g"] = float(mass_series.iloc[0])
        summary["mass_end_g"] = float(mass_series.iloc[-1])
        summary["mass_loss_g"] = float(mass_series.iloc[0] - mass_series.iloc[-1])

    if "Température de l'air (°C)" in df.columns and not df["Température de l'air (°C)"].dropna().empty:
        temp_series = df["Température de l'air (°C)"].dropna()
        summary["temperature_min_c"] = float(temp_series.min())
        summary["temperature_max_c"] = float(temp_series.max())

    if "Pression atmosphérique (mbar)" in df.columns and not df["Pression atmosphérique (mbar)"].dropna().empty:
        pressure_series = df["Pression atmosphérique (mbar)"].dropna()
        summary["pressure_min_mbar"] = float(pressure_series.min())
        summary["pressure_max_mbar"] = float(pressure_series.max())

    if "Air density (g/cm³)" in df.columns and not df["Air density (g/cm³)"].dropna().empty:
        density_series = df["Air density (g/cm³)"].dropna()
        summary["air_density_min_g_cm3"] = float(density_series.min())
        summary["air_density_max_g_cm3"] = float(density_series.max())

    if "Emplacement du CP (cm)" in df.columns:
        cp_series = df["Emplacement du CP (cm)"].dropna()
        cp_series = cp_series[cp_series > 0]
        if not cp_series.empty:
            summary["cp_start_cm"] = float(cp_series.iloc[0])
            summary["cp_end_cm"] = float(cp_series.iloc[-1])

    if "Emplacement du CG (cm)" in df.columns:
        cg_series = df["Emplacement du CG (cm)"].dropna()
        cg_series = cg_series[cg_series > 0]
        if not cg_series.empty:
            summary["cg_start_cm"] = float(cg_series.iloc[0])
            summary["cg_end_cm"] = float(cg_series.iloc[-1])

    if "Marge statique (calibres)" in df.columns and not df["Marge statique (calibres)"].dropna().empty:
        ms_series = df["Marge statique (calibres)"].dropna()
        ms_series = ms_series[ms_series > 0]
        if not ms_series.empty:
            summary["static_margin_min_cal"] = float(ms_series.min())
            summary["static_margin_max_cal"] = float(ms_series.max())

    return summary