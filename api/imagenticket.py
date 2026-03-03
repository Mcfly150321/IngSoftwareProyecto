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
    Genera una imagen PNG basada en la plantilla.
    Pillow trabaja en PIXELES, por lo que convertimos los CM a PX (aprox 1cm = 38px).
    """
    # 1. Cargar la plantilla de fondo
    template_path = os.path.join(ASSETS_DIR, "Template3.png")
    with Image.open(template_path) as template:
        # Convertimos a RGBA para asegurar que soporte transparencia si la tiene
        img = template.convert("RGBA")
        draw = ImageDraw.Draw(img)
        
        # Obtener dimensiones de la plantilla (ej: 228x406 px para 6x10.7cm a 96dpi)
        w_img, h_img = img.size 
        factor = w_img / 6.0  # Factor de conversión CM a PX basado en el ancho

        # 2. Configurar el QR (Medidas originales en CM convertidas a PX)
        qr_orig_x, qr_orig_y = 2.41 * factor, 3.86 * factor
        qr_orig_w, qr_orig_h = 1.16 * factor, 1.16 * factor
        
        # Escala (Usamos tu escala 2.6)
        qr_w = int(qr_orig_w * 2.6)
        qr_h = int(qr_orig_h * 2.6)
        
        # Centrar QR respecto a su posición original
        qr_x = int(qr_orig_x + (qr_orig_w - qr_w) / 2)
        qr_y = int(qr_orig_y + (qr_orig_h - qr_h) / 2)

        # Pegar el QR sobre la plantilla
        with Image.open(qr_path) as qr_img:
            qr_img = qr_img.convert("RGBA").resize((qr_w, qr_h), Image.Resampling.LANCZOS)
            img.paste(qr_img, (qr_x, qr_y), qr_img)

        # 3. Texto: "Sistema de Parqueo"
        fuente_path = os.path.join(ASSETS_DIR, "templatefuente.ttf")
        # El tamaño de fuente en Pillow es en puntos, ajustamos según tu escala
        font_size = int(25 * factor / 10) # Ajuste manual para que se vea similar
        font = ImageFont.truetype(fuente_path, font_size)

        texto = "Sistema de Parqueo"
        # Calcular posición para centrar el texto
        bbox = draw.textbbox((0, 0), texto, font=font)
        text_w = bbox[2] - bbox[0]
        
        margen_texto = 0.15 * factor
        texto_x = (w_img - text_w) / 2
        texto_y = qr_y + qr_h + margen_texto

        # Dibujar el texto (puedes cambiar el color en 'fill')
        draw.text((texto_x, texto_y), texto, font=font, fill="black")

        # 4. Guardar como PNG
        output_path = os.path.join(TMP_IMAGES, f"carnet_{idclient}.png")
        img.save(output_path, "PNG")
        
    return output_path