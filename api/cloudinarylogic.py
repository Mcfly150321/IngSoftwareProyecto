import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url
import os


def subir_imagen(file_path):
    # Configuración (Se recomienda mover esto fuera de la función para mayor eficiencia, 
    # pero aquí está corregido para que funcione de inmediato)
    cloudinary.config( 
        cloud_name = os.getenv("CloudName_Cloudinary"), 
        api_key = os.getenv("ApiKey_Cloudinary"), 
        api_secret = os.getenv("ApiSectet_Cloudinary"),
        secure=True
    )
    
    # Subida del archivo
    upload_result = cloudinary.uploader.upload(
        file_path,
        # 'auto' detecta si es PDF, imagen o video automáticamente
        resource_type="auto", 
        # 'public_id' opcional: puedes darle un nombre claro al archivo
        # use_filename=True, 
        # unique_filename=True
    )
    
    # Retornamos la URL segura (HTTPS)
    return upload_result["secure_url"]