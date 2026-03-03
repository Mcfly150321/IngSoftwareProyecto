import os
from PIL import Image, ImageDraw

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
TMP_IMAGES = "/tmp/images"
os.makedirs(TMP_IMAGES, exist_ok=True)

def photo_rounded(image_path, radius=None, border=4):
    """
    Aplica bordes redondeados y contorno negro a una imagen.
    - radius: si es None, se calcula como 15% del lado más corto
    - No hace resize ni recorte
    - Devuelve la ruta del PNG redondeado
    """

    img = Image.open(image_path).convert("RGBA")
    w, h = img.size

    # Calcular radius relativo si no se pasa
    if radius is None:
        radius = int(min(w, h) * 0.15)

    # Canvas más grande para el borde
    total_size = w + 2 * border
    canvas = Image.new("RGBA", (total_size, total_size), (0, 0, 0, 0))

    # Máscara para esquinas redondeadas
    mask = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, w, h), radius=radius, fill=255)

    # Pegar imagen en canvas con máscara
    canvas.paste(img, (border, border), mask)

    # Dibujar borde negro
    draw_canvas = ImageDraw.Draw(canvas)
    draw_canvas.rounded_rectangle(
        (border, border, border + w, border + h),
        radius=radius,
        outline="black",
        width=border
    )

    # Construir ruta basada en archivo de entrada
    base_name = os.path.splitext(os.path.basename(image_path))[0]
    output_name = f"{base_name}_rounded.png"
    output_path = os.path.join(TMP_IMAGES, output_name)

    canvas.save(output_path, optimize=True)
    return output_path
