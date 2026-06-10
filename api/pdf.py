import os
import uuid
from fpdf import FPDF

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")
TMP_PDFS = "/tmp/pdfs"

os.makedirs(TMP_PDFS, exist_ok=True)


# ✏️ Escalas independientes por elemento
ESCALA_FOTO   = 1.8
ESCALA_QR     = 2.6
ESCALA_TEXTO  = 2.5

def generar_pdf(nombre, image_path, qr_path):
    """
    Genera un carnet PDF con plantilla.
    Medidas en cm.
    """
    pdf = FPDF(unit="cm", format=(6.0, 10.7))
    pdf.add_page()

    # 🖼️ Plantilla de fondo
    template_path = os.path.join(ASSETS_DIR, "Template3.png") #cambiando template con nuevo diseno
    pdf.image(template_path, x=0, y=0, w=6.0, h=10.7)

    # 📸 Foto alumna (base: x=1.64, y=1.46, w=2.7, h=2.7)
    foto_orig_x, foto_orig_y = 1.64, 1.46
    foto_orig_w, foto_orig_h = 2.7,  2.7
    foto_w = foto_orig_w * ESCALA_FOTO
    foto_h = foto_orig_h * ESCALA_FOTO
    foto_x = foto_orig_x + (foto_orig_w - foto_w) / 2
    foto_y = foto_orig_y + (foto_orig_h - foto_h) / 2
    pdf.image(image_path, x=foto_x, y=foto_y, w=foto_w, h=foto_h)

    # El borde inferior de la foto escalada marca el punto de referencia
    # para todo lo que viene debajo, conservando distancias relativas.
    foto_bottom      = foto_orig_y + foto_orig_h          # borde inferior original
    foto_bottom_new  = foto_y + foto_h                    # borde inferior escalado
    desplazamiento   = foto_bottom_new - foto_bottom      # cuánto bajó todo

    # 📦 QR (base: x=2.41, y=3.86, w=1.16, h=1.16)
    qr_orig_x, qr_orig_y = 2.41, 3.86
    qr_orig_w, qr_orig_h = 1.16, 1.16
    qr_w = qr_orig_w * ESCALA_QR
    qr_h = qr_orig_h * ESCALA_QR
    qr_x = qr_orig_x + (qr_orig_w - qr_w) / 2
    qr_y = (qr_orig_y + desplazamiento) + (qr_orig_h - qr_h) / 2
    pdf.image(qr_path, x=qr_x, y=qr_y, w=qr_w, h=qr_h)

    # 🧾 Nombre alumna — siempre justo debajo del QR, con margen fijo
    MARGEN_TEXTO = 0.15   # cm de respiro entre QR y texto
    texto_y      = qr_y + qr_h + MARGEN_TEXTO
    texto_size   = 10 * ESCALA_TEXTO
    linea_h      = 0.6 * ESCALA_TEXTO

    # Fuente personalizada (templatefuente.ttf en /tmp/pdfs para evitar Error 30 Read-only)
    fuente_orig_path = os.path.join(ASSETS_DIR, "templatefuente.ttf")
    fuente_tmp_path = os.path.join(TMP_PDFS, "templatefuente.ttf")
    
    import shutil
    if not os.path.exists(fuente_tmp_path):
        shutil.copy2(fuente_orig_path, fuente_tmp_path)

    pdf.add_font("templatefuente", "", fuente_tmp_path, uni=True)
    pdf.set_font("templatefuente", size=texto_size)

    pdf.set_xy(0, texto_y)
    pdf.multi_cell(w=6.0, h=linea_h, txt=nombre, align="C")

    # 💾 Guardar
    base_name   = nombre.replace(" ", "_")
    output_path = os.path.join(TMP_PDFS, f"{base_name}_carnet.pdf")
    pdf.output(output_path)
    return output_path


def generar_pdf_historial_tickets(clients, desde=None, hasta=None):
    pdf = FPDF(unit="mm", format="A4")
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Historial de Tickets", ln=True, align="C")

    pdf.set_font("Arial", "", 11)
    if desde or hasta:
        range_text = f"Fecha: {desde or 'inicio'} → {hasta or 'hoy'}"
        pdf.cell(0, 8, range_text, ln=True)
    pdf.ln(4)

    if not clients:
        pdf.cell(0, 7, "No hay clientes para el rango seleccionado.", ln=True)
    else:
        for client in clients:
            title = f"{client.get('nombres', '')} {client.get('apellidos', '')}"
            pdf.set_font("Arial", "B", 12)
            pdf.multi_cell(0, 7, title)
            pdf.set_font("Arial", "", 11)
            pdf.cell(0, 6, f"ID ticket: {client.get('client_id', '')}", ln=True)
            pdf.cell(0, 6, f"Placa: {client.get('placa', '')}  ·  DPI: {client.get('dpi', '')}", ln=True)
            numero = client.get('numero') or 'N/A'
            pdf.cell(0, 6, f"Número: {numero}", ln=True)
            pdf.ln(4)

    output_path = os.path.join(TMP_PDFS, f"historial_tickets_{uuid.uuid4().hex}.pdf")
    pdf.output(output_path)
    return output_path


def generar_pdf_transacciones(client_name, client_id, transacciones, desde=None, hasta=None):
    pdf = FPDF(unit="mm", format="A4")
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Historial de Transacciones", ln=True, align="C")

    pdf.set_font("Arial", "", 11)
    pdf.cell(0, 7, f"Cliente: {client_name}", ln=True)
    pdf.cell(0, 7, f"Ticket: {client_id}", ln=True)
    if desde or hasta:
        range_text = f"Rango: {desde or 'inicio'} → {hasta or 'hoy'}"
        pdf.cell(0, 7, range_text, ln=True)
    pdf.ln(4)

    if not transacciones:
        pdf.cell(0, 7, "No hay transacciones para el rango seleccionado.", ln=True)
    else:
        for tx in transacciones:
            fecha = tx.get('fecha_hora', '')
            tipo = tx.get('tipo_transaccion', '')
            monto = tx.get('monto', 0)
            pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 7, f"{fecha} — {tipo.upper()}", ln=True)
            pdf.set_font("Arial", "", 11)
            pdf.cell(0, 7, f"Monto: Q{monto:.2f}" if isinstance(monto, (int, float)) else f"Monto: Q{monto}", ln=True)
            pdf.ln(2)

    output_path = os.path.join(TMP_PDFS, f"transacciones_{uuid.uuid4().hex}.pdf")
    pdf.output(output_path)
    return output_path