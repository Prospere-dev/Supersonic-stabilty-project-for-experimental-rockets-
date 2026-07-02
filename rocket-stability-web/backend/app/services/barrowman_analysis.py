import math
from typing import Any


def to_float_or_none(value: Any) -> float | None:
    # Transforme une valeur quelconque en nombre exploitable.
    # Si la valeur est vide, invalide ou infinie, on renvoie None.
    if value is None:
        return None

    text = str(value).strip().replace(",", ".")

    if text == "":
        return None

    try:
        number = float(text)
    except ValueError:
        return None

    if not math.isfinite(number):
        return None

    return number


def is_positive(value: float | None) -> bool:
    # Vérifie qu'une grandeur géométrique est strictement positive.
    return value is not None and value > 0


def compute_reference_area(diameter_m: float) -> float:
    # Surface de référence de la fusée.
    # Le PDF indique qu'on prend généralement la section de la base de l'ogive.
    return math.pi * diameter_m**2 / 4.0


def compute_nose_cna(nose_diameter_m: float, reference_diameter_m: float) -> float:
    # Gradient de portance de l'ogive selon Barrowman.
    # Pour une fusée sans changement de diamètre :
    # Cnα_ogive = 2
    # Si le diamètre d'ogive diffère du diamètre de référence, on corrige par le rapport des surfaces.
    return 2.0 * (nose_diameter_m / reference_diameter_m) ** 2


def compute_nose_cp(nose_height_m: float, nose_profile: str | None) -> float:
    # Position du CPA de l'ogive depuis la pointe.
    # Les profils classiques n'ont pas exactement le même foyer aérodynamique.
    profile = (nose_profile or "").strip().lower()

    if profile == "conique":
        return (2.0 / 3.0) * nose_height_m

    if profile == "parabolique":
        return 0.50 * nose_height_m

    if profile == "elliptique":
        return 0.50 * nose_height_m

    # Approximation classique pour une ogive tangentielle / ogivale.
    return 0.466 * nose_height_m


def compute_fin_mid_chord_length(
    root_chord_m: float,
    tip_chord_m: float,
    sweep_m: float,
    span_m: float,
) -> float:
    # Longueur de la ligne mi-corde des ailerons.
    # Cette grandeur intervient dans la formule Barrowman des ailerons trapézoïdaux.
    mid_chord_offset_m = sweep_m + (tip_chord_m - root_chord_m) / 2.0

    return math.sqrt(mid_chord_offset_m**2 + span_m**2)


def compute_fin_body_interference_factor(
    rocket_diameter_m: float,
    span_m: float,
    fin_count: float,
) -> float:
    # Facteur d'interaction corps/ailerons.
    # Le PDF indique qu'un facteur correctif est utilisé pour les ailerons en présence du tube.
    # Pour 3 ou 4 ailerons : 1 + d / (2E + d)
    # Pour 6 ailerons : le quotient correctif est réduit de moitié.
    base_ratio = rocket_diameter_m / (2.0 * span_m + rocket_diameter_m)

    if round(fin_count) == 6:
        return 1.0 + 0.5 * base_ratio

    if round(fin_count) in (3, 4):
        return 1.0 + base_ratio

    # Pour les autres nombres d'ailerons, on reste prudent.
    # On applique le facteur standard, mais le rapport signale que l'hypothèse est moins sûre.
    return 1.0 + base_ratio


