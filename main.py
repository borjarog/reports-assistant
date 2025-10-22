from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from datetime import datetime
import os, tempfile
import psycopg2
from dotenv import load_dotenv

import matplotlib

matplotlib.use("Agg")  # backend sin GUI
import matplotlib.pyplot as plt

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# Carga .env en local; en Render usaremos variables de entorno del panel
load_dotenv()

app = FastAPI(title="Reports Assistant API", version="1.0")


class Payload(BaseModel):
    patient_id: str


def conectar_db():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "postgres"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD"),
    )


def fetch_paciente(cur, patient_id):
    cur.execute(
        """
        SELECT nombre, edad, sexo, motivo_ingreso, fecha_ingreso, servicio
        FROM paciente WHERE patient_id = %s
    """,
        (patient_id,),
    )
    return cur.fetchone()


def fetch_constantes(cur, patient_id):
    cur.execute(
        """
        SELECT fecha, temperatura, spo2, presion_arterial
        FROM resultados_clinicos
        WHERE patient_id = %s
        ORDER BY fecha
    """,
        (patient_id,),
    )
    return cur.fetchall()


def fetch_notas(cur, patient_id):
    cur.execute(
        """
        SELECT fecha, nota_medica
        FROM evolucion_medica
        WHERE patient_id = %s
        ORDER BY fecha
    """,
        (patient_id,),
    )
    return cur.fetchall()


def fetch_alta(cur, patient_id):
    cur.execute(
        """
        SELECT fecha_alta, diagnostico_principal, diagnosticos_secundarios,
               evolucion_resumen, tratamiento_alta, seguimiento_recomendado,
               riesgo_recaida_estimado, modelo_generador
        FROM alta_resumen
        WHERE patient_id = %s
        ORDER BY fecha_alta DESC
        LIMIT 1
    """,
        (patient_id,),
    )
    return cur.fetchone()


