from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import tempfile
import requests
import os
import matplotlib.pyplot as plt
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # durante desarrollo, permite todos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Variables de entorno
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


# --------------------------
# MODELO DE ENTRADA
# --------------------------
class PacienteInput(BaseModel):
    patient_id: str


# --------------------------
# FUNCIONES DE UTILIDAD
# --------------------------
def obtener_datos_paciente(patient_id):
    """Obtiene los datos del paciente desde la tabla 'paciente'."""
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }
    url = f"{SUPABASE_URL}/rest/v1/paciente?patient_id=eq.{patient_id}"

    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        raise HTTPException(status_code=500, detail=f"Error Supabase: {r.text}")

    data = r.json()
    if not data:
        raise HTTPException(
            status_code=404, detail=f"Paciente {patient_id} no encontrado."
        )
    return data[0]


def obtener_tratamientos(patient_id):
    """Obtiene los tratamientos del paciente desde la tabla 'tratamientos'."""
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }
    url = f"{SUPABASE_URL}/rest/v1/tratamientos?patient_id=eq.{patient_id}&order=dia_estancia.asc"

    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        raise HTTPException(status_code=500, detail=f"Error Supabase: {r.text}")
    return r.json()


def obtener_resultados_clinicos(patient_id):
    """Obtiene los resultados clínicos (analíticas, signos vitales...)"""
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }
    url = f"{SUPABASE_URL}/rest/v1/resultados_clinicos?patient_id=eq.{patient_id}&order=fecha.asc"

    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        raise HTTPException(status_code=500, detail=f"Error Supabase: {r.text}")
    return r.json()


# --------------------------
# FUNCIÓN PARA GRAFICAR
# --------------------------
def generar_grafico(resultados):
    """Genera un gráfico de la evolución de temperatura y PCR."""
    if not resultados:
        return None

    fechas = [r["fecha"] for r in resultados]
    temp = [r.get("temperatura", 0) for r in resultados]
    pcr = [r.get("pcr_mg_l", 0) for r in resultados]

    plt.figure(figsize=(6, 3))
    plt.plot(fechas, temp, marker="o", label="Temperatura (°C)")
    plt.plot(fechas, pcr, marker="x", label="PCR (mg/L)")
    plt.xlabel("Fecha")
    plt.ylabel("Valores")
    plt.title("Evolución clínica")
    plt.legend()
    plt.tight_layout()

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    plt.savefig(temp_file.name)
    plt.close()
    return temp_file.name


# --------------------------
# FUNCIÓN PARA GENERAR PDF
# --------------------------
def generar_pdf(paciente, tratamientos, resultados):
    """Genera un informe PDF básico con los datos del paciente."""
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    c = canvas.Canvas(tmp.name, pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 16)
    c.drawString(
        50, height - 80, f"Informe Evolutivo del Paciente: {paciente['nombre']}"
    )

    c.setFont("Helvetica", 11)
    c.drawString(50, height - 110, f"ID: {paciente['patient_id']}")
    c.drawString(50, height - 125, f"Edad: {paciente['edad']} años")
    c.drawString(50, height - 140, f"Sexo: {paciente['sexo']}")
    c.drawString(50, height - 155, f"Motivo de ingreso: {paciente['motivo_ingreso']}")
    c.drawString(50, height - 170, f"Servicio: {paciente['servicio']}")

    c.line(50, height - 180, width - 50, height - 180)
    c.drawString(50, height - 200, "Tratamientos principales:")

    y = height - 220
    for t in tratamientos[:5]:
        texto = f"- Día {t['dia_estancia']}: {t['tratamiento']} ({t.get('via_administracion', 'N/A')})"
        c.drawString(60, y, texto)
        y -= 15
        if y < 100:
            c.showPage()
            y = height - 100

    grafico_path = generar_grafico(resultados)
    if grafico_path:
        c.drawImage(grafico_path, 50, 200, width=500, height=250)

    c.setFont("Helvetica-Oblique", 10)
    c.drawString(50, 50, "Generado automáticamente por el asistente clínico IA.")
    c.save()
    return tmp.name


# --------------------------
# ENDPOINT PRINCIPAL
# --------------------------
@app.post("/generar_informe")
def generar_informe(p: PacienteInput):
    try:
        paciente = obtener_datos_paciente(p.patient_id)
        tratamientos = obtener_tratamientos(p.patient_id)
        resultados = obtener_resultados_clinicos(p.patient_id)

        pdf_path = generar_pdf(paciente, tratamientos, resultados)
        return FileResponse(
            pdf_path,
            media_type="application/pdf",
            filename=f"informe_{p.patient_id}.pdf",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --------------------------
# ROOT (solo para test rápido)
# --------------------------
@app.get("/")
def home():
    return {"status": "ok", "message": "API funcionando con Supabase REST"}
