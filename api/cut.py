import os
from PIL import Image

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TMP_IMAGES = "/tmp/images"
os.makedirs(TMP_IMAGES, exist_ok=True)

def cut_image(image_path, target_ratio=1.0):
    """
    Recorta la imagen para que tenga el ratio deseado.
    - target_ratio = ancho/alto deseado (1.0 para cuadrado)
    - No cambia resolución, solo recorta centrado
    - Devuelve la ruta del PNG recortado
    """

    img = Image.open(image_path).convert("RGB")
    w, h = img.size
    img_ratio = w / h

    # Determinar recorte
    if img_ratio > target_ratio:
        # Imagen más ancha → recortar ancho
        new_w = int(h * target_ratio)
        left = (w - new_w) // 2
        img = img.crop((left, 0, left + new_w, h))
    elif img_ratio < target_ratio:
        # Imagen más alta → recortar alto
        new_h = int(w / target_ratio)
        top = (h - new_h) // 2
        img = img.crop((0, top, w, top + new_h))
    # else: mismo ratio → no recortar
    img = img.resize((574, 574), Image.LANCZOS)
    # Construir ruta basada en nombre del archivo original
    base_name = os.path.splitext(os.path.basename(image_path))[0]
    output_name = f"{base_name}_resized.png"
    output_path = os.path.join(TMP_IMAGES, output_name)

    img.save(output_path, optimize=True)
    return output_path
