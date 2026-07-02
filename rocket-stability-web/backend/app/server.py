from pathlib import Path
import io
import tempfile
import traceback

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.services.csv_reader import read_openrocket_csv
from app.services.data_extractor import extract_useful_columns
from app.services.data_normalizer import normalize_openrocket_data
from app.services.stability_analysis import compute_stability, summarize_stability
from app.services.mach_analysis import analyze_mach_regime, summarize_mach
from app.services.performance_analysis import evaluate_performance
from app.services.launch_analysis import analyze_launch_phase, summarize_launch
from app.services.combined_analysis import analyze_stability_vs_mach, summarize_stability_vs_mach
from app.services.flight_summary import build_flight_summary
from app.services.compliance_analysis import build_fusex_compliance_report
from app.services.scientific_report_pdf import build_scientific_pdf_report
from app.services.propulsion_database import list_propellants, search_propellants

from app.services.plot_data import (
    build_plot_dataframe,
    build_cp_cg_vs_time,
    build_static_margin_vs_time,
    build_static_margin_vs_mach,
    build_cn_vs_time,
    build_cna_vs_time,
    build_ms_times_cna_vs_time,
    build_stability_criteria_diagram,
    build_speed_vs_time,
    build_altitude_vs_time,
    build_altitude_vs_range,
)


app = FastAPI(title="Analyse Stabilité Fusée")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def to_float_or_none(value: str | None) -> float | None:
    # Convertit proprement les champs du formulaire en nombres.
    # Une case vide reste None, ce qui permet ensuite de signaler une donnée manquante.
    if value is None:
        return None

    text = str(value).strip().replace(",", ".")

    if text == "":
        return None

    try:
        return float(text)
    except ValueError:
        return None


def remove_temp_file(path: str | None) -> None:
    # Supprime un fichier temporaire si la lecture du CSV est terminée.
    if path is None:
        return

    try:
        Path(path).unlink(missing_ok=True)
    except Exception:
        pass


async def save_upload_to_temp_csv(file: UploadFile) -> str:
    # Sauvegarde le CSV reçu dans un fichier temporaire lisible par pandas.
    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
        content = await file.read()
        tmp.write(content)
        return tmp.name


def read_clean_plot_dataframe(csv_path: str):
    # Pipeline commun aux routes : lecture OpenRocket, extraction, normalisation et préparation graphique.
    df_raw = read_openrocket_csv(csv_path)
    df_useful = extract_useful_columns(df_raw)
    df_clean = normalize_openrocket_data(df_useful)
    df_plot = build_plot_dataframe(df_clean)

    return df_clean, df_plot


def collect_geometry_kwargs(
    rocket_length_m: str | None,
    rocket_diameter_m: str | None,
    mass_reference_kg: str | None,
    mass_reference_type: str | None,
    cg_reference_m: str | None,
    cg_reference_type: str | None,
    motor_type: str | None,
    motor_rear_position_m: str | None,
    nose_profile: str | None,
    nose_height_m: str | None,
    nose_diameter_m: str | None,
    fin_position_m: str | None,
    fin_root_chord_m: str | None,
    fin_tip_chord_m: str | None,
    fin_sweep_m: str | None,
    fin_span_m: str | None,
    fin_thickness_m: str | None,
    fin_count: str | None,
) -> dict:
    # Les clés retournées ici correspondent exactement aux arguments du rapport FUSEX.
    return {
        "rocket_length_m": to_float_or_none(rocket_length_m),
        "rocket_diameter_m": to_float_or_none(rocket_diameter_m),
        "mass_reference_kg": to_float_or_none(mass_reference_kg),
        "mass_reference_type": mass_reference_type,
        "cg_reference_m": to_float_or_none(cg_reference_m),
        "cg_reference_type": cg_reference_type,
        "motor_type": motor_type,
        "motor_rear_position_m": to_float_or_none(motor_rear_position_m),
        "nose_profile": nose_profile,
        "nose_height_m": to_float_or_none(nose_height_m),
        "nose_diameter_m": to_float_or_none(nose_diameter_m),
        "fin_position_m": to_float_or_none(fin_position_m),
        "fin_root_chord_m": to_float_or_none(fin_root_chord_m),
        "fin_tip_chord_m": to_float_or_none(fin_tip_chord_m),
        "fin_sweep_m": to_float_or_none(fin_sweep_m),
        "fin_span_m": to_float_or_none(fin_span_m),
        "fin_thickness_m": to_float_or_none(fin_thickness_m),
        "fin_count": to_float_or_none(fin_count),
    }