def compute_fins_cna(
    rocket_diameter_m: float,
    fin_count: float,
    root_chord_m: float,
    tip_chord_m: float,
    sweep_m: float,
    span_m: float,
) -> float:
    # Cnα des ailerons trapézoïdaux selon Barrowman.
    # Cette formule remplace l'ancienne approximation surface / aspect ratio.
    #
    # m = corde à l'emplanture
    # n = corde au saumon
    # p = flèche
    # E = envergure
    # d = diamètre de référence
    # N = nombre d'ailerons

    mid_chord_length_m = compute_fin_mid_chord_length(
        root_chord_m=root_chord_m,
        tip_chord_m=tip_chord_m,
        sweep_m=sweep_m,
        span_m=span_m,
    )

    denominator = 1.0 + math.sqrt(
        1.0 + (2.0 * mid_chord_length_m / (root_chord_m + tip_chord_m)) ** 2
    )

    interference = compute_fin_body_interference_factor(
        rocket_diameter_m=rocket_diameter_m,
        span_m=span_m,
        fin_count=fin_count,
    )

    cna = (
        interference
        * (4.0 * fin_count * (span_m / rocket_diameter_m) ** 2)
        / denominator
    )

    return cna


def compute_fins_cp(
    fin_position_m: float,
    root_chord_m: float,
    tip_chord_m: float,
    sweep_m: float,
) -> float:
    # Position du CPA des ailerons trapézoïdaux depuis la pointe de la fusée.
    #
    # Dans notre interface :
    # fin_position_m = position du bas / bord arrière des ailettes.
    # Donc le bord d'attaque à l'emplanture vaut :
    # x_root_leading = fin_position_m - root_chord_m

    x_root_leading_m = fin_position_m - root_chord_m

    first_term = (
        sweep_m * (root_chord_m + 2.0 * tip_chord_m)
        / (3.0 * (root_chord_m + tip_chord_m))
    )

    second_term = (
        (root_chord_m + tip_chord_m)
        - (root_chord_m * tip_chord_m / (root_chord_m + tip_chord_m))
    ) / 6.0

    return x_root_leading_m + first_term + second_term


def compute_total_cp(weighted_components: list[dict]) -> float | None:
    # Calcule le CPA total par barycentre pondéré des Cnα.
    total_cna = sum(component["cna"] for component in weighted_components)

    if total_cna <= 0:
        return None

    return sum(component["cna"] * component["cp_m"] for component in weighted_components) / total_cna


