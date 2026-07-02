def _fmt(value, digits=3, unit=""):
    # Met les valeurs numériques au même format dans toutes les phrases du diagnostic.
    if value is None:
        return "indisponible"

    try:
        return f"{float(value):.{digits}f}{unit}"
    except Exception:
        return str(value)


def _is_between(value, low, high):
    # Teste une grandeur seulement si elle existe vraiment.
    return value is not None and low <= value <= high


def build_scientific_interpretation(theoretical: dict, simulated: dict) -> dict:
    # Construit le diagnostic scientifique affiché dans l'interface et dans le rapport PDF.
    # L'ordre des parties suit la logique retenue pour le projet : théorie, simulation, écart, causes,
    # conclusion et recommandations.
    sections = [
        _interpret_theoretical_geometry(theoretical),
        _interpret_simulated_flight(simulated),
        _compare_theory_and_simulation(theoretical, simulated),
        _build_probable_causes(theoretical, simulated),
        _build_general_conclusion(theoretical, simulated),
        _build_recommendations(theoretical, simulated),
    ]

    return {
        "title": "Diagnostic et interprétation scientifique",
        "sections": sections,
        "confidence": _build_confidence_level(theoretical, simulated),
    }


def _interpret_theoretical_geometry(theoretical: dict) -> dict:
    # Interprète la stabilité obtenue avec les données théoriques saisies.
    if not theoretical.get("available"):
        missing = theoretical.get("missing_fields", [])
        details = ", ".join(missing) if missing else "données théoriques incomplètes"
        return {
            "title": "1. Interprétation théorique de la géométrie",
            "severity": "gray",
            "verdict": "Analyse théorique indisponible",
            "text": (
                "L'analyse théorique ne peut pas être conclue car certaines données nécessaires ne sont pas "
                f"exploitables : {details}. Le résultat ne doit donc pas être assimilé à une validation de stabilité."
            ),
            "facts": [],
        }

    verdict = theoretical.get("verdict")
    cp = theoretical.get("cp_theoretical_m")
    cna = theoretical.get("cna_theoretical")
    ms_min = theoretical.get("ms_min")
    ms_max = theoretical.get("ms_max")
    moment_min = theoretical.get("moment_min")
    moment_max = theoretical.get("moment_max")
    mass_states = theoretical.get("mass_states", {}) or {}

    if verdict == "Stable":
        severity = "green"
        title = "La géométrie présente une stabilité théorique satisfaisante."
        text = (
            "Le centre de pression aérodynamique théorique est placé en arrière du centre de masse. "
            "La marge statique, le gradient de portance et le produit MS × Cnα sont dans les domaines "
            "retenus pour une fusée expérimentale. La géométrie produit donc un couple de rappel suffisant "
            "sans tomber dans une surstabilité excessive."
        )
    elif verdict == "Sous-stable":
        severity = "red"
        title = "La géométrie paraît sous-stable."
        text = (
            "Le couple de rappel théorique est insuffisant. Cela peut venir d'une marge statique trop faible, "
            "d'un Cnα trop bas ou d'un produit MS × Cnα insuffisant. Dans ce cas, la fusée risque de ne pas "
            "retrouver correctement son axe après une perturbation."
        )
    elif verdict == "Surstable":
        severity = "orange"
        title = "La géométrie présente un risque de surstabilité."
        text = (
            "Le couple de rappel devient trop important. Une fusée surstable peut sur-réagir aux perturbations, "
            "osciller davantage et être très sensible au vent en sortie de rampe."
        )
    elif verdict == "Hors finesse recommandée":
        severity = "orange"
        title = "La stabilité principale est lisible, mais la finesse sort du domaine recommandé."
        text = (
            "La finesse de la fusée n'est pas dans le domaine retenu. La marge statique reste alors moins "
            "facile à interpréter, car le diamètre de référence ne représente pas toujours correctement "
            "l'échelle aérodynamique et inertielle de l'engin."
        )
    else:
        severity = "orange"
        title = "La géométrie demande une lecture prudente."
        text = (
            "Une ou plusieurs grandeurs sortent des domaines recommandés. La stabilité théorique ne doit pas "
            "être validée sans examiner précisément les critères en défaut."
        )

    facts = [
        {"label": "Propulseur", "value": mass_states.get("motor_label") or theoretical.get("motor_type") or "indisponible"},
        {"label": "CPA théorique", "value": _fmt(cp, 3, " m")},
        {"label": "CG plein", "value": _fmt(theoretical.get("center_of_mass_full_m"), 3, " m")},
        {"label": "CG vide", "value": _fmt(theoretical.get("center_of_mass_empty_m"), 3, " m")},
        {"label": "Marge statique théorique", "value": f"[{_fmt(ms_min)} ; {_fmt(ms_max)}] D"},
        {"label": "Cnα théorique", "value": _fmt(cna)},
        {"label": "MS × Cnα théorique", "value": f"[{_fmt(moment_min)} ; {_fmt(moment_max)}]"},
    ]

    return {
        "title": "1. Interprétation théorique de la géométrie",
        "severity": severity,
        "verdict": title,
        "text": text,
        "facts": facts,
    }


