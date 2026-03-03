from PIL import Image, ImageDraw, ImageFont
import os
import shutil

# Configuraciones de rutas
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")
TMP_IMAGES = "/tmp/images"
os.makedirs(TMP_IMAGES, exist_ok=True)

def generar_imgticket(idclient, qr_path):
    """
    Genera una imagen PNG de alta resolución basada en la plantilla de 768px.
    Optimizado para que el QR sea grande, nítido y fácil de escanear.
    """
    # 1. Cargar la plantilla de fondo
    template_path = os.path.join(ASSETS_DIR, "Template3.png")
    
    with Image.open(template_path) as template:
        # Convertimos a RGBA para máxima calidad
        img = template.convert("RGBA")
        draw = ImageDraw.Draw(img)
        
        w_img, h_img = img.size 
        # factor será ~128 si tu plantilla es de 768px (768 / 6.0)
        factor = w_img / 6.0  

        # 2. Configurar el QR (Subimos escala de 2.6 a 3.8 para que sea GIGANTE)
        ESCALA_QR_HD = 3.8
        
        # Posiciones base en CM según tu diseño original
        qr_orig_x, qr_orig_y = 2.41 * factor, 3.86 * factor
        qr_orig_w, qr_orig_h = 1.16 * factor, 1.16 * factor
        
        # Tamaño final en píxeles (Escalado)
        qr_w = int(qr_orig_w * ESCALA_QR_HD)
        qr_h = int(qr_orig_h * ESCALA_QR_HD)
        
        # Fórmula para que el QR crezca desde el centro y no se mueva de lugar
        qr_x = int(qr_orig_x + (qr_orig_w - qr_w) / 2)
        qr_y = int(qr_orig_y + (qr_orig_h - qr_h) / 2)

        # Pegar el QR con máxima calidad de interpolación
        with Image.open(qr_path) as qr_img:
            # LANCZOS es el secreto para que no se vea borroso al agrandar/achicar
            qr_img = qr_img.convert("RGBA").resize((qr_w, qr_h), Image.Resampling.LANCZOS)
            img.paste(qr_img, (qr_x, qr_y), qr_img)

        # 3. Texto: "Sistema de Parqueo"
        fuente_path = os.path.join(ASSETS_DIR, "templatefuente.ttf")
        
        # Tamaño de fuente proporcional al nuevo tamaño del QR
        font_size = int(32 * factor / 10) 
        font = ImageFont.truetype(fuente_path, font_size)

        texto = "Sistema de Parqueo"
        # Centrado horizontal automático del texto
        bbox = draw.textbbox((0, 0), texto, font=font)
        text_w = bbox[2] - bbox[0]
        
        # Margen para que el texto no choque con el QR agrandado
        margen_texto = 0.3 * factor 
        texto_x = (w_img - text_w) / 2
        texto_y = qr_y + qr_h + margen_texto

        # Dibujamos el texto en negro puro para mejor contraste
        draw.text((texto_x, texto_y), texto, font=font, fill="black")

        # 4. Guardar como PNG optimizado
        output_path = os.path.join(TMP_IMAGES, f"carnet_{idclient}.png")
        # 'optimize=True' mantiene la calidad bajando un poco el peso del archivo
        img.save(output_path, "PNG", optimize=True)
        
    return output_path