@app.post("/generar_informe")
async def generar_informe(data: Payload):
    try:
        con = conectar_db()
        cur = con.cursor()
        paciente = fetch_paciente(cur, data.patient_id)
        if not paciente:
            return JSONResponse({"error": "Paciente no encontrado"}, status_code=404)

        nombre, edad, sexo, motivo, ingreso, servicio = paciente
        constantes = fetch_constantes(cur, data.patient_id)
        notas = fetch_notas(cur, data.patient_id)
        alta = fetch_alta(cur, data.patient_id)
        con.close()

        # 1) Gráfico de temperatura
        img_path = os.path.join(tempfile.gettempdir(), f"temp_{data.patient_id}.png")
        if constantes:
            fechas = [r[0] for r in constantes]
            temps = [float(r[1]) if r[1] is not None else None for r in constantes]
            plt.figure()
            plt.plot(fechas, temps, marker="o")
            plt.title(f"Evolución de temperatura - {nombre}")
            plt.xlabel("Fecha")
            plt.ylabel("Temperatura (°C)")
            plt.tight_layout()
            plt.savefig(img_path)
            plt.close()
        else:
            # Por si no hay constantes
            plt.figure()
            plt.plot([0, 1], [36.8, 36.9], marker="o")
            plt.title(f"Evolución de temperatura - {nombre}")
            plt.xlabel("Tiempo")
            plt.ylabel("Temperatura (°C)")
            plt.tight_layout()
            plt.savefig(img_path)
            plt.close()

        # 2) PDF
        pdf_path = os.path.join(tempfile.gettempdir(), f"informe_{data.patient_id}.pdf")
        c = canvas.Canvas(pdf_path, pagesize=A4)
        width, height = A4

        # Cabecera
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, height - 60, f"Informe Evolutivo – {nombre}")
        c.setFont("Helvetica", 11)
        c.drawString(
            50, height - 80, f"ID: {data.patient_id}   Edad: {edad}   Sexo: {sexo}"
        )
        c.drawString(50, height - 95, f"Servicio: {servicio}")
        c.drawString(50, height - 110, f"Motivo de ingreso: {motivo}")
        if isinstance(ingreso, datetime):
            ingreso_str = ingreso.strftime("%d/%m/%Y")
        else:
            ingreso_str = str(ingreso) if ingreso else "-"
        c.drawString(50, height - 125, f"Fecha ingreso: {ingreso_str}")
        c.line(50, height - 135, width - 50, height - 135)

        # Evolución médica
        c.setFont("Helvetica-Bold", 13)
        c.drawString(50, height - 155, "Evolución clínica:")
        c.setFont("Helvetica", 10)
        y = height - 170
        if notas:
            for fecha, nota in notas:
                fecha_str = (
                    fecha.strftime("%d/%m/%Y")
                    if isinstance(fecha, datetime)
                    else str(fecha)
                )
                for linea in wrap_text(f"{fecha_str}: {nota}", 95):
                    c.drawString(55, y, linea)
                    y -= 12
                    if y < 120:
                        # inserta gráfico y salto de página
                        try:
                            c.drawImage(
                                img_path, 50, 140, width=500, preserveAspectRatio=True
                            )
                        except:
                            pass
                        c.showPage()
                        y = height - 60
                        c.setFont("Helvetica-Bold", 13)
                        c.drawString(50, y, "Evolución clínica (cont.):")
                        y -= 15
                        c.setFont("Helvetica", 10)
        else:
            c.drawString(55, y, "Sin notas registradas.")
            y -= 14

        # Gráfico (si cabe en la misma página)
        if y > 300:
            try:
                c.drawImage(img_path, 50, 140, width=500, preserveAspectRatio=True)
            except:
                pass
        else:
            c.showPage()
            try:
                c.drawImage(img_path, 50, 140, width=500, preserveAspectRatio=True)
            except:
                pass

        # Resumen de alta (si existe)
        c.setFont("Helvetica-Bold", 13)
        c.drawString(50, 120, "Resumen de alta:")
        c.setFont("Helvetica", 10)
        y2 = 105
        if alta:
            (
                fecha_alta,
                dx_principal,
                dx_sec,
                evol_resumen,
                tto_alta,
                seguimiento,
                riesgo,
                modelo,
            ) = alta
            campos = [
                (
                    "Fecha de alta",
                    fecha_alta.strftime("%d/%m/%Y")
                    if isinstance(fecha_alta, datetime)
                    else str(fecha_alta),
                ),
                ("Diagnóstico principal", dx_principal or "-"),
                ("Diagnósticos secundarios", dx_sec or "-"),
                ("Evolución (resumen)", evol_resumen or "-"),
                ("Tratamiento al alta", tto_alta or "-"),
                ("Seguimiento", seguimiento or "-"),
                ("Riesgo de recaída", f"{riesgo:.2f}" if riesgo is not None else "-"),
                ("Modelo generador", modelo or "-"),
            ]
            for titulo, valor in campos:
                lines = wrap_text(f"{titulo}: {valor}", 95)
                for line in lines:
                    c.drawString(55, y2, line)
                    y2 -= 12
                    if y2 < 60:
                        c.showPage()
                        y2 = height - 60
                        c.setFont("Helvetica-Bold", 13)
                        c.drawString(50, y2, "Resumen de alta (cont.):")
                        y2 -= 15
                        c.setFont("Helvetica", 10)
        else:
            c.drawString(55, y2, "No hay registro de alta para este paciente.")

        c.setFont("Helvetica-Oblique", 9)
        c.drawString(
            50,
            40,
            f"Generado automáticamente el {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        )
        c.save()

        return FileResponse(
            pdf_path, filename=os.path.basename(pdf_path), media_type="application/pdf"
        )

    except Exception as e:
        # Sí, errores pasan. No me mires así.
        return JSONResponse({"error": str(e)}, status_code=500)


def wrap_text(text, max_chars):
    # Rompe líneas largas para que no se salga del margen en PDF
    words = text.split()
    line, out = [], []
    for w in words:
        if sum(len(x) for x in line) + len(line) + len(w) <= max_chars:
            line.append(w)
        else:
            out.append(" ".join(line))
            line = [w]
    if line:
        out.append(" ".join(line))
    return out
