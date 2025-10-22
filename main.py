from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import requests
import os

from pdf_generator import generar_informe_pdf  # <- Importa tu nuevo módulo

app = FastAPI(title="Asistente de Informes Médicos")

# ==========================
# VARIABLES DE ENTORNO
# ==========================
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


# ==========================
# MODELO DE ENTRADA
# ==========================
class PacienteInput(BaseModel):
    patient_id: str


# ==========================
# FUNCIONES AUXILIARES
# ==========================
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


def obtener_evolucion_medica(patient_id):
    """Obtiene las valoraciones médicas de la tabla 'evolucion_medica'."""
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }
    url = f"{SUPABASE_URL}/rest/v1/evolucion_medica?patient_id=eq.{patient_id}&order=fecha.asc"
    r = requests.get(url, headers=headers)

    if r.status_code != 200:
        raise HTTPException(status_code=500, detail=f"Error Supabase: {r.text}")
    return r.json()


# ==========================
# ENDPOINT PRINCIPAL
# ==========================
@app.post("/generar_informe")
def generar_informe(p: PacienteInput):
    """Genera y devuelve el PDF con la evolución del paciente."""
    try:
        paciente = obtener_datos_paciente(p.patient_id)
        tratamientos = obtener_tratamientos(p.patient_id)
        resultados = obtener_resultados_clinicos(p.patient_id)
        evolucion = obtener_evolucion_medica(p.patient_id)

        pdf_path = generar_informe_pdf(paciente, tratamientos, resultados, evolucion)

        return FileResponse(
            pdf_path,
            media_type="application/pdf",
            filename=f"informe_{p.patient_id}.pdf",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================
# ROOT (para probar)
# ==========================
@app.get("/")
def home():
    return {"status": "ok", "message": "API funcionando con Supabase y PDF mejorado"}
