import math

from app.services.propulsion_database import get_propellant_data


FUSEX_CRITERIA = {
    "ms_min": 2.0,
    "ms_max": 6.0,
    "cna_min": 15.0,
    "cna_max": 40.0,
    "moment_min": 40.0,
    "moment_max": 100.0,
    "fineness_min": 10.0,
    "fineness_max": 35.0,
    "rail_speed_min_m_s": 20.0,
}


def is_positive(value):
    # Vérifie qu'une valeur existe et qu'elle est strictement positive.
    return value is not None and value > 0


def check_interval(value_min, value_max, low, high):
    # Vérifie qu'un intervalle complet reste dans un domaine autorisé.
    if value_min is None or value_max is None:
        return {"value": None, "expected": f"entre {low} et {high}", "status": "Indisponible"}

    ok = value_min >= low and value_max <= high
    return {
        "value": f"[{value_min:.3f} ; {value_max:.3f}]",
        "expected": f"entre {low} et {high}",
        "status": "Conforme" if ok else "Non conforme",
    }


def check_value(value, low, high):
    # Vérifie qu'une valeur unique appartient à l'intervalle demandé.
    if value is None:
        return {"value": None, "expected": f"entre {low} et {high}", "status": "Indisponible"}

    ok = low <= value <= high
    return {"value": value, "expected": f"entre {low} et {high}", "status": "Conforme" if ok else "Non conforme"}


def _motor_cg_abs(motor_rear_position_m, motor_length_m, motor_cg_local_m):
    # Transforme un centre de gravité local du propulseur en position absolue depuis la pointe.
    # La position arrière du propulseur correspond au plan arrière du bloc moteur dans la fusée.
    return motor_rear_position_m - motor_length_m + motor_cg_local_m


def _missing_fields(fields):
    # Liste les entrées absentes pour expliquer proprement pourquoi un calcul n'est pas disponible.
    return [name for name, value in fields.items() if value is None or value == ""]