def compute_barrowman_stability(
    rocket_length_m: float | None,
    rocket_diameter_m: float | None,
    center_of_mass_m: float | None,
    nose_profile: str | None,
    nose_height_m: float | None,
    nose_diameter_m: float | None,
    fin_position_m: float | None,
    fin_root_chord_m: float | None,
    fin_tip_chord_m: float | None,
    fin_sweep_m: float | None,
    fin_span_m: float | None,
    fin_thickness_m: float | None,
    fin_count: float | None,
) -> dict:
    # Fonction principale du calcul Barrowman.
    #
    # Objectif :
    # - calculer Cnα ogive ;
    # - calculer CPA ogive ;
    # - calculer Cnα ailerons ;
    # - calculer CPA ailerons ;
    # - sommer les Cnα ;
    # - calculer le CPA total par barycentre ;
    # - calculer MS et MS × Cnα.
    #
    # Les tubes cylindriques sont négligés, conformément à la méthode Barrowman de base
    # rappelée dans le PDF.

    required_fields = {
        "rocket_length_m": rocket_length_m,
        "rocket_diameter_m": rocket_diameter_m,
        "center_of_mass_m": center_of_mass_m,
        "nose_height_m": nose_height_m,
        "nose_diameter_m": nose_diameter_m,
        "fin_position_m": fin_position_m,
        "fin_root_chord_m": fin_root_chord_m,
        "fin_tip_chord_m": fin_tip_chord_m,
        "fin_sweep_m": fin_sweep_m,
        "fin_span_m": fin_span_m,
        "fin_count": fin_count,
    }

    missing_fields = [
        field_name
        for field_name, field_value in required_fields.items()
        if field_value is None
    ]

    if missing_fields:
        return {
            "available": False,
            "message": "Calcul Barrowman indisponible : géométrie incomplète.",
            "missing_fields": missing_fields,
        }

    positive_fields = {
        "rocket_length_m": rocket_length_m,
        "rocket_diameter_m": rocket_diameter_m,
        "nose_height_m": nose_height_m,
        "nose_diameter_m": nose_diameter_m,
        "fin_root_chord_m": fin_root_chord_m,
        "fin_tip_chord_m": fin_tip_chord_m,
        "fin_span_m": fin_span_m,
        "fin_count": fin_count,
    }

    invalid_fields = [
        field_name
        for field_name, field_value in positive_fields.items()
        if not is_positive(field_value)
    ]

    if invalid_fields:
        return {
            "available": False,
            "message": "Calcul Barrowman indisponible : certaines dimensions doivent être strictement positives.",
            "missing_fields": [],
            "invalid_fields": invalid_fields,
        }

    warnings = []

    if fin_thickness_m is not None and fin_thickness_m <= 0:
        warnings.append(
            "Épaisseur ep invalide ou négative : elle n'intervient pas dans le Cnα Barrowman de base, mais doit rester positive pour la cohérence géométrique."
        )

    if round(fin_count) not in (3, 4, 6):
        warnings.append(
            "Nombre d'ailerons différent de 3, 4 ou 6 : le facteur d'interaction corps/ailerons est moins directement couvert par les hypothèses usuelles."
        )

    if nose_diameter_m != rocket_diameter_m:
        warnings.append(
            "Diamètre d'ogive différent du diamètre de référence : le Cnα d'ogive est corrigé par le rapport des surfaces."
        )

    nose_cna = compute_nose_cna(
        nose_diameter_m=nose_diameter_m,
        reference_diameter_m=rocket_diameter_m,
    )

    nose_cp_m = compute_nose_cp(
        nose_height_m=nose_height_m,
        nose_profile=nose_profile,
    )

    fins_cna = compute_fins_cna(
        rocket_diameter_m=rocket_diameter_m,
        fin_count=fin_count,
        root_chord_m=fin_root_chord_m,
        tip_chord_m=fin_tip_chord_m,
        sweep_m=fin_sweep_m,
        span_m=fin_span_m,
    )

    fins_cp_m = compute_fins_cp(
        fin_position_m=fin_position_m,
        root_chord_m=fin_root_chord_m,
        tip_chord_m=fin_tip_chord_m,
        sweep_m=fin_sweep_m,
    )

    components = [
        {
            "name": "Ogive",
            "cna": nose_cna,
            "cp_m": nose_cp_m,
        },
        {
            "name": "Ailerons",
            "cna": fins_cna,
            "cp_m": fins_cp_m,
        },
    ]

    total_cna = nose_cna + fins_cna
    cp_total_m = compute_total_cp(components)

    if cp_total_m is None:
        static_margin = None
        ms_times_cna = None
    else:
        static_margin = (cp_total_m - center_of_mass_m) / rocket_diameter_m
        ms_times_cna = static_margin * total_cna

    fineness = rocket_length_m / rocket_diameter_m

    return {
        "available": True,
        "message": "Calcul Barrowman effectué avec les formules composant par composant.",
        "warnings": warnings,
        "missing_fields": [],
        "invalid_fields": [],
        "components": components,
        "nose_cna": nose_cna,
        "nose_cp_m": nose_cp_m,
        "fins_cna": fins_cna,
        "fins_cp_m": fins_cp_m,
        "total_cna": total_cna,
        "cp_total_m": cp_total_m,
        "center_of_mass_m": center_of_mass_m,
        "static_margin_barrowman": static_margin,
        "ms_times_cna_barrowman": ms_times_cna,
        "fineness": fineness,
        "method_notes": [
            "Méthode Barrowman de base.",
            "Tube cylindrique négligé en portance.",
            "Formule des ailerons trapézoïdaux utilisée.",
            "Correction corps/ailerons appliquée.",
            "Effets Mach, forte incidence, décrochage et stabilité dynamique non inclus dans ce calcul statique.",
        ],
    }