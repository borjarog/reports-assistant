import os
import socket
import psycopg2
import matplotlib.pyplot as plt
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from datetime import datetime

load_dotenv()

app = FastAPI(title="Asistente de Informes Médicos")


# ----------------------------
# Función para conectar a la BD
# ----------------------------
def conectar_db():
    host = os.getenv("DB_HOST")
    try:
        ipv4 = socket.gethostbyname(host)
    except Exception:
        ipv4 = host

    return psycopg2.connect(
        host=ipv4,
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "postgres"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD"),
        connect_timeout=10,
    )


# ----------------------------
# Función para obtener datos del paciente
# ----------------------------
def obtener_datos_paciente(patient_id):
    con = conectar_db()
    cur = con.cursor()
    cur.execute("SELECT * FROM paciente WHERE patient_id = %s", (patient_id,))
    data = cur.fetchone()
    cur.close()
    con.close()
    return data


# ----------------------------
# Función para obtener resultados clínicos
# ----------------------------
def obtener_resultados_clinicos(patient_id):
    con = conectar_db()
    cur = con.cursor()
    cur.execute(
        "SELECT fecha, temperatura, frecuencia_cardiaca, spo2, pcr_mg_l FROM resultados_clinicos WHERE patient_id = %s ORDER BY fecha",
        (patient_id,),
    )
    data = cur.fetchall()
    cur.close()
    con.close()
    return data


# ----------------------------
# Función para generar gráfico temporal
# ----------------------------
def generar_grafico(resultados):
    if not resultados:
        return None

    fechas = [r[0] for r in resultados]
    temperatura = [r[1] for r in resultados]
    pcr = [r[4] for r in resultados]

    plt.figure(figsize=(6, 3))
    plt.plot(fechas, temperatura, marker="o", label="Temperatura (°C)")
    plt.plot(fechas, pcr, marker="s", label="PCR (mg/L)")
    plt.xlabel("Fecha")
    plt.ylabel("Valor")
    plt.title("Evolución Clínica del Paciente")
    plt.legend()
    plt.tight_layout()

    grafico_path = "grafico.png"
    plt.savefig(grafico_path)
    plt.close()
    return grafico_path


# ----------------------------
# Generar informe PDF
# ----------------------------
def generar_pdf(paciente, resultados):
    pdf_path = f"informe_{paciente[0]}.pdf"
    c = canvas.Canvas(pdf_path, pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 16)
    c.drawString(2 * cm, height - 2 * cm, "Informe Evolutivo del Paciente")

    c.setFont("Helvetica", 12)
    c.drawString(2 * cm, height - 3 * cm, f"Paciente: {paciente[1]}")
    c.drawString(2 * cm, height - 3.7 * cm, f"Edad: {paciente[2]} años")
    c.drawString(2 * cm, height - 4.4 * cm, f"Motivo ingreso: {paciente[10]}")
    c.drawString(2 * cm, height - 5.1 * cm, f"Servicio: {paciente[11]}")

    # Inserta gráfico si existe
    grafico = generar_grafico(resultados)
    if grafico:
        c.drawImage(
            grafico,
            2 * cm,
            height / 2 - 3 * cm,
            width=16 * cm,
            preserveAspectRatio=True,
        )

    c.setFont("Helvetica", 10)
    c.setFillColor(colors.gray)
    c.drawString(
        2 * cm, 2 * cm, f"Generado el {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )

    c.save()
    return pdf_path


# ----------------------------
# Endpoint principal
# ----------------------------
@app.post("/generar_informe")
def generar_informe(data: dict):
    patient_id = data.get("patient_id")
    if not patient_id:
        raise HTTPException(status_code=400, detail="Falta patient_id")

    paciente = obtener_datos_paciente(patient_id)
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    resultados = obtener_resultados_clinicos(patient_id)
    pdf_path = generar_pdf(paciente, resultados)
    return FileResponse(
        pdf_path, media_type="application/pdf", filename=os.path.basename(pdf_path)
    )
