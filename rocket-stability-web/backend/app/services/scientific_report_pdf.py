import io
from datetime import datetime


def _fmt(value, digits=3, unit=""):
    # Formate les valeurs numériques pour garder une présentation homogène.
    if value is None or value == "":
        return "Indisponible"

    try:
        return f"{float(value):.{digits}f}{unit}"
    except Exception:
        return str(value)


def _safe_text(value):
    # Évite les erreurs lorsque le rapport contient une valeur vide.
    if value is None:
        return "Indisponible"
    return str(value)


def _status_color(status):
    # Couleur simple selon le résultat d'un critère.
    if status == "Conforme":
        return "#15803d"
    if status == "Non conforme":
        return "#b91c1c"
    return "#475569"


def build_scientific_pdf_report(report: dict, filename: str = "simulation.csv") -> bytes:
    # Génère le rapport scientifique PDF complet à partir du rapport FUSEX calculé.
    # La fonction retourne directement les octets du PDF pour FastAPI.
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        SimpleDocTemplate,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
        PageBreak,
    )

    buffer = io.BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.6 * cm,
        leftMargin=1.6 * cm,
        topMargin=1.4 * cm,
        bottomMargin=1.4 * cm,
        title="Rapport scientifique de stabilité FUSEX",
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "TitreRapport",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=14,
    )

    subtitle_style = ParagraphStyle(
        "SousTitreRapport",
        parent=styles["Normal"],
        alignment=TA_CENTER,
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#475569"),
        spaceAfter=18,
    )

    section_style = ParagraphStyle(
        "TitreSection",
        parent=styles["Heading2"],
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#1d4ed8"),
        spaceBefore=12,
        spaceAfter=8,
    )

    normal_style = ParagraphStyle(
        "TexteNormal",
        parent=styles["Normal"],
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#334155"),
        alignment=TA_LEFT,
    )

    strong_style = ParagraphStyle(
        "TexteFort",
        parent=normal_style,
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#0f172a"),
    )

    story = []

    story.append(Paragraph("Rapport scientifique de stabilité FUSEX", title_style))
    story.append(
        Paragraph(
            f"Fichier analysé : <b>{_safe_text(filename)}</b><br/>"
            f"Date de génération : {datetime.now().strftime('%d/%m/%Y à %H:%M')}",
            subtitle_style,
        )
    )

    story.append(Paragraph("1. Synthèse générale", section_style))
    story.append(
        Paragraph(
            f"Verdict global : <b>{_safe_text(report.get('global_verdict'))}</b><br/>"
            f"Référence utilisée : <b>{_safe_text(report.get('criteria_reference', 'FUSEX'))}</b>",
            strong_style,
        )
    )

    criteria = report.get("criteria", {}) or {}
    if criteria:
        story.append(Spacer(1, 8))
        criteria_rows = [
            ["Critère", "Domaine retenu"],
            ["Marge statique MS", f"{criteria.get('ms_min', 2)} à {criteria.get('ms_max', 6)} D"],
            ["Cnα", f"{criteria.get('cna_min', 15)} à {criteria.get('cna_max', 40)}"],
            ["MS × Cnα", f"{criteria.get('moment_min', 40)} à {criteria.get('moment_max', 100)}"],
            ["Finesse", f"{criteria.get('fineness_min', 10)} à {criteria.get('fineness_max', 35)}"],
            ["Vitesse sortie rampe", "> 20 m/s"],
        ]
        story.append(_make_table(criteria_rows))

    story.append(Paragraph("2. Données théoriques", section_style))
    theoretical = report.get("theoretical", {}) or {}
    geometry = report.get("geometry", {}) or {}

    theoretical_rows = [
        ["Grandeur", "Valeur"],
        ["Longueur fusée", _fmt(geometry.get("rocket_length_m"), 3, " m")],
        ["Diamètre de référence", _fmt(geometry.get("rocket_diameter_m"), 3, " m")],
        ["Propulseur", _safe_text(theoretical.get("motor_type") or theoretical.get("mass_states", {}).get("motor_label"))],
        ["CPA théorique", _fmt(theoretical.get("cp_theoretical_m"), 3, " m")],
        ["CG plein", _fmt(theoretical.get("center_of_mass_full_m"), 3, " m")],
        ["CG vide", _fmt(theoretical.get("center_of_mass_empty_m"), 3, " m")],
        ["Cnα théorique", _fmt(theoretical.get("cna_theoretical"))],
        ["MS théorique minimale", _fmt(theoretical.get("ms_min"), 3, " D")],
        ["MS théorique maximale", _fmt(theoretical.get("ms_max"), 3, " D")],
        ["MS × Cnα minimal", _fmt(theoretical.get("moment_min"))],
        ["MS × Cnα maximal", _fmt(theoretical.get("moment_max"))],
        ["Finesse", _fmt(theoretical.get("fineness"))],
        ["Verdict théorique", _safe_text(theoretical.get("verdict"))],
    ]
    story.append(_make_table(theoretical_rows))

    story.append(Paragraph("3. Données simulées OpenRocket", section_style))
    simulated = report.get("simulated", {}) or {}

    simulated_rows = [
        ["Grandeur", "Valeur"],
        ["MS simulée minimale", _fmt(simulated.get("ms_min_openrocket"), 3, " D")],
        ["MS simulée maximale", _fmt(simulated.get("ms_max_openrocket"), 3, " D")],
        ["Cn minimal OpenRocket", _fmt(simulated.get("cn_min_openrocket"))],
        ["Cn maximal OpenRocket", _fmt(simulated.get("cn_max_openrocket"))],
        ["MS × Cnα simulé minimal", _fmt(simulated.get("moment_min"))],
        ["MS × Cnα simulé maximal", _fmt(simulated.get("moment_max"))],
        ["Vitesse sortie rampe", _fmt(simulated.get("rail_speed_m_s"), 3, " m/s")],
        ["Instant retenu", _fmt(simulated.get("rail_speed_time_s"), 3, " s")],
        ["Mach maximal", _fmt(simulated.get("mach_max"))],
        ["Altitude maximale", _fmt(simulated.get("altitude_max_m"), 2, " m")],
    ]
    story.append(_make_table(simulated_rows))

    checks = report.get("checks", {}) or {}
    if checks:
        story.append(Paragraph("4. Vérifications FUSEX", section_style))
        check_rows = [["Critère", "Valeur trouvée", "Attendu", "Statut"]]

        for key, check in checks.items():
            label = _labelize_check(key)
            check_rows.append(
                [
                    label,
                    _safe_text(check.get("value")),
                    _safe_text(check.get("expected")),
                    _safe_text(check.get("status")),
                ]
            )

        story.append(_make_checks_table(check_rows))

    interpretation = report.get("interpretation", {}) or {}
    sections = interpretation.get("sections", []) or []

    if sections:
        story.append(PageBreak())
        story.append(Paragraph("5. Diagnostic et interprétation scientifique", section_style))

        for section in sections:
            story.append(Paragraph(f"<b>{_safe_text(section.get('title'))}</b>", strong_style))
            story.append(Paragraph(f"<b>{_safe_text(section.get('verdict'))}</b>", normal_style))
            story.append(Paragraph(_safe_text(section.get("text")), normal_style))

            facts = section.get("facts", []) or []
            if facts:
                fact_rows = [["Élément", "Valeur"]]
                for fact in facts:
                    fact_rows.append([_safe_text(fact.get("label")), _safe_text(fact.get("value"))])
                story.append(_make_table(fact_rows))

            story.append(Spacer(1, 8))

    confidence = interpretation.get("confidence")
    if confidence:
        story.append(Paragraph("6. Niveau de confiance", section_style))
        story.append(
            Paragraph(
                f"<b>{_safe_text(confidence.get('level'))}</b><br/>{_safe_text(confidence.get('text'))}",
                normal_style,
            )
        )

    story.append(Paragraph("7. Remarque scientifique", section_style))
    story.append(
        Paragraph(
            "Le rapport sépare volontairement l'analyse théorique issue de la géométrie et l'analyse simulée "
            "issue du CSV OpenRocket. Le coefficient Cn exporté par OpenRocket n'est pas confondu avec le "
            "gradient Cnα. Le produit MS × Cnα utilise donc le Cnα théorique calculé à partir de la géométrie.",
            normal_style,
        )
    )

    document.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    return pdf_bytes