def compute_mass_states(
    mass_reference_kg,
    mass_reference_type,
    cg_reference_m,
    cg_reference_type,
    motor_type,
    motor_rear_position_m,
):
    # Reconstruit les trois états de masse utilisés par StabTraj :
    # fusée sans propulseur, fusée avec propulseur plein, fusée avec propulseur vide.
    # L'utilisateur choisit un moteur ; les masses et CG du moteur viennent de la base interne.
    motor = get_propellant_data(motor_type)

    required = {
        "mass_reference_kg": mass_reference_kg,
        "mass_reference_type": mass_reference_type,
        "cg_reference_m": cg_reference_m,
        "cg_reference_type": cg_reference_type,
        "motor_type": motor_type,
        "motor_rear_position_m": motor_rear_position_m,
    }
    missing = _missing_fields(required)

    if missing:
        return {
            "available": False,
            "message": "Bilan de masse indisponible : données de masse, de centrage ou de moteur incomplètes.",
            "missing_fields": missing,
            "motor": None,
        }

    if motor is None:
        return {
            "available": False,
            "message": "Bilan de masse indisponible : propulseur absent de la base interne.",
            "missing_fields": ["motor_type"],
            "motor": None,
        }

    motor_full_mass_kg = motor.get("motor_full_mass_kg")
    motor_empty_mass_kg = motor.get("motor_empty_mass_kg")
    motor_length_m = motor.get("motor_length_m")
    motor_cg_full_local_m = motor.get("motor_cg_full_local_m")
    motor_cg_empty_local_m = motor.get("motor_cg_empty_local_m")

    motor_required = {
        "motor_full_mass_kg": motor_full_mass_kg,
        "motor_empty_mass_kg": motor_empty_mass_kg,
        "motor_length_m": motor_length_m,
        "motor_cg_full_local_m": motor_cg_full_local_m,
        "motor_cg_empty_local_m": motor_cg_empty_local_m,
    }
    motor_missing = _missing_fields(motor_required)

    if motor_missing:
        return {
            "available": False,
            "message": "Bilan de masse indisponible : fiche propulseur incomplète.",
            "missing_fields": motor_missing,
            "motor": motor,
        }

    motor_cg_full_abs = _motor_cg_abs(motor_rear_position_m, motor_length_m, motor_cg_full_local_m)
    motor_cg_empty_abs = _motor_cg_abs(motor_rear_position_m, motor_length_m, motor_cg_empty_local_m)

    if mass_reference_type == "sans_propulseur":
        mass_without_motor = mass_reference_kg
    elif mass_reference_type == "avec_propulseur_vide":
        mass_without_motor = mass_reference_kg - motor_empty_mass_kg
    elif mass_reference_type == "avec_propulseur_plein":
        mass_without_motor = mass_reference_kg - motor_full_mass_kg
    else:
        return {"available": False, "message": "Type de masse inconnu.", "invalid_fields": ["mass_reference_type"], "motor": motor}

    mass_empty = mass_without_motor + motor_empty_mass_kg
    mass_full = mass_without_motor + motor_full_mass_kg

    if mass_without_motor <= 0 or mass_empty <= 0 or mass_full <= 0:
        return {"available": False, "message": "Bilan de masse impossible : masse négative ou nulle.", "motor": motor}

    if cg_reference_type == "sans_propulseur":
        cg_without_motor = cg_reference_m
    elif cg_reference_type == "avec_propulseur_vide":
        cg_without_motor = (cg_reference_m * mass_empty - motor_cg_empty_abs * motor_empty_mass_kg) / mass_without_motor
    elif cg_reference_type == "avec_propulseur_plein":
        cg_without_motor = (cg_reference_m * mass_full - motor_cg_full_abs * motor_full_mass_kg) / mass_without_motor
    else:
        return {"available": False, "message": "Type de CG inconnu.", "invalid_fields": ["cg_reference_type"], "motor": motor}

    cg_full = (cg_without_motor * mass_without_motor + motor_cg_full_abs * motor_full_mass_kg) / mass_full
    cg_empty = (cg_without_motor * mass_without_motor + motor_cg_empty_abs * motor_empty_mass_kg) / mass_empty

    return {
        "available": True,
        "message": "Bilan de masse calculé.",
        "motor": motor,
        "motor_type": motor_type,
        "motor_label": motor.get("label"),
        "mass_without_motor_kg": mass_without_motor,
        "mass_empty_kg": mass_empty,
        "mass_full_kg": mass_full,
        "cg_without_motor_m": cg_without_motor,
        "cg_full_m": cg_full,
        "cg_empty_m": cg_empty,
        "motor_cg_full_abs_m": motor_cg_full_abs,
        "motor_cg_empty_abs_m": motor_cg_empty_abs,
        "motor_rear_position_m": motor_rear_position_m,
        "motor_full_mass_kg": motor_full_mass_kg,
        "motor_empty_mass_kg": motor_empty_mass_kg,
        "motor_length_m": motor_length_m,
        "motor_diameter_m": motor.get("motor_diameter_m"),
    }


def compute_nose_cna(nose_diameter_m, reference_diameter_m):
    # Cnα de l'ogive. Pour un diamètre identique au diamètre de référence, on retrouve Cnα = 2.
    return 2.0 * (nose_diameter_m / reference_diameter_m) ** 2


def compute_nose_cp(nose_height_m, nose_profile):
    # Position du CPA d'ogive depuis la pointe.
    # Les coefficients sont ceux des formes classiques utilisées dans la méthode de Barrowman.
    profile = (nose_profile or "").strip().lower()

    if profile.startswith("con"):
        return (2.0 / 3.0) * nose_height_m

    if profile.startswith("parab") or profile.startswith("ellip"):
        return 0.5 * nose_height_m

    return (7.0 / 15.0) * nose_height_m