def build_plots_payload(df_plot):
    # Toutes les courbes envoyées au frontend sont produites depuis le même tableau normalisé.
    return {
        "cp_cg_vs_time": build_cp_cg_vs_time(df_plot),
        "static_margin_vs_time": build_static_margin_vs_time(df_plot),
        "static_margin_vs_mach": build_static_margin_vs_mach(df_plot),
        "cn_vs_time": build_cn_vs_time(df_plot),
        "cna_vs_time": build_cna_vs_time(df_plot),
        "ms_times_cna_vs_time": build_ms_times_cna_vs_time(df_plot),
        "stability_criteria_diagram": build_stability_criteria_diagram(df_plot),
        "speed_vs_time": build_speed_vs_time(df_plot),
        "altitude_vs_time": build_altitude_vs_time(df_plot),
        "altitude_vs_range": build_altitude_vs_range(df_plot),
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/propellants")
def propellants(q: str | None = None):
    # Catalogue moteur pour la liste déroulante avec recherche.
    return {"items": search_propellants(q) if q else list_propellants()}


@app.post("/plot-data")
async def plot_data(file: UploadFile = File(...)):
    tmp_path = None

    try:
        print("1")
        tmp_path = await save_upload_to_temp_csv(file)

        print("2")
        df_clean, df_plot = read_clean_plot_dataframe(tmp_path)

        print("3")

        payload = build_plots_payload(df_plot)

        print("4")

        return {
            "filename": file.filename,
            "columns": list(df_plot.columns),
            "rows": int(len(df_plot)),
            **payload,
        }

    finally:
        remove_temp_file(tmp_path)
        

@app.post("/flight-summary")
async def flight_summary(file: UploadFile = File(...)):
    tmp_path = None

    try:
        tmp_path = await save_upload_to_temp_csv(file)
        _, df_plot = read_clean_plot_dataframe(tmp_path)

        return {"filename": file.filename, "summary": build_flight_summary(df_plot)}

    except Exception as e:
        print("=== ERREUR /flight-summary ===")
        print(traceback.format_exc())
        return {"error": str(e), "detail": "Regarde la console du serveur"}

    finally:
        remove_temp_file(tmp_path)


@app.post("/compliance-report")
async def compliance_report(
    file: UploadFile = File(...),
    rocket_length_m: str | None = Form(default=None),
    rocket_diameter_m: str | None = Form(default=None),
    mass_reference_kg: str | None = Form(default=None),
    mass_reference_type: str | None = Form(default=None),
    cg_reference_m: str | None = Form(default=None),
    cg_reference_type: str | None = Form(default=None),
    motor_type: str | None = Form(default=None),
    motor_rear_position_m: str | None = Form(default=None),
    nose_profile: str | None = Form(default=None),
    nose_height_m: str | None = Form(default=None),
    nose_diameter_m: str | None = Form(default=None),
    fin_position_m: str | None = Form(default=None),
    fin_root_chord_m: str | None = Form(default=None),
    fin_tip_chord_m: str | None = Form(default=None),
    fin_sweep_m: str | None = Form(default=None),
    fin_span_m: str | None = Form(default=None),
    fin_thickness_m: str | None = Form(default=None),
    fin_count: str | None = Form(default=None),
):
    tmp_path = None

    try:
        tmp_path = await save_upload_to_temp_csv(file)
        _, df_plot = read_clean_plot_dataframe(tmp_path)

        geometry_kwargs = collect_geometry_kwargs(
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
        )

        report = build_fusex_compliance_report(df_plot, **geometry_kwargs)

        return {"filename": file.filename, "report": report}

    except Exception as e:
        print("=== ERREUR /compliance-report ===")
        print(traceback.format_exc())
        return {"error": str(e), "detail": "Regarde la console du serveur"}

    finally:
        remove_temp_file(tmp_path)


@app.post("/full-analysis")
async def full_analysis(
    file: UploadFile = File(...),
    rocket_length_m: str | None = Form(default=None),
    rocket_diameter_m: str | None = Form(default=None),
    mass_reference_kg: str | None = Form(default=None),
    mass_reference_type: str | None = Form(default=None),
    cg_reference_m: str | None = Form(default=None),
    cg_reference_type: str | None = Form(default=None),
    motor_type: str | None = Form(default=None),
    motor_rear_position_m: str | None = Form(default=None),
    nose_profile: str | None = Form(default=None),
    nose_height_m: str | None = Form(default=None),
    nose_diameter_m: str | None = Form(default=None),
    fin_position_m: str | None = Form(default=None),
    fin_root_chord_m: str | None = Form(default=None),
    fin_tip_chord_m: str | None = Form(default=None),
    fin_sweep_m: str | None = Form(default=None),
    fin_span_m: str | None = Form(default=None),
    fin_thickness_m: str | None = Form(default=None),
    fin_count: str | None = Form(default=None),
):
    tmp_path = None

    try:
        tmp_path = await save_upload_to_temp_csv(file)
        df_clean, df_plot = read_clean_plot_dataframe(tmp_path)

        df_stability = compute_stability(df_clean)
        stability_summary = summarize_stability(df_stability)
        df_mach = analyze_mach_regime(df_stability)
        mach_summary = summarize_mach(df_mach)
        df_launch = analyze_launch_phase(df_mach)
        launch_summary = summarize_launch(df_launch) if not df_launch.empty else {}
        stability_vs_mach_df = analyze_stability_vs_mach(df_clean)
        stability_vs_mach_summary = summarize_stability_vs_mach(stability_vs_mach_df)
        performance_summary = evaluate_performance(df_stability)
        flight_summary_data = build_flight_summary(df_plot)

        geometry_kwargs = collect_geometry_kwargs(
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
        )

        compliance_report_data = build_fusex_compliance_report(df_plot, **geometry_kwargs)

        return {
            "filename": file.filename,
            "columns": list(df_plot.columns),
            "rows": int(len(df_plot)),
            "summaries": {
                "stability": stability_summary,
                "mach": mach_summary,
                "launch": launch_summary,
                "stability_vs_mach": stability_vs_mach_summary,
                "performance": performance_summary,
                "flight": flight_summary_data,
                "compliance": compliance_report_data,
            },
            "plots": build_plots_payload(df_plot),
        }

    except Exception as e:
        print("=== ERREUR /full-analysis ===")
        print(traceback.format_exc())
        return {"error": str(e), "detail": "Regarde la console du serveur"}

    finally:
        remove_temp_file(tmp_path)


@app.post("/export-report-pdf")
async def export_report_pdf(
    file: UploadFile = File(...),
    rocket_length_m: str | None = Form(default=None),
    rocket_diameter_m: str | None = Form(default=None),
    mass_reference_kg: str | None = Form(default=None),
    mass_reference_type: str | None = Form(default=None),
    cg_reference_m: str | None = Form(default=None),
    cg_reference_type: str | None = Form(default=None),
    motor_type: str | None = Form(default=None),
    motor_rear_position_m: str | None = Form(default=None),
    nose_profile: str | None = Form(default=None),
    nose_height_m: str | None = Form(default=None),
    nose_diameter_m: str | None = Form(default=None),
    fin_position_m: str | None = Form(default=None),
    fin_root_chord_m: str | None = Form(default=None),
    fin_tip_chord_m: str | None = Form(default=None),
    fin_sweep_m: str | None = Form(default=None),
    fin_span_m: str | None = Form(default=None),
    fin_thickness_m: str | None = Form(default=None),
    fin_count: str | None = Form(default=None),
):
    tmp_path = None

    try:
        tmp_path = await save_upload_to_temp_csv(file)
        _, df_plot = read_clean_plot_dataframe(tmp_path)

        geometry_kwargs = collect_geometry_kwargs(
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
        )

        report = build_fusex_compliance_report(df_plot, **geometry_kwargs)
        pdf_bytes = build_scientific_pdf_report(report=report, filename=file.filename or "simulation.csv")

        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": 'attachment; filename="rapport_stabilite_fusex.pdf"'},
        )

    except Exception as e:
        print("=== ERREUR /export-report-pdf ===")
        print(traceback.format_exc())
        return {"error": str(e), "detail": "Regarde la console du serveur"}

    finally:
        remove_temp_file(tmp_path)