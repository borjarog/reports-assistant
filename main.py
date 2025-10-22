from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel
from datetime import datetime
import matplotlib

matplotlib.use("Agg")  # evita problemas con backend gráfico
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import random, tempfile, os

app = FastAPI()


class Paciente(BaseModel):
    paciente: str


@app.post("/generar_informe")
async def generar_informe(data: Paciente):
    nombre = data.paciente
    presiones = [random.randint(110, 140) for _ in range(5)]

    # --- 1. Generar y guardar el gráfico temporalmente ---
    temp_dir = tempfile.gettempdir()
    img_path = os.path.join(temp_dir, "grafico.png")

    plt.plot(presiones, marker="o", color="blue")
    plt.title(f"Presión arterial de {nombre}")
    plt.xlabel("Medición")
    plt.ylabel("mmHg")
    plt.savefig(img_path)
    plt.close()

    # --- 2. Crear PDF ---
    pdf_path = os.path.join(temp_dir, f"informe_{nombre.replace(' ', '_')}.pdf")
    c = canvas.Canvas(pdf_path, pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 80, "Informe Clínico Automatizado")
    c.setFont("Helvetica", 12)
    c.drawString(50, height - 120, f"Paciente: {nombre}")
    c.drawString(
        50, height - 140, f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    )
    c.drawString(50, height - 180, "Presión arterial (mmHg):")
    c.drawString(70, height - 200, ", ".join(map(str, presiones)))

    # --- 3. Insertar la imagen guardada ---
    c.drawImage(
        img_path, 50, height - 450, width=500, preserveAspectRatio=True, mask="auto"
    )

    c.setFont("Helvetica-Oblique", 10)
    c.drawString(50, 60, "Informe generado automáticamente — demo para datathon")
    c.save()

    # --- 4. Devolver el PDF ---
    return FileResponse(
        pdf_path, filename=os.path.basename(pdf_path), media_type="application/pdf"
    )