def compute_fin_mid_chord(root_chord_m, tip_chord_m, sweep_m, span_m):
    # Longueur de la ligne mi-corde de l'aileron trapézoïdal.
    return math.sqrt(span_m**2 + (sweep_m + (tip_chord_m - root_chord_m) / 2.0) ** 2)


def compute_fin_interference_factor(reference_diameter_m, span_m, fin_count):
    # Facteur correctif d'interaction entre le corps et les ailerons.
    ratio = reference_diameter_m / (2.0 * span_m + reference_diameter_m)
    if round(fin_count) == 6:
        return 1.0 + 0.5 * ratio
    return 1.0 + ratio


def compute_fins_cna(reference_diameter_m, fin_count, root_chord_m, tip_chord_m, sweep_m, span_m):
    # Gradient de portance des ailerons trapézoïdaux.
    mid_chord = compute_fin_mid_chord(root_chord_m, tip_chord_m, sweep_m, span_m)
    denominator = 1.0 + math.sqrt(1.0 + (2.0 * mid_chord / (root_chord_m + tip_chord_m)) ** 2)
    interference = compute_fin_interference_factor(reference_diameter_m, span_m, fin_count)
    return interference * (4.0 * fin_count * (span_m / reference_diameter_m) ** 2) / denominator


def compute_fins_cp(fin_position_m, root_chord_m, tip_chord_m, sweep_m):
    # Position du CPA des ailerons depuis la pointe.
    # fin_position_m désigne le bord arrière au pied de l'aileron.
    x_root_leading = fin_position_m - root_chord_m
    first_term = sweep_m * (root_chord_m + 2.0 * tip_chord_m) / (3.0 * (root_chord_m + tip_chord_m))
    second_term = ((root_chord_m + tip_chord_m) - (root_chord_m * tip_chord_m / (root_chord_m + tip_chord_m))) / 6.0
    return x_root_leading + first_term + second_term


def compute_weighted_cp(components):
    # Le CPA total est un barycentre pondéré par les Cna de chaque élément.
    total_cna = sum(component["cna"] for component in components)
    if total_cna <= 0:
        return None
    return sum(component["cna"] * component["cp_m"] for component in components) / total_cna


def classify_theoretical_stability(ms_min, ms_max, cna, moment_min, moment_max, fineness):
    # Classement global à partir des critères FUSEX.
    if None in (ms_min, ms_max, cna, moment_min, moment_max, fineness):
        return "Indéterminé"
    if ms_min < FUSEX_CRITERIA["ms_min"] or cna < FUSEX_CRITERIA["cna_min"] or moment_min < FUSEX_CRITERIA["moment_min"]:
        return "Sous-stable"
    if ms_max > FUSEX_CRITERIA["ms_max"] or cna > FUSEX_CRITERIA["cna_max"] or moment_max > FUSEX_CRITERIA["moment_max"]:
        return "Surstable"
    if not (FUSEX_CRITERIA["fineness_min"] <= fineness <= FUSEX_CRITERIA["fineness_max"]):
        return "Hors finesse recommandée"
    return "Stable"


