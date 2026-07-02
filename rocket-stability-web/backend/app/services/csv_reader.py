from pathlib import Path
import io
import pandas as pd


COLONNES_EXACTES = [
    "Temps (s)",
    "Altitude (m)",
    "Vitesse totale (m/s)",
    "Masse (g)",
    "Emplacement du CP (cm)",
    "Emplacement du CG (cm)",
    "Calibres marge de stabilité (​)",
    "Coefficient de force normale (​)",
    "Température de l'air (°C)",
    "Pression atmosphérique (mbar)",
    "Air density (g/cm³)",
    "Mach number (​)",
]


def read_openrocket_csv(csv_path: str | Path) -> pd.DataFrame:
    path = Path(csv_path)

    if not path.exists():
        raise FileNotFoundError(f"Fichier introuvable : {path}")

    # On lit tout le fichier brut pour pouvoir repérer la vraie ligne d'en-tête
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    if not lines:
        raise ValueError("Le fichier est vide")

    header_index = None

    # Dans les exports OpenRocket, la ligne des colonnes peut commencer par #
    # Donc on ne supprime pas tout de suite les lignes commentées
    for i, line in enumerate(lines):
        ligne_propre = line.strip()

        if not ligne_propre:
            continue

        # On enlève juste le # au début pour tester si c'est la ligne des colonnes
        candidate = ligne_propre.lstrip("#").strip()

        # Si on retrouve plusieurs noms de colonnes connus sur la même ligne,
        # alors on considère que c'est la vraie ligne d'en-tête
        matches = sum(col in candidate for col in COLONNES_EXACTES)

        if matches >= 3:
            header_index = i
            break

    if header_index is None:
        raise ValueError("Impossible de trouver la ligne d'en-tête du CSV")

    # On récupère la ligne d'en-tête sans le #
    header_line = lines[header_index].lstrip("#").strip()

    # On choisit le séparateur le plus probable
    separator = ";" if header_line.count(";") >= header_line.count(",") else ","

    # On reconstruit un mini CSV propre :
    # - la vraie ligne d'en-tête
    # - puis seulement les lignes de données
    cleaned_lines = [header_line + "\n"]

    for line in lines[header_index + 1:]:
        ligne_propre = line.strip()

        if not ligne_propre:
            continue

        # On ignore les autres lignes commentées (# Event, etc.)
        if ligne_propre.startswith("#"):
            continue

        cleaned_lines.append(ligne_propre + "\n")

    if len(cleaned_lines) <= 1:
        raise ValueError("Aucune ligne de données exploitable n'a été trouvée")

    # On lit maintenant un contenu propre comme un vrai tableau
    df = pd.read_csv(
        io.StringIO("".join(cleaned_lines)),
        sep=separator,
        skipinitialspace=True,
        engine="python",
    )

    # Petit nettoyage minimal sur les noms de colonnes
    df.columns = [str(col).strip().replace('"', "") for col in df.columns]

    if df.empty:
        raise ValueError("Le CSV est lu mais aucune donnée exploitable")

    return df