def _interpret_simulated_flight(simulated: dict) -> dict:
    # Interprète la partie qui provient uniquement du CSV de simulation OpenRocket.
    ms_min = simulated.get("ms_min_openrocket")
    ms_max = simulated.get("ms_max_openrocket")
    rail_speed = simulated.get("rail_speed_m_s")
    mach_max = simulated.get("mach_max")
    altitude_max = simulated.get("altitude_max_m")

    if ms_min is None and ms_max is None:
        return {
            "title": "2. Interprétation du vol simulé",
            "severity": "gray",
            "verdict": "Analyse simulée indisponible",
            "text": (
                "La simulation ne fournit pas de marge statique exploitable. Les graphes peuvent rester utiles, "
                "mais la stabilité simulée ne peut pas être conclue à partir des critères FUSEX."
            ),
            "facts": [],
        }

    if ms_min is not None and ms_min < 2:
        severity = "red"
        verdict = "La stabilité simulée n'est pas maintenue sur tout le vol."
        text = (
            "La marge statique simulée descend sous la limite minimale. Pendant au moins une partie du vol, "
            "le bras de levier entre le centre de masse et le centre de pression est trop faible pour garantir "
            "un rappel aérodynamique suffisant."
        )
    elif ms_max is not None and ms_max > 6:
        severity = "orange"
        verdict = "La simulation montre un risque de surstabilité."
        text = (
            "La marge statique simulée dépasse la limite haute. Le vol peut devenir très sensible au vent, "
            "en particulier lorsque la vitesse est encore faible après la sortie de rampe."
        )
    else:
        severity = "green"
        verdict = "La stabilité simulée reste dans le domaine attendu."
        text = (
            "La marge statique simulée reste dans le domaine recommandé. La simulation est donc cohérente "
            "avec une stabilité globale correcte pour ce critère."
        )

    if rail_speed is not None and rail_speed <= 20:
        severity = "red" if severity != "orange" else severity
        text += " La vitesse estimée en sortie de rampe est cependant insuffisante pour le critère FUSEX."

    return {
        "title": "2. Interprétation du vol simulé",
        "severity": severity,
        "verdict": verdict,
        "text": text,
        "facts": [
            {"label": "Marge statique simulée", "value": f"[{_fmt(ms_min)} ; {_fmt(ms_max)}] D"},
            {"label": "Vitesse estimée en sortie de rampe", "value": _fmt(rail_speed, 3, " m/s")},
            {"label": "Mach maximal", "value": _fmt(mach_max)},
            {"label": "Altitude maximale", "value": _fmt(altitude_max, 2, " m")},
        ],
    }