def build_theoretical_stability(
    rocket_length_m,
    rocket_diameter_m,
    mass_reference_kg,
    mass_reference_type,
    cg_reference_m,
    cg_reference_type,
    motor_type,
    motor_rear_position_m,
    nose_profile,
    nose_height_m,
    nose_diameter_m,
    fin_position_m,
    fin_root_chord_m,
    fin_tip_chord_m,
    fin_sweep_m,
    fin_span_m,
    fin_thickness_m,
    fin_count,
):
    # Analyse théorique complète : bilan de masse, CPA, Cnα, marge statique et produit MS × Cnα.
    mass_states = compute_mass_states(
        mass_reference_kg=mass_reference_kg,
        mass_reference_type=mass_reference_type,
        cg_reference_m=cg_reference_m,
        cg_reference_type=cg_reference_type,
        motor_type=motor_type,
        motor_rear_position_m=motor_rear_position_m,
    )

    cg_full = mass_states.get("cg_full_m") if mass_states.get("available") else None
    cg_empty = mass_states.get("cg_empty_m") if mass_states.get("available") else None

    required = {
        "rocket_length_m": rocket_length_m,
        "rocket_diameter_m": rocket_diameter_m,
        "cg_full": cg_full,
        "cg_empty": cg_empty,
        "nose_height_m": nose_height_m,
        "nose_diameter_m": nose_diameter_m,
        "fin_position_m": fin_position_m,
        "fin_root_chord_m": fin_root_chord_m,
        "fin_tip_chord_m": fin_tip_chord_m,
        "fin_sweep_m": fin_sweep_m,
        "fin_span_m": fin_span_m,
        "fin_count": fin_count,
    }

    missing = _missing_fields(required)
    if missing:
        return {
            "available": False,
            "message": "Analyse théorique indisponible : données théoriques incomplètes.",
            "missing_fields": missing,
            "mass_states": mass_states,
        }

    nose_cna = compute_nose_cna(nose_diameter_m, rocket_diameter_m)
    nose_cp = compute_nose_cp(nose_height_m, nose_profile)
    fins_cna = compute_fins_cna(rocket_diameter_m, fin_count, fin_root_chord_m, fin_tip_chord_m, fin_sweep_m, fin_span_m)
    fins_cp = compute_fins_cp(fin_position_m, fin_root_chord_m, fin_tip_chord_m, fin_sweep_m)

    components = [
        {"name": "Ogive", "cna": nose_cna, "cp_m": nose_cp},
        {"name": "Ailerons", "cna": fins_cna, "cp_m": fins_cp},
    ]

    total_cna = nose_cna + fins_cna
    cp_total = compute_weighted_cp(components)

    ms_full = (cp_total - cg_full) / rocket_diameter_m
    ms_empty = (cp_total - cg_empty) / rocket_diameter_m
    ms_min = min(ms_full, ms_empty)
    ms_max = max(ms_full, ms_empty)

    moment_full = ms_full * total_cna
    moment_empty = ms_empty * total_cna
    moment_min = min(moment_full, moment_empty)
    moment_max = max(moment_full, moment_empty)

    fineness = rocket_length_m / rocket_diameter_m
    verdict = classify_theoretical_stability(ms_min, ms_max, total_cna, moment_min, moment_max, fineness)

    return {
        "available": True,
        "message": "Analyse théorique effectuée.",
        "mass_states": mass_states,
        "components": components,
        "cp_theoretical_m": cp_total,
        "cna_theoretical": total_cna,
        "nose_cna": nose_cna,
        "nose_cp_m": nose_cp,
        "fins_cna": fins_cna,
        "fins_cp_m": fins_cp,
        "center_of_mass_full_m": cg_full,
        "center_of_mass_empty_m": cg_empty,
        "ms_full": ms_full,
        "ms_empty": ms_empty,
        "ms_min": ms_min,
        "ms_max": ms_max,
        "moment_full": moment_full,
        "moment_empty": moment_empty,
        "moment_min": moment_min,
        "moment_max": moment_max,
        "fineness": fineness,
        "verdict": verdict,
        "checks": {
            "marge_statique_theorique": check_interval(ms_min, ms_max, FUSEX_CRITERIA["ms_min"], FUSEX_CRITERIA["ms_max"]),
            "cna_theorique": check_value(total_cna, FUSEX_CRITERIA["cna_min"], FUSEX_CRITERIA["cna_max"]),
            "moment_theorique": check_interval(moment_min, moment_max, FUSEX_CRITERIA["moment_min"], FUSEX_CRITERIA["moment_max"]),
            "finesse": check_value(fineness, FUSEX_CRITERIA["fineness_min"], FUSEX_CRITERIA["fineness_max"]),
        },
    }