import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url
import os


def subir_imagen(image_path):
    # Configuration       
    cloudinary.config( 
        cloud_name = os.getenv("CloudName_Cloudinary"), 
        api_key = os.getenv("ApiKey_Cloudinary"), 
        api_secret = os.getenv("ApiSectet_Cloudinary"), # Click 'View API Keys' above to copy your API secret
        secure=True
    )
    # Upload an image
    upload_result = cloudinary.uploader.upload(image_path)
    return upload_result["secure_url"]