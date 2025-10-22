import tempfile
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import matplotlib.pyplot as plt
import os

# ==========================
# FUNCIONES AUXILIARES
# ==========================


def generar_grafico_evolucion(resultados, evolucion):
    """Genera un gráfico con temperatura, PCR y evolución general del paciente."""
    fig, ax1 = plt.subplots(figsize=(6, 3))

    # Eje 1 - temperatura y PCR
    fechas = [r["fecha"] for r in resultados if r.get("fecha")]
    temperatura = [r.get("temperatura", None) for r in resultados]
    pcr = [r.get("pcr_mg_l", None) for r in resultados]

    if fechas:
        ax1.plot(
            fechas, temperatura, color="tab:red", marker="o", label="Temperatura (°C)"
        )
        ax1.set_ylabel("Temperatura (°C)", color="tab:red")
        ax1.tick_params(axis="y", labelcolor="tab:red")
        ax1.set_xlabel("Fecha")
        ax1.set_title("Evolución clínica y biomarcadores")

        # Eje 2 - PCR
        ax2 = ax1.twinx()
        ax2.plot(fechas, pcr, color="tab:blue", marker="x", label="PCR (mg/L)")
        ax2.set_ylabel("PCR (mg/L)", color="tab:blue")
        ax2.tick_params(axis="y", labelcolor="tab:blue")

        ax1.grid(alpha=0.3)

    # Eje 3 - evolución médica (si hay)
    if evolucion:
        dias = [e["dia_estancia"] for e in evolucion]
        valoracion = [e["valoracion_estado"] for e in evolucion]
        plt.plot(dias, valoracion, "g--", label="Valoración médica (1-5)")
        plt.legend()

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    plt.tight_layout()
    plt.savefig(temp_file.name)
    plt.close()
    return temp_file.name


# ==========================
# FUNCIÓN PRINCIPAL PDF
# ==========================


def generar_informe_pdf(paciente, tratamientos, resultados, evolucion):
    """Crea un informe médico completo con formato elegante y gráfico de evolución."""
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    doc = SimpleDocTemplate(
        tmp.name,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="Titulo", fontSize=18, leading=22, alignment=1, spaceAfter=12
        )
    )
    styles.add(
        ParagraphStyle(
            name="Subtitulo",
            fontSize=13,
            textColor=colors.HexColor("#1d3557"),
            spaceAfter=6,
            leading=16,
        )
    )
    styles.add(ParagraphStyle(name="Texto", fontSize=10.5, leading=14))

    elementos = []

    # --- Encabezado ---
    elementos.append(Paragraph("Informe Clínico Evolutivo", styles["Titulo"]))
    elementos.append(
        Paragraph(
            f"Paciente: <b>{paciente['nombre']}</b> (ID: {paciente['patient_id']})",
            styles["Subtitulo"],
        )
    )
    elementos.append(
        Paragraph(
            f"<b>Edad:</b> {paciente['edad']} años &nbsp;&nbsp; "
            f"<b>Sexo:</b> {paciente['sexo']} &nbsp;&nbsp; "
            f"<b>Servicio:</b> {paciente['servicio']}",
            styles["Texto"],
        )
    )
    elementos.append(Spacer(1, 10))

    # --- Motivo y antecedentes ---
    elementos.append(
        Paragraph(
            "<b>Motivo de ingreso:</b> " + paciente.get("motivo_ingreso", ""),
            styles["Texto"],
        )
    )
    if paciente.get("comorbilidades"):
        elementos.append(
            Paragraph(
                "<b>Comorbilidades:</b> " + paciente["comorbilidades"], styles["Texto"]
            )
        )
    if paciente.get("alergias"):
        elementos.append(
            Paragraph("<b>Alergias:</b> " + paciente["alergias"], styles["Texto"])
        )
    elementos.append(Spacer(1, 14))

    # --- Tratamientos principales ---
    if tratamientos:
        elementos.append(Paragraph("Tratamientos principales", styles["Subtitulo"]))
        data = [["Día", "Tratamiento", "Vía", "Efectos"]]
        for t in tratamientos[:8]:
            data.append(
                [
                    t.get("dia_estancia", ""),
                    t.get("tratamiento", ""),
                    t.get("via_administracion", ""),
                    t.get("efectos_secundarios", "—"),
                ]
            )
        tabla = Table(data, colWidths=[2 * cm, 6 * cm, 3 * cm, 5 * cm])
        tabla.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d3557")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 10),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ]
            )
        )
        elementos.append(tabla)
        elementos.append(Spacer(1, 18))

    # --- Gráfico de evolución ---
    if resultados or evolucion:
        elementos.append(Paragraph("Evolución clínica", styles["Subtitulo"]))
        grafico = generar_grafico_evolucion(resultados, evolucion)
        elementos.append(Image(grafico, width=15 * cm, height=7 * cm))
        elementos.append(Spacer(1, 18))

    # --- Evolución médica ---
    if evolucion:
        elementos.append(Paragraph("Valoraciones médicas", styles["Subtitulo"]))
        data = [["Fecha", "Estado", "Dolor", "Movilidad", "Apetito", "Riesgo Recaída"]]
        for e in evolucion[-5:]:
            data.append(
                [
                    e["fecha"],
                    e["estado_general"],
                    e["dolor_nivel"],
                    e["movilidad"],
                    e["apetito"],
                    round(e["riesgo_recaida_estimado"] * 100, 1),
                ]
            )
        tabla_ev = Table(
            data, colWidths=[3 * cm, 3 * cm, 2 * cm, 2 * cm, 2 * cm, 3 * cm]
        )
        tabla_ev.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#457b9d")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ]
            )
        )
        elementos.append(tabla_ev)
        elementos.append(Spacer(1, 18))

    # --- Pie de informe ---
    elementos.append(Spacer(1, 20))
    elementos.append(
        Paragraph(
            "Informe generado automáticamente por el sistema <b>MedAI Evolution Assistant</b>.",
            styles["Texto"],
        )
    )
    elementos.append(
        Paragraph(
            "Los datos se obtienen en tiempo real desde el sistema clínico y registros de evolución.",
            styles["Texto"],
        )
    )

    doc.build(elementos)
    return tmp.name
