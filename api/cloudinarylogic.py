import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url
import os
import uuid


def _init_cloudinary():
    cloud_name = os.getenv("CloudName_Cloudinary") or os.getenv("CLOUDINARY_CLOUD_NAME")
    api_key = os.getenv("ApiKey_Cloudinary") or os.getenv("CLOUDINARY_API_KEY")
    api_secret = os.getenv("ApiSecret_Cloudinary") or os.getenv("ApiSectet_Cloudinary") or os.getenv("CLOUDINARY_API_SECRET")
    
    if not cloud_name or not api_key or not api_secret:
        raise RuntimeError("Cloudinary credentials missing: configure CloudName_Cloudinary, ApiKey_Cloudinary and ApiSecret_Cloudinary")

    cloudinary.config(
        cloud_name=cloud_name,
        api_key=api_key,
        api_secret=api_secret,
        secure=True
    )


def subir_imagen(file_path):
    _init_cloudinary()
    upload_result = cloudinary.uploader.upload(
        file_path,
        resource_type="auto",
        folder="parqueo_images",
        use_filename=True,
        unique_filename=True,
        access_mode="public"
    )
    return upload_result["secure_url"]


def subir_pdf(file_path):
    _init_cloudinary()
    upload_result = cloudinary.uploader.upload(
        file_path,
        resource_type="auto",
        folder="parqueo_pdfs",
        public_id=f"pdf_{uuid.uuid4().hex}",
        format="pdf",  # <--- Forzamos a Cloudinary a que entregue el archivo con extensión .pdf pública
        access_mode="public"
    )
    return upload_result["secure_url"]