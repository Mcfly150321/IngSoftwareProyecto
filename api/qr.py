import os
import segno

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
TMP_IMAGES = "/tmp/images"

os.makedirs(TMP_IMAGES, exist_ok=True)


def generar_qr(data):
    # El 'data' ya es un hash (hex), usamos los últimos caracteres para el nombre
    # del archivo temporal para evitar colisiones y nombres demasiado largos.
    hash_ref = data[-5:] if len(data) > 5 else data
    file_name = f"qr_tmp_{hash_ref}.png"

    path = os.path.join(TMP_IMAGES, file_name)

    qr = segno.make_qr(data, error='h')
    qr.save(path, scale=15, dark="#003610", light="#ffffff")
    return path

