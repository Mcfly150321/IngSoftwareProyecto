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

def generar_pdf(idclient, qr_path, foto_path=None, desplazamiento=0.0):
    """
    Genera un idclient PDF con plantilla.
    Medidas en cm.
    """
    pdf = FPDF(unit="cm", format=(6.0, 10.7))
    pdf.add_page()

    # 🖼️ Plantilla de fondo
    template_path = os.path.join(ASSETS_DIR, "Template3.png") #cambiando template con nuevo diseno
    pdf.image(template_path, x=0, y=0, w=6.0, h=10.7)

    # 👤 Foto Alumna (opcional)
    if foto_path and os.path.exists(foto_path):
        # x=1.9, y=1.2, w=2.2, h=2.2 aprox
        foto_orig_x, foto_orig_y = 1.9, 1.2
        foto_orig_w, foto_orig_h = 2.2, 2.2
        foto_w = foto_orig_w * ESCALA_FOTO
        foto_h = foto_orig_h * ESCALA_FOTO
        foto_x = foto_orig_x + (foto_orig_w - foto_w) / 2
        foto_y = foto_orig_y + (foto_orig_h - foto_h) / 2
        pdf.image(foto_path, x=foto_x, y=foto_y, w=foto_w, h=foto_h)

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
    pdf.multi_cell(w=6.0, h=linea_h, txt="Sistema de Parqueo", align="C")

    # 💾 Guardar
    output_path = os.path.join(TMP_PDFS, f"carnet_{idclient}.pdf")
    pdf.output(output_path)
    return output_path