def _compare_theory_and_simulation(theoretical: dict, simulated: dict) -> dict:
    # Compare l'analyse théorique et les grandeurs issues du vol simulé.
    theory_ok = theoretical.get("verdict") == "Stable"
    ms_sim_min = simulated.get("ms_min_openrocket")
    ms_sim_max = simulated.get("ms_max_openrocket")
    rail_speed = simulated.get("rail_speed_m_s")
    sim_ok = _is_between(ms_sim_min, 2, 6) and _is_between(ms_sim_max, 2, 6) and (rail_speed is None or rail_speed > 20)

    if theory_ok and sim_ok:
        return {
            "title": "3. Écart entre théorie et simulation",
            "severity": "green",
            "verdict": "L'analyse théorique et la simulation sont cohérentes.",
            "text": "La géométrie est stable et la simulation ne montre pas de rupture des critères principaux.",
            "facts": [],
        }

    if theory_ok and not sim_ok:
        return {
            "title": "3. Écart entre théorie et simulation",
            "severity": "orange",
            "verdict": "La géométrie est correcte, mais la simulation révèle une limite en vol.",
            "text": (
                "Le problème ne vient pas forcément de la forme générale de la fusée. Il peut être lié à la vitesse "
                "de sortie de rampe, à l'évolution du centre de masse, au régime de vol ou à la façon dont OpenRocket "
                "modélise les grandeurs aérodynamiques pendant la simulation."
            ),
            "facts": [],
        }

    if not theory_ok and sim_ok:
        return {
            "title": "3. Écart entre théorie et simulation",
            "severity": "orange",
            "verdict": "La simulation paraît acceptable, mais la théorie doit être corrigée.",
            "text": (
                "La lecture simulée ne suffit pas à valider une géométrie théoriquement hors domaine. Les données "
                "saisies doivent être vérifiées avant toute conclusion favorable."
            ),
            "facts": [],
        }

    return {
        "title": "3. Écart entre théorie et simulation",
        "severity": "red",
        "verdict": "La théorie et la simulation signalent des réserves.",
        "text": "Les deux lectures présentent au moins une non-conformité. La configuration doit être reprise avant validation.",
        "facts": [],
    }


def _build_probable_causes(theoretical: dict, simulated: dict) -> dict:
    # Liste uniquement les causes appuyées par une grandeur calculée.
    causes = []
    cna = theoretical.get("cna_theoretical")
    ms_theory_min = theoretical.get("ms_min")
    ms_theory_max = theoretical.get("ms_max")
    moment_min = theoretical.get("moment_min")
    moment_max = theoretical.get("moment_max")
    rail_speed = simulated.get("rail_speed_m_s")
    ms_sim_min = simulated.get("ms_min_openrocket")
    ms_sim_max = simulated.get("ms_max_openrocket")

    if cna is not None and cna < 15:
        causes.append("Cnα théorique trop faible : les ailettes sont probablement trop peu efficaces.")
    if cna is not None and cna > 40:
        causes.append("Cnα théorique trop fort : les ailettes rendent probablement le rappel aérodynamique excessif.")
    if ms_theory_min is not None and ms_theory_min < 2:
        causes.append("Marge statique théorique trop basse : le CG est trop arrière ou le CPA trop avancé.")
    if ms_theory_max is not None and ms_theory_max > 6:
        causes.append("Marge statique théorique trop haute : le CG est très avancé ou l'empennage trop stabilisant.")
    if moment_min is not None and moment_min < 40:
        causes.append("Produit MS × Cnα trop faible : le moment de rappel théorique est insuffisant.")
    if moment_max is not None and moment_max > 100:
        causes.append("Produit MS × Cnα trop fort : la fusée risque de sur-réagir aux perturbations.")
    if ms_sim_min is not None and ms_sim_min < 2:
        causes.append("Marge statique simulée trop basse sur une partie du vol : l'évolution du CG ou du CPA doit être vérifiée.")
    if ms_sim_max is not None and ms_sim_max > 6:
        causes.append("Marge statique simulée trop haute sur une partie du vol : le risque de girouettage augmente.")
    if rail_speed is not None and rail_speed <= 20:
        causes.append("Vitesse de sortie de rampe insuffisante : les ailettes ne travaillent pas encore assez efficacement.")

    if not causes:
        causes.append("Aucune cause critique évidente n'est détectée avec les données disponibles.")

    return {
        "title": "4. Causes probables",
        "severity": "blue",
        "verdict": "Lecture causale des écarts",
        "text": "Les causes ci-dessous sont proposées uniquement lorsqu'elles sont reliées aux grandeurs calculées.",
        "facts": [{"label": f"Cause {index + 1}", "value": cause} for index, cause in enumerate(causes)],
    }


