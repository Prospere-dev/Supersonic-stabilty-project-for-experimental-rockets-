import numpy as np
import pandas as pd


def normalize_openrocket_data(df: pd.DataFrame) -> pd.DataFrame:
    df_clean = df.copy()

    # On essaie de transformer les colonnes en vrai format numérique
    # C'est ce tableau propre qu'on manipulera ensuite dans le projet
    for col in df_clean.columns:
        values = df_clean[col].astype(str).str.strip().str.replace(",", ".", regex=False)
        df_clean[col] = pd.to_numeric(values, errors="coerce")

    # On neutralise les valeurs infinies qui peuvent apparaître
    df_clean = df_clean.replace([np.inf, -np.inf], np.nan)

    return df_clean