def _make_table(rows):
    # Tableau standard pour les valeurs numériques et géométriques.
    from reportlab.lib import colors
    from reportlab.platypus import Table, TableStyle

    table = Table(rows, colWidths=[210, 260])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.6),
                ("LEADING", (0, 0), (-1, -1), 11),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#cbd5e1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def _make_checks_table(rows):
    # Tableau spécifique aux critères pour garder les statuts bien visibles.
    from reportlab.lib import colors
    from reportlab.platypus import Table, TableStyle

    table = Table(rows, colWidths=[150, 105, 115, 100])

    style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.2),
        ("LEADING", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#cbd5e1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]

    for row_index in range(1, len(rows)):
        status = rows[row_index][3]
        if status == "Conforme":
            style.append(("BACKGROUND", (3, row_index), (3, row_index), colors.HexColor("#dcfce7")))
            style.append(("TEXTCOLOR", (3, row_index), (3, row_index), colors.HexColor("#166534")))
        elif status == "Non conforme":
            style.append(("BACKGROUND", (3, row_index), (3, row_index), colors.HexColor("#fee2e2")))
            style.append(("TEXTCOLOR", (3, row_index), (3, row_index), colors.HexColor("#991b1b")))
        else:
            style.append(("BACKGROUND", (3, row_index), (3, row_index), colors.HexColor("#f1f5f9")))
            style.append(("TEXTCOLOR", (3, row_index), (3, row_index), colors.HexColor("#475569")))

    table.setStyle(TableStyle(style))
    return table


def _labelize_check(key: str) -> str:
    # Libellés propres pour les critères affichés dans le rapport.
    labels = {
        "marge_statique_theorique": "Marge statique théorique",
        "cna_theorique": "Cnα théorique",
        "moment_theorique": "MS × Cnα théorique",
        "finesse": "Finesse",
        "marge_statique_simulee": "Marge statique simulée",
        "moment_simule": "MS × Cnα simulé",
        "vitesse_sortie_rampe": "Vitesse de sortie de rampe",
    }

    return labels.get(key, key.replace("_", " "))