def _build_general_conclusion(theoretical: dict, simulated: dict) -> dict:
    # Rédige une conclusion générale en combinant théorie et simulation.
    theory_ok = theoretical.get("verdict") == "Stable"
    ms_sim_min = simulated.get("ms_min_openrocket")
    ms_sim_max = simulated.get("ms_max_openrocket")
    rail_speed = simulated.get("rail_speed_m_s")
    sim_margin_ok = _is_between(ms_sim_min, 2, 6) and _is_between(ms_sim_max, 2, 6)
    rail_ok = rail_speed is not None and rail_speed > 20

    if theory_ok and sim_margin_ok and rail_ok:
        return {
            "title": "5. Conclusion générale",
            "severity": "green",
            "verdict": "Conclusion favorable",
            "text": "La configuration respecte les critères principaux disponibles et ne montre pas de défaut majeur dans la simulation.",
            "facts": [],
        }

    if theory_ok:
        return {
            "title": "5. Conclusion générale",
            "severity": "orange",
            "verdict": "Géométrie favorable, mais validation de vol réservée",
            "text": (
                "La géométrie est théoriquement stable, mais la simulation signale au moins une limite. "
                "La configuration doit être améliorée ou justifiée avant une conclusion globale favorable."
            ),
            "facts": [],
        }

    return {
        "title": "5. Conclusion générale",
        "severity": "red",
        "verdict": "Conclusion défavorable ou incomplète",
        "text": "Les données disponibles ne permettent pas de valider la stabilité. Les non-conformités doivent être corrigées.",
        "facts": [],
    }


def _build_recommendations(theoretical: dict, simulated: dict) -> dict:
    # Propose des actions concrètes à partir des critères en défaut.
    recommendations = []
    cna = theoretical.get("cna_theoretical")
    ms_theory_min = theoretical.get("ms_min")
    ms_theory_max = theoretical.get("ms_max")
    rail_speed = simulated.get("rail_speed_m_s")

    if rail_speed is not None and rail_speed <= 20:
        recommendations.append("Augmenter la vitesse de sortie de rampe : rampe plus longue, masse réduite ou choix moteur à revoir.")
    if cna is not None and cna < 15:
        recommendations.append("Augmenter l'efficacité des ailettes : envergure plus grande, implantation plus basse ou géométrie plus favorable.")
    if cna is not None and cna > 40:
        recommendations.append("Réduire l'efficacité des ailettes pour limiter la surstabilité.")
    if ms_theory_min is not None and ms_theory_min < 2:
        recommendations.append("Avancer le centre de masse ou reculer le centre de pression pour augmenter la marge statique.")
    if ms_theory_max is not None and ms_theory_max > 6:
        recommendations.append("Réduire la marge statique en évitant un CG trop avancé ou un empennage trop stabilisant.")

    if not recommendations:
        recommendations.append("Aucune modification majeure n'est déduite des critères disponibles. Une vérification expérimentale reste nécessaire.")

    return {
        "title": "6. Recommandations justifiées",
        "severity": "blue",
        "verdict": "Actions proposées",
        "text": "Les recommandations sont liées aux non-conformités détectées.",
        "facts": [{"label": f"Recommandation {index + 1}", "value": item} for index, item in enumerate(recommendations)],
    }


def _build_confidence_level(theoretical: dict, simulated: dict) -> dict:
    # Évalue la robustesse du diagnostic selon les données réellement disponibles.
    theory_available = theoretical.get("available") is True
    simulation_available = simulated.get("ms_min_openrocket") is not None

    if theory_available and simulation_available:
        return {"level": "Élevé", "text": "Les données théoriques et les données principales du CSV OpenRocket sont disponibles."}
    if theory_available or simulation_available:
        return {"level": "Moyen", "text": "Une seule partie de l'analyse est complète. La conclusion doit rester prudente."}
    return {"level": "Faible", "text": "Les données nécessaires à une conclusion robuste sont insuffisantes."}