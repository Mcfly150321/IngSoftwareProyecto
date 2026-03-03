from fastapi import FastAPI, Depends, HTTPException, Query, APIRouter, Request, File, Form, UploadFile
import json
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_, desc
from typing import List, Optional
from pydantic import BaseModel
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from . import database, schemas, models
from .database import SessionLocal, init_db
from .generatecarnet import generate_carnet
import datetime
from datetime import date
import random
import os
from .pdf import generar_pdf
from .qr import generar_qr
from .border import photo_rounded
from .hash import hashear_carnet
from .cloudinarylogic import subir_imagen




from fastapi.staticfiles import StaticFiles

app = FastAPI()

app.mount("/assets", StaticFiles(directory="assets"), name="assets")

router = APIRouter(prefix="/api")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Database
init_db()

@app.on_event("startup")
def on_startup():
    db = SessionLocal()
    try:
        # Filtramos directamente en la query para mayor eficiencia
        active_students = db.query(models.Client).filter(models.Client.is_active == True).all()
        
        new_records_count = 0
        
        for Client in active_students:
            for module_name in MODULES_LIST:
                exists = db.query(models.Modulos).filter(
                    models.Modulos.student_id == Client.idclient,
                    models.Modulos.Modulos == module_name
                ).first()
                
                if not exists:
                    db.add(models.Modulos(
                        student_id=Client.idclient,
                        Modulos=module_name,
                        month=0,
                        year=0,
                        is_approved=False
                    ))
                    new_records_count += 1 # Solo sumamos si realmente se añade a la DB
        
        db.commit()
        print(f"DEBUG: Startup - Se crearon {new_records_count} nuevos registros de módulos.")
        
    except Exception as e:
        db.rollback() # Siempre haz rollback si algo falla
        print(f"ERROR: {e}")
    finally:
        db.close()
# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

MODULES_LIST = [
    "Tratamientos Faciales y Cuidado de piel",
    "Maquillaje Profesional",
    "Manicura Express y Spa",
    "Pedicura Express y Spa",
    "Tratamientos Capilares",
    "Cortes de Cabello",
    "Introduccion a la Barberia",
    "Colorimetria",
    "Permacologia",
    "Peinados",
    "Administracion Economica y Creacion de Microempresas"
]



@router.get("/ping")
def ping():
    return {"status": "ok"}


@router.post("/clients/", response_model=schemas.StudentSchema)
async def create_student(
    student_data: str = Form(...), 
    photo: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    # PARSEO DE DATOS
    data = json.loads(student_data)
    Client = schemas.StudentCreate(**data)

    # --- LÓGICA DE RECEPCIÓN DE IMAGEN ---
    # La variable 'photo' es de tipo UploadFile.
    # Puedes usar 'await photo.read()' para obtener los bytes originales.
    if photo:
        # Validar tipo de archivo
        allowed_types = ["image/jpeg", "image/jpg", "image/png", "image/webp"]
        if photo.content_type not in allowed_types:
            raise HTTPException(
                status_code=400, 
                detail=f"Tipo de archivo no soportado: {photo.content_type}. Use JPG, PNG o WEBP."
            )
        
        photo_bytes = await photo.read()
        print(f"DEBUG: Foto recibida para nueva alumna. Tamaño: {len(photo_bytes)} bytes. Tipo: {photo.content_type}")
        # La variable 'photo_bytes' contiene la "carne" de la foto para tus operaciones.
    # ---------------------------------------

    db_student = models.Client(
        names=Client.names,
        lastnames=Client.lastnames,
        nit=Client.nit,
        parqueo_id=Client.parqueo_id,
        is_created=datetime.datetime.now()
    )
    db_student.idclient = f"2026{str(random.randint(100000, 999999))}"
    db_student.hash_carnet = hashear_carnet(db_student.idclient) 
    db_student.registration_date = datetime.datetime.now().strftime("%Y-%m")
    db_student.is_created = datetime.datetime.now()
    db.add(db_student)
    db.commit()
    db.refresh(db_student)

    # --- LÓGICA DE PROCESAMIENTO (QR, PDF, DRIVE) ---
    # Creamos carpetas temporales si no existen (En Vercel SOLO /tmp es escribible)
    tmp_images_dir = "/tmp/images"
    os.makedirs(tmp_images_dir, exist_ok=True)

    try:
        # 1. HASH Y QR (Siempre se generan)
        hash_qr = db_student.hash_carnet
        qr_path = generar_qr(hash_qr)
        qr_rounded = photo_rounded(qr_path)

        # 2. FOTO (Solo si el usuario la mandó)
        image_rounded = None
        if photo:
            # Guardamos los bytes en un archivo temporal para que photo_rounded pueda leerlo
            temp_photo_path = os.path.join(tmp_images_dir, f"temp_{db_student.idclient}.jpg")

            with open(temp_photo_path, "wb") as f:
                f.write(photo_bytes)

            photo_cloudinary_url = subir_imagen(temp_photo_path)
            db_student.photo_url = photo_cloudinary_url
            
            # Generar versión redondeada para el carnet
            image_rounded = photo_rounded(temp_photo_path)
            print(f"DEBUG: Foto subida para {db_student.idclient}")

        # 3. GENERAR PDF (Siempre se genera, con o sin foto)
        # pdf.py: generar_pdf(idclient, qr_path, foto_path=None, desplazamiento=0.0)
        pdf_path = generar_pdf(db_student.idclient, qr_rounded, image_rounded)
        
        # --- SUBIR PDF A CLOUDINARY ---
        pdf_cloudinary_url = subir_imagen(pdf_path)
        db_student.carnet_pdf_url = pdf_cloudinary_url
        
        db.commit()
        print(f"DEBUG: PDF subido a Cloudinary para {db_student.idclient}")

        # 4. AGREGAR A MODULOS (Independiente de si hay foto)
        for module_name in MODULES_LIST:
            exists = db.query(models.Modulos).filter(
                models.Modulos.student_id == db_student.idclient,
                models.Modulos.Modulos == module_name
            ).first()
            if not exists:
                db.add(models.Modulos(
                    student_id=db_student.idclient,
                    Modulos=module_name,
                    month=0,
                    year=0,
                    is_approved=False
                ))
        db.commit()

        # 5. LIMPIEZA DE ARCHIVOS TEMPORALES (Evitar llenar /tmp)
        # Recolectamos todos los archivos creados para borrar
        archivos_a_borrar = [qr_path, qr_rounded]
        if photo:
            archivos_a_borrar.extend([temp_photo_path, image_rounded, pdf_path])
        
        for p in archivos_a_borrar:
            try:
                if os.path.exists(p): os.remove(p)
            except: pass

    except Exception as e:
        print(f"ERROR en procesamiento post-registro: {str(e)}")
        # No lanzamos HTTPException para no anular la creación de la alumna en DB
    
    #esto para agregar estudiante a modulos
    

    return db_student


@router.get("/clients/", response_model=list[schemas.StudentSchema])
def read_students(status: str = "active", db: Session = Depends(get_db)):
    # status: "active", "inactive", "all"
    query = db.query(models.Client)
    
    if status == "active":
        query = query.filter(models.Client.is_active == True, models.Client.is_graduated == False)
    elif status == "inactive":
        # Inactive means effectively NOT active in current sessions
        query = query.filter(or_(models.Client.is_active == False, models.Client.is_graduated == True))
    
    return query.all()

@router.get("/clients/{plan}", response_model=list[schemas.StudentSchema])
def read_students_by_plan(plan: str, status: str = "active", db: Session = Depends(get_db)):
    query = db.query(models.Client)
    
    if status == "active":
        query = query.filter(models.Client.is_active == True, models.Client.is_graduated == False)
    elif status == "inactive":
        query = query.filter(or_(models.Client.is_active == False, models.Client.is_graduated == True))
        
    if plan == "todos":
        return query.all()
    return query.filter(models.Client.plan == plan).all()

@router.get("/clients/{idclient}/idclient-url")
def get_carnet_url(idclient: str, db: Session = Depends(get_db)):
    Client = db.query(models.Client.carnet_pdf_url).filter(models.Client.idclient == idclient).first()
    if not Client:
        raise HTTPException(status_code=404, detail="Client not found")
    return {"carnet_pdf_url": Client[0]}


@router.post("/clients/{idclient}/graduate")
def graduate_student(idclient: str, db: Session = Depends(get_db)):
    db_student = db.query(models.Client).filter(models.Client.idclient == idclient).first()
    if not db_student:
        raise HTTPException(status_code=404, detail="Client not found")
    
    db_student.is_graduated = True
    db_student.is_active = False # Al graduarse deja de estar activa en ciclos corrientes
    db.commit()
    #aca generamos ficha academica
    estado = "Graduada"
    Client = db.query(models.Client).filter(models.Client.idclient == idclient).first()
    if not Client:
        raise HTTPException(status_code=404, detail="Alumna no encontrada")

    # Obtener módulos aprobados directamente de la DB (Consulta fancy/eficiente)
    approved_modules = db.query(models.Modulos.Modulos).filter(
        models.Modulos.student_id == idclient,
        models.Modulos.is_approved == True
    ).all()
    approved_workshops = db.query(models.Workshop.name).join(
        models.WorkshopStudent,
        models.WorkshopStudent.workshop_id == models.Workshop.id
    ).filter(
        models.WorkshopStudent.student_id == idclient,
        models.Workshop.is_active == False
    ).all()

    lista_talleres = [w[0] for w in approved_workshops]

    # Extraer los nombres de los módulos de la lista de tuplas
    lista_aprobados = [m[0] for m in approved_modules]

    return {
        "status": "ok",
        "message": "¡Alumna graduada exitosamente!"
    }




@router.delete("/clients/{idclient}")
def deactivate_student(idclient: str, db: Session = Depends(get_db)):
    db_student = db.query(models.Client).filter(models.Client.idclient == idclient).first()
    if not db_student:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # SOFT DELETE: Solo cambiamos el estado
    db_student.is_active = False
    db.commit()
     #aca generamos ficha academica
    estado = "Dada de Baja"
    Client = db.query(models.Client).filter(models.Client.idclient == idclient).first()
    if not Client:
        raise HTTPException(status_code=404, detail="Alumna no encontrada")

    # Obtener módulos aprobados directamente de la DB (Consulta fancy/eficiente)
    approved_modules = db.query(models.Modulos.Modulos).filter(
        models.Modulos.student_id == idclient,
        models.Modulos.is_approved == True
    ).all()
    approved_workshops = db.query(models.Workshop.name).join(
    models.WorkshopStudent,
    models.WorkshopStudent.workshop_id == models.Workshop.id
    ).filter(
        models.WorkshopStudent.student_id == idclient,
        models.Workshop.is_active == False
    ).all()

    lista_talleres = [w[0] for w in approved_workshops]

    # Extraer los nombres de los módulos de la lista de tuplas
    lista_aprobados = [m[0] for m in approved_modules]

    return {
        "status": "success",
        "message": "¡Alumna dada de baja exitosamente!"
    }

@router.put("/clients/{idclient}", response_model=schemas.StudentSchema)
async def update_student(
    idclient: str, 
    student_data: str = Form(...), 
    photo: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    # PARSEO DE DATOS
    data = json.loads(student_data)
    student_obj = schemas.StudentCreate(**data)

    db_student = db.query(models.Client).filter(models.Client.idclient == idclient).first()
    if not db_student:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # --- LÓGICA DE RECEPCIÓN DE IMAGEN (EDICIÓN) ---
    photo_bytes = None
    if photo:
        # Validar tipo de archivo
        allowed_types = ["image/jpeg", "image/jpg", "image/png", "image/webp"]
        if photo.content_type not in allowed_types:
            raise HTTPException(
                status_code=400, 
                detail=f"Tipo de archivo no soportado: {photo.content_type}. Use JPG, PNG o WEBP."
            )
        await photo.seek(0)
        photo_bytes = await photo.read()
        photo_cloudinary_url = subir_imagen(photo_bytes)
        print(f"DEBUG: Foto recibida para actualización de {idclient}. Tamaño: {len(photo_bytes)} bytes. Tipo: {photo.content_type}")
    else:
        print(f"DEBUG: No se recibió foto nueva para actualización de {idclient}")
    # ------------------------------------------------

    # Update fields
    db_student.names = student_obj.names
    db_student.lastnames = student_obj.lastnames
    db_student.age = student_obj.age
    db_student.cui = student_obj.cui
    db_student.phone = student_obj.phone
    db_student.plan = student_obj.plan
    db_student.is_adult = student_obj.is_adult
    db_student.guardian1_name = student_obj.guardian1_name
    db_student.guardian1_phone = student_obj.guardian1_phone
    db_student.guardian2_name = student_obj.guardian2_name
    db_student.guardian2_phone = student_obj.guardian2_phone
    if photo_cloudinary_url:
        db_student.photo_url = photo_cloudinary_url
    
    # Asegurar que tenga hash_carnet (por si era de registros viejos)
    if not db_student.hash_carnet:
        db_student.hash_carnet = hashear_carnet(db_student.idclient)

    db.commit()

    # --- LÓGICA DE PROCESAMIENTO POST-UPDATE (Igual que en create) ---
    tmp_images_dir = "/tmp/images"
    os.makedirs(tmp_images_dir, exist_ok=True)

    try:
        # 1. HASH Y QR (Siempre se generan)
        hash_qr = db_student.hash_carnet
        qr_path = generar_qr(hash_qr)
        qr_rounded = photo_rounded(qr_path)

        # 2. PROCESAR FOTO (Solo si mandaron una nueva)
        image_rounded = None
        if photo:
            temp_photo_path = os.path.join(tmp_images_dir, f"update_temp_{db_student.idclient}.jpg")
            with open(temp_photo_path, "wb") as f:
                f.write(photo_bytes)
            
            image_rounded = photo_rounded(temp_photo_path)
            print(f"DEBUG: Nueva foto procesada para {db_student.idclient}")

        # 3. GENERAR NUEVO PDF
        pdf_path = generar_pdf(db_student.idclient, qr_rounded, image_rounded)
        
        # --- SUBIR PDF A CLOUDINARY ---
        pdf_cloudinary_url = subir_imagen(pdf_path)
        db_student.carnet_pdf_url = pdf_cloudinary_url
        db.commit()
        print(f"DEBUG: PDF actualizado y subido para {db_student.idclient}")

        # 5. LIMPIEZA
        archivos_a_borrar = [qr_path, qr_rounded]
        if photo:
            archivos_a_borrar.extend([temp_photo_path, image_rounded, pdf_path])
        
        for p in archivos_a_borrar:
            try:
                if os.path.exists(p): os.remove(p)
            except: pass

    except Exception as e:
        print(f"ERROR en procesamiento post-update: {str(e)}")

    db.refresh(db_student)
    return db_student


# Payments
    # Refrescamos para asegurar que devolvemos el estado real de la DB
    return {"status": status, "is_paid": is_paid}

@router.post("/payments/close/{student_id}")
def close_payment(student_id: str, db: Session = Depends(get_db)):
    client = db.query(models.Client).filter(models.Client.idclient == student_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    payment = db.query(models.Payment).filter(
        models.Payment.student_id == student_id,
        models.Payment.is_paid == False
    ).first()

    if not payment:
        raise HTTPException(status_code=404, detail="No pending payment found for this client")

    if not client.is_created or not payment.lastscanhour:
        raise HTTPException(status_code=400, detail="Missing entry or exit time for calculation")

    # Calcular costo según dos tarifas:
    # Por cada hora tarifa2 de la tabla tarifas
    # Fraccion superior a 15 min paga tarifa 1
    duration = payment.lastscanhour - client.is_created
    seconds = duration.total_seconds()
    hours = int(seconds // 3600)
    remaining_minutes = (seconds % 3600) / 60
    
    # Buscar tarifas en DB
    t1 = db.query(models.Tarifa).filter(models.Tarifa.nombre == "Tarifa 1").first()
    t2 = db.query(models.Tarifa).filter(models.Tarifa.nombre == "Tarifa 2").first()
    
    cost1 = t1.costo if t1 else 5.0  # Fallback
    cost2 = t2.costo if t2 else 10.0 # Fallback
    
    total_calc = hours * cost2
    if remaining_minutes > 15:
        total_calc += cost1
        
    payment.total = total_calc
    payment.is_paid = True
    client.is_paid = True
    
    db.commit()
    
    return {
        "status": "ok",
        "duration_minutes": round(seconds / 60, 2),
        "total": payment.total,
        "is_paid": True
    }

# Inventory
@router.post("/products/", response_model=schemas.ProductSchema)
def create_product(product: schemas.ProductCreate, db: Session = Depends(get_db)):
    db_product = models.Product(**product.dict())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

@router.get("/products/", response_model=list[schemas.ProductSchema])
def read_products(db: Session = Depends(get_db)):
    return db.query(models.Product).all()

@router.get("/products/{code}", response_model=schemas.ProductSchema)
def read_product_by_code(code: str, db: Session = Depends(get_db)):
    product = db.query(models.Product).filter(models.Product.code == code).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@router.put("/products/{product_id}", response_model=schemas.ProductSchema)
def update_product(product_id: int, product_data: schemas.ProductCreate, db: Session = Depends(get_db)):
    db_product = db.query(models.Product).get(product_id)
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    db_product.code = product_data.code
    db_product.description = product_data.description
    db_product.cost = product_data.cost
    db_product.units = product_data.units
    db_product.alert_threshold = product_data.alert_threshold

    db.commit()
    db.refresh(db_product)
    return db_product

# Workshops
@router.post("/workshops/", response_model=schemas.WorkshopSchema)
def create_workshop(workshop: schemas.WorkshopBase, db: Session = Depends(get_db)):
    db_workshop = models.Workshop(**workshop.dict())
    db.add(db_workshop)
    db.commit()
    db.refresh(db_workshop)
    return db_workshop

@router.get("/workshops/", response_model=list[schemas.WorkshopSchema])
def read_workshops(status: str = "active", db: Session = Depends(get_db)):
    # status: "active", "inactive", "all"
    query = db.query(models.Workshop)
    
    if status == "active":
        query = query.filter(models.Workshop.is_active == True)
    elif status == "inactive":
        query = query.filter(models.Workshop.is_active == False)
        
    return query.all()

@router.post("/workshops/{workshop_id}/culminate")
def deactivate_workshop(workshop_id: int, db: Session = Depends(get_db)):
    db_workshop = db.query(models.Workshop).get(workshop_id)
    if not db_workshop:
        raise HTTPException(status_code=404, detail="Workshop not found")
    
    db_workshop.is_active = False
    db.commit()
    return {"status": "success", "message": "Workshop culminated successfully"}

@router.get("/packages/", response_model=list[schemas.PackageSchema])
def read_packages(status: str = "active", db: Session = Depends(get_db)):
    # joinedload anidado para traer el producto y que el @property product_description funcione
    query = db.query(models.Package).options(
        joinedload(models.Package.products).joinedload(models.PackageProduct.product)
    )
    
    if status == "active":
        query = query.filter(models.Package.is_active == True)
    elif status == "inactive":
        query = query.filter(models.Package.is_active == False)
        
    return query.all()

@router.post("/packages/{package_id}/jubilar")
def deactivate_package(package_id: int, db: Session = Depends(get_db)):
    db_package = db.query(models.Package).get(package_id)
    if not db_package:
        raise HTTPException(status_code=404, detail="Package not found")
    
    db_package.is_active = False
    db.commit()
    return {"status": "success", "message": "Package retired (jubilado) successfully"}

@router.get("/stats")
async def get_stats(db: Session = Depends(get_db)):
    # Contar clientes activos (no pagados)
    active_count = db.query(models.Client).filter(models.Client.is_paid == False).count()
    
    # Obtener todos los parqueos para los gráficos
    parqueos = db.query(models.Parqueo).all()
    
    charts_data = {
        "labels": [p.nombre for p in parqueos],
        "values": []
    }
    
    for p in parqueos:
        count = db.query(models.Client).filter(
            models.Client.parqueo_id == p.id,
            models.Client.is_paid == False
        ).count()
        # Porcentaje de ocupación
        percent = (count / p.capacidad_maxima * 100) if p.capacidad_maxima > 0 else 0
        charts_data["values"].append(round(percent, 1))

    # Format datetime (Guatemala)
    now_gt = datetime.datetime.now()
    server_datetime = now_gt.strftime("%d/%m/%Y %I:%M:%S %p")

    return {
        "clients": active_count,
        "charts_data": charts_data,
        "server_datetime": server_datetime
    }

@router.get("/parqueos/", response_model=List[schemas.ParqueoSchema])
async def list_parqueos(db: Session = Depends(get_db)):
    return db.query(models.Parqueo).all()

@router.get("/tarifas/", response_model=List[schemas.TarifaSchema])
async def list_tarifas(db: Session = Depends(get_db)):
    return db.query(models.Tarifa).all()

@router.get("/inventory/alerts/")
def get_inventory_alerts(db: Session = Depends(get_db)):
    return db.query(models.Product).filter(models.Product.units <= models.Product.alert_threshold).all()

@router.post("/workshops/{workshop_id}/clients/{student_id}")
def add_student_to_workshop(workshop_id: int, student_id: str, db: Session = Depends(get_db)):
    # Check if exists
    exists = db.query(models.WorkshopStudent).filter(
        models.WorkshopStudent.workshop_id == workshop_id,
        models.WorkshopStudent.student_id == student_id
    ).first()
    if exists:
        raise HTTPException(status_code=400, detail="Esta alumna ya está inscrita en este taller")
    
    assoc = models.WorkshopStudent(workshop_id=workshop_id, student_id=student_id)
    db.add(assoc)
    db.commit()
    return {"status": "success"}

# Workshops and Packages
@router.delete("/workshops/{workshop_id}/clients/{student_id}")
def remove_student_from_workshop(workshop_id: int, student_id: str, db: Session = Depends(get_db)):
    assoc = db.query(models.WorkshopStudent).filter(
        models.WorkshopStudent.workshop_id == workshop_id,
        models.WorkshopStudent.student_id == student_id
    ).first()
    if not assoc:
        raise HTTPException(status_code=404, detail="Client not found in workshop")
    
    # Clean up snapshots for this specific Client in this workshop
    db.query(models.WorkshopStudentPackageSnapshot).filter(
        models.WorkshopStudentPackageSnapshot.workshop_id == workshop_id,
        models.WorkshopStudentPackageSnapshot.student_id == student_id
    ).delete()
    
    db.delete(assoc)
    db.commit()
    return {"status": "success"}

@router.get("/workshops/{workshop_id}/clients/", response_model=list[schemas.WorkshopStudentSchema])
def get_workshop_students(workshop_id: int, db: Session = Depends(get_db)):
    clients = db.query(models.WorkshopStudent).filter(models.WorkshopStudent.workshop_id == workshop_id).order_by(models.WorkshopStudent.id).all()
    result = []
    for s in clients:
        student_data = db.query(models.Client).filter(models.Client.idclient == s.student_id).first()
        if student_data:
            result.append({
                "student_id": s.student_id,
                "idclient": student_data.idclient,
                "names": student_data.names,
                "lastnames": student_data.lastnames,
                "photo_url": student_data.photo_url,
                "package_paid": s.package_paid,
                "workshop_paid": s.workshop_paid,
                "package_id": s.package_id
            })
    return result

@router.post("/packages/{package_id}/products/")
def add_product_to_package(package_id: int, item: schemas.PackageProductCreate, db: Session = Depends(get_db)):
    db_item = models.PackageProduct(**item.dict(), package_id=package_id)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@router.delete("/packages/{package_id}/products/{product_id}")
def remove_product_from_package(package_id: int, product_id: int, db: Session = Depends(get_db)):
    item = db.query(models.PackageProduct).filter(
        models.PackageProduct.package_id == package_id,
        models.PackageProduct.product_id == product_id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Product not found in package")
    db.delete(item)
    db.commit()
    return {"status": "success"}

@router.post("/packages/", response_model=schemas.PackageSchema)
def create_package(package: schemas.PackageCreate, db: Session = Depends(get_db)):
    db_package = models.Package(
        name=package.name,
        description=package.description,
        is_active=package.is_active
    )
    db.add(db_package)
    
    if package.products:
        for p in package.products:
            db_item = models.PackageProduct(
                product_id=p.product_id,
                quantity=p.quantity
            )
            db_package.products.append(db_item)
    
    db.commit()
    # Recargar con productos y el objeto product anidado
    return db.query(models.Package).options(
        joinedload(models.Package.products).joinedload(models.PackageProduct.product)
    ).get(db_package.id)

@router.post("/workshops/{workshop_id}/packages/{package_id}")
def link_package_to_workshop(workshop_id: int, package_id: int, db: Session = Depends(get_db)):
    exists = db.query(models.WorkshopPackage).filter(
        models.WorkshopPackage.workshop_id == workshop_id,
        models.WorkshopPackage.package_id == package_id
    ).first()
    if exists:
        return {"status": "already_linked"}
    
    link = models.WorkshopPackage(workshop_id=workshop_id, package_id=package_id)
    db.add(link)
    db.commit()
    return {"status": "success"}

@router.delete("/workshops/{workshop_id}/packages/{package_id}")
def unlink_package_from_workshop(workshop_id: int, package_id: int, db: Session = Depends(get_db)):
    # Validar si hay alumnas que ya pagaron este paquete en este taller
    paid_count = db.query(models.WorkshopStudent).filter(
        models.WorkshopStudent.workshop_id == workshop_id,
        models.WorkshopStudent.package_id == package_id,
        models.WorkshopStudent.package_paid == True
    ).count()

    if paid_count > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"No se puede desvincular: {paid_count} alumna(s) ya pagaron este paquete."
        )

    link = db.query(models.WorkshopPackage).filter(
        models.WorkshopPackage.workshop_id == workshop_id,
        models.WorkshopPackage.package_id == package_id
    ).first()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    db.delete(link)
    db.commit()
    return {"status": "success"}



@router.get("/workshops/{workshop_id}/packages/", response_model=list[schemas.PackageSchema])
def get_workshop_packages(workshop_id: int, db: Session = Depends(get_db)):
    ws = db.query(models.Workshop).get(workshop_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workshop not found")
    return ws.packages

@router.put("/packages/{package_id}", response_model=schemas.PackageSchema)
def update_package(package_id: int, package_data: schemas.PackageCreate, db: Session = Depends(get_db)):
    db_package = db.query(models.Package).get(package_id)
    if not db_package:
        raise HTTPException(status_code=404, detail="Package not found")
    
    # ---------------------------------------------------------
    # STRATEGY: Refund -> Update Definition -> Recharge
    # This ensures inventory sync without "delta" bugs
    # ---------------------------------------------------------

    # 1. FIND AFFECTED PAYMENTS (Snapshot of current state)
    affected_payments = db.query(models.WorkshopStudent).filter(
        models.WorkshopStudent.package_id == package_id,
        models.WorkshopStudent.package_paid == True
    ).all()
    
    affected_ids = []
    for row in affected_payments:
        affected_ids.append({
            "student_id": row.student_id, 
            "workshop_id": row.workshop_id
        })

    # 2. REFUND (Undo Inventory using OLD Snapshots)
    for item in affected_ids:
        snapshots = db.query(models.WorkshopStudentPackageSnapshot).filter(
            models.WorkshopStudentPackageSnapshot.workshop_id == item["workshop_id"],
            models.WorkshopStudentPackageSnapshot.student_id == item["student_id"]
        ).all()
        
        for snapshot in snapshots:
            product = db.query(models.Product).get(snapshot.product_id)
            if product:
                product.units += snapshot.quantity # Return to inventory
            db.delete(snapshot) # Remove old snapshot

    # 3. UPDATE DEFINITION
    db_package.name = package_data.name
    db_package.description = package_data.description
    
    # Limpiar productos viejos (SQLAlchemy orphan-delete se encarga)
    db_package.products = []
    
    new_package_products = [] 
    if package_data.products:
        for p in package_data.products:
            db_item = models.PackageProduct(
                product_id=p.product_id,
                quantity=p.quantity
            )
            db_package.products.append(db_item)
            new_package_products.append({"product_id": p.product_id, "quantity": p.quantity})
            
    db.flush() 

    # 4. RECHARGE (Deduct Inventory using NEW Definition)
    for item in affected_ids:
        for new_prod in new_package_products:
            product = db.query(models.Product).get(new_prod["product_id"])
            if product:
                product.units -= new_prod["quantity"]
                
                # Create NEW snapshot
                snapshot = models.WorkshopStudentPackageSnapshot(
                    workshop_id=item["workshop_id"],
                    student_id=item["student_id"],
                    product_id=new_prod["product_id"],
                    quantity=new_prod["quantity"]
                )
                db.add(snapshot)

    db.commit()
    # Devolver con productos cargados
    return db.query(models.Package).options(
        joinedload(models.Package.products).joinedload(models.PackageProduct.product)
    ).get(db_package.id)

@router.delete("/packages/{package_id}")
def delete_package(package_id: int, db: Session = Depends(get_db)):
    db_package = db.query(models.Package).get(package_id)
    if not db_package:
        raise HTTPException(status_code=404, detail="Package not found")
        
    # Check 1: Is it linked to any workshop?
    linked_workshops = db.query(models.WorkshopPackage).filter(
        models.WorkshopPackage.package_id == package_id
    ).count()
    
    if linked_workshops > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"No se puede eliminar: El paquete está vinculado a {linked_workshops} taller(es)."
        )

    # Check 2: Was it used in any Client history (PAID)?
    paid_history = db.query(models.WorkshopStudent).filter(
        models.WorkshopStudent.package_id == package_id,
        models.WorkshopStudent.package_paid == True
    ).count()
    
    if paid_history > 0:
        raise HTTPException(
            status_code=400,
            detail=f"No se puede eliminar: Hay {paid_history} registro(s) de alumnas que pagaron este paquete."
        )
    
    # Clean up unpaid history (ghost records)
    unpaid_history = db.query(models.WorkshopStudent).filter(
        models.WorkshopStudent.package_id == package_id,
        models.WorkshopStudent.package_paid == False
    ).all()
    
    for record in unpaid_history:
        record.package_id = None
        db.add(record)

    db.delete(db_package)
    db.commit()
    return {"status": "success"}

@router.delete("/workshops/{workshop_id}")
def delete_workshop(workshop_id: int, db: Session = Depends(get_db)):
    # Buscar el taller usando filter().first() en lugar de .get()
    db_ws = db.query(models.Workshop).filter(models.Workshop.id == workshop_id).first()
    
    if not db_ws:
        raise HTTPException(status_code=404, detail="Workshop not found")
    
    # Check 1: Verificar si hay alumnas inscritas
    students_count = db.query(models.WorkshopStudent).filter(
        models.WorkshopStudent.workshop_id == workshop_id
    ).count()
    
    if students_count > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"No se puede eliminar: Hay {students_count} alumnas inscritas."
        )
    
    # Check 2: Verificar si hay paquetes vinculados
    pkg_count = db.query(models.WorkshopPackage).filter(
        models.WorkshopPackage.workshop_id == workshop_id
    ).count()
    
    if pkg_count > 0:
        raise HTTPException(
            status_code=400, 
            detail="No se puede eliminar: El taller tiene un paquete vinculado. Desvincúlalo primero."
        )
    
    # Intentar eliminar
    try:
        db.delete(db_ws)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, 
            detail=f"Error al eliminar: {str(e)}"
        )
    
    return {"status": "success"}

@router.put("/workshops/{workshop_id}", response_model=schemas.WorkshopSchema)
def update_workshop(workshop_id: int, workshop_data: schemas.WorkshopBase, db: Session = Depends(get_db)):
    db_workshop = db.query(models.Workshop).filter(models.Workshop.id == workshop_id).first()
    if not db_workshop:
        raise HTTPException(status_code=404, detail="Workshop not found")
    
    db_workshop.name = workshop_data.name
    db_workshop.description = workshop_data.description
    
    db.commit()
    db.refresh(db_workshop)
    return db_workshop

@router.post("/workshop-clients/toggle/")
def toggle_workshop_payment(workshop_id: int, student_id: str, payment_type: str, db: Session = Depends(get_db)):
    assoc = db.query(models.WorkshopStudent).filter(
        models.WorkshopStudent.workshop_id == workshop_id,
        models.WorkshopStudent.student_id == student_id
    ).first()
    
    if not assoc:
        raise HTTPException(status_code=404, detail="Client not found in workshop")
    
    if payment_type == "package":
        # Si no tiene paquete asignado, intentamos tomar el del taller
        if not assoc.package_id:
            ws_pkg = db.query(models.WorkshopPackage).filter(models.WorkshopPackage.workshop_id == workshop_id).first()
            if not ws_pkg:
                raise HTTPException(status_code=400, detail="El taller no tiene un paquete vinculado.")
            assoc.package_id = ws_pkg.package_id
            db.commit() # Commit association first 
            db.refresh(assoc)

        # Descuento de bodega automático CON SNAPSHOT
        if assoc.package_id:
            db_package = db.query(models.Package).get(assoc.package_id)
            if db_package:
                if not assoc.package_paid:  # Se está marcando como pagado
                    # CRITICAL FIX: Refresh package to ensure we get the latest products definition
                    db.refresh(db_package) 
                    
                    # Guardar snapshot de las cantidades actuales
                    for pkg_prod in db_package.products:
                        product = pkg_prod.product
                        if product:
                            # Crear snapshot
                            snapshot = models.WorkshopStudentPackageSnapshot(
                                workshop_id=workshop_id,
                                student_id=student_id,
                                product_id=pkg_prod.product_id,
                                quantity=pkg_prod.quantity
                            )
                            db.add(snapshot)
                            
                            # Descontar de inventario
                            product.units -= pkg_prod.quantity
                else:  # Se está desmarcando (reembolso)
                    # Usar snapshot, NO el paquete actual
                    snapshots = db.query(models.WorkshopStudentPackageSnapshot).filter(
                        models.WorkshopStudentPackageSnapshot.workshop_id == workshop_id,
                        models.WorkshopStudentPackageSnapshot.student_id == student_id
                    ).all()
                    
                    for snapshot in snapshots:
                        product = db.query(models.Product).get(snapshot.product_id)
                        if product:
                            # Devolver la cantidad exacta que se descontó
                            product.units += snapshot.quantity
                        # Eliminar snapshot
                        db.delete(snapshot)
        
        assoc.package_paid = not assoc.package_paid
    elif payment_type == "workshop":
        assoc.workshop_paid = not assoc.workshop_paid
    
    db.commit()
    return {"status": "success", "package_paid": assoc.package_paid, "workshop_paid": assoc.workshop_paid}

@router.post("/workshop-clients/assign-package/")
def assign_package_to_student(workshop_id: int, student_id: str, package_id: Optional[int] = None, db: Session = Depends(get_db)):
    assoc = db.query(models.WorkshopStudent).filter(
        models.WorkshopStudent.workshop_id == workshop_id,
        models.WorkshopStudent.student_id == student_id
    ).first()
    if not assoc:
        raise HTTPException(status_code=404, detail="Client not found in workshop")
    
    # REEMBOLSO DE STOCK: Si ya tenía un paquete pagado, hay que devolverlo a bodega antes de cambiarlo
    # CRITICAL: Usar snapshots, NO la definición actual del paquete
    if assoc.package_paid and assoc.package_id:
        snapshots = db.query(models.WorkshopStudentPackageSnapshot).filter(
            models.WorkshopStudentPackageSnapshot.workshop_id == workshop_id,
            models.WorkshopStudentPackageSnapshot.student_id == student_id
        ).all()
        
        for snapshot in snapshots:
            product = db.query(models.Product).get(snapshot.product_id)
            if product:
                # Devolver la cantidad exacta que se descontó según el snapshot
                product.units += snapshot.quantity
            # Eliminar snapshot ya que se está cambiando de paquete
            db.delete(snapshot)
    
    # Siempre apagamos el switch de pago al cambiar de paquete para seguridad
    assoc.package_paid = False
    assoc.package_id = package_id
    db.commit()
    return {"status": "success"}



# Servir archivos estáticos (con validación para evitar crash en Vercel)
# Crucial: Apuntamos tanto /img como /assets a la carpeta física 'assets'
static_dirs = {
    "/css": os.path.join(os.path.dirname(__file__), "..", "css"),
    "/js": os.path.join(os.path.dirname(__file__), "..", "js"),
    "/assets": os.path.join(os.path.dirname(__file__), "..", "assets"),
    "/img": os.path.join(os.path.dirname(__file__), "..", "assets")
}

for mount_path, directory in static_dirs.items():
    if os.path.exists(directory):
        app.mount(mount_path, StaticFiles(directory=directory), name=mount_path[1:])
    else:
        print(f"WARNING: Carpeta {directory} no encontrada. Saltando montaje.")

# Configuración de Sesiones con Cookies Firmadas
secret_key = os.getenv("SECRET_KEY")
app.add_middleware(SessionMiddleware, secret_key=secret_key)

@app.get("/")
def read_index():
    # Usamos .. para salir de la carpeta /api y buscar en la raíz
    path = os.path.join(os.path.dirname(__file__), '..', 'index.html')
    return FileResponse(path)

@app.get("/dashboard")
def read_dashboard(request: Request):
    # Verificamos la sesión firmada
    if not request.session.get("session_user"):
        return RedirectResponse(url="/", status_code=303)
    
    # Servir el dashboard desde la raíz
    path = os.path.join(os.path.dirname(__file__), '..', 'dashboard.html')
    return FileResponse(path)

@app.get("/logout")
def logout(request: Request):
    # Limpiamos la sesión firmada
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)

ph = PasswordHasher()

# Cargar usuarios desde environment
user1 = os.getenv("USER")
hash_password = os.getenv("PASSWORD")

class LoginData(BaseModel): 
    username: str
    password: str

@router.post("/login")
def login(datos: LoginData, request: Request):
    # 1. Validar primero el usuario (¡Muy importante!)
    if datos.username != user1:
        raise HTTPException(
            status_code=401,
            detail="Usuario o contraseña incorrectos"
        )

    # Comparar password con hash
    try:
        ph.verify(hash_password, datos.password)
        
        # ✅ Login exitoso: Seteamos la sesión firmada
        request.session["session_user"] = user1
        
        return {
            "success": True,
            "mensaje": "Login exitoso",
            "username": user1
        }
        
    except VerifyMismatchError:
        # ❌ Contraseña incorrecta
        raise HTTPException(
            status_code=401,
            detail="Contraseña incorrecta"
        )
    except Exception as e:
        # Cualquier otro error (ej: hash malformado)
        print(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=401,
            detail="Error al verificar credenciales"
        )

@router.post("/assistance/finish")
def calculate_and_save_attendance(db: Session = Depends(get_db)):
    """
    Calcula el porcentaje histórico de asistencia de todas las alumnas activas
    y actualiza la columna attendance_percentage en la tabla clients.
    """
    try:
        # Obtener alumnas activas, excepto las de plan ejecutivo
        active_students = db.query(models.Client).filter(
            models.Client.is_active == True,
            models.Client.plan != "ejecutivo"
        ).all()
        updated_count = 0

        for Client in active_students:
            # Todas las asistencias registradas para esta alumna
            assistances = db.query(models.Assistance).filter(
                models.Assistance.student_id == Client.idclient
            ).all()

            total_days = len(assistances)
            
            if total_days > 0:
                # Contar días que sí asistió
                present_days = sum(1 for a in assistances if a.assistance)
                percentage = round((present_days / total_days) * 100, 1)
            else:
                percentage = 0.0

            # Guardar en base de datos
            Client.attendance_percentage = percentage
            updated_count += 1

        db.commit()
        return {"status": "success", "message": f"Porcentajes calculados para {updated_count} alumnas."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error calculando asistencia: {str(e)}")



##-----------------------------



@router.get(
    "/modules/{student_id}",
    response_model=list[schemas.ModulosSchema]
)
def get_student_modules(
    student_id: str,
    db: Session = Depends(get_db)
):
    return db.query(models.Modulos).filter(
        models.Modulos.student_id == student_id
    ).all()

@router.post("/modules/toggle")
def toggle_module(
    data: schemas.ModulosCreate,
    db: Session = Depends(get_db)
):
    record = db.query(models.Modulos).filter(
        models.Modulos.student_id == data.student_id,
        models.Modulos.Modulos == data.Modulos
    ).first()

    if not record:
        raise HTTPException(
            status_code=404,
            detail="Registro de módulo no inicializado"
        )

    record.is_approved = data.is_approved
    db.commit()

    return {
        "status": "ok",
        "student_id": data.student_id,
        "module": data.Modulos,
        "is_approved": data.is_approved
    }


@router.post("/modules/init")
def init_modules_for_students(db: Session = Depends(get_db)):
    clients = db.query(models.Client).all()

    created = 0

    for Client in clients:
        for module_name in MODULES_LIST:
            exists = db.query(models.Modulos).filter(
                models.Modulos.student_id == Client.idclient,
                models.Modulos.Modulos == module_name
            ).first()

            if not exists:
                db.add(models.Modulos(
                    student_id=Client.idclient,
                    Modulos=module_name,
                    month=0,
                    year=0,
                    is_approved=False
                ))
                created += 1

    db.commit()
    return {"status": "ok", "created": created}



@router.get("/clients-modules/", response_model=list[schemas.StudentSchema])
def read_students_with_modules(
    status: str = Query("active", enum=["active", "inactive", "all"]),
    plan: str | None = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(models.Client)

    if status == "active":
        query = query.filter(
            models.Client.is_active.is_(True),
            models.Client.is_graduated.is_(False)
        )
    elif status == "inactive":
        query = query.filter(
            or_(
                models.Client.is_active.is_(False),
                models.Client.is_graduated.is_(True)
            )
        )

    if plan:
        if plan not in {"diario", "fin_de_semana", "ejecutivo"}:
            raise HTTPException(status_code=400, detail="Plan inválido")
        query = query.filter(models.Client.plan == plan)

    return query.options(joinedload(models.Client.Modulos)).all()


@router.post("/assistance/init")
def initialize_assistance(
    plan: str,
    date: date,
    db: Session = Depends(get_db)
):
    if plan == "ejecutivo":
        raise HTTPException(status_code=400, detail="El plan ejecutivo no requiere registro de asistencia")

    # Obtener todas las alumnas activas del plan
    clients = db.query(models.Client).filter(
        models.Client.plan == plan,
        models.Client.is_active.is_(True),
        models.Client.is_graduated.is_(False)
    ).all()

    if not clients:
        raise HTTPException(status_code=404, detail="No se encontraron alumnas para este plan")

    for Client in clients:
        # Buscar si ya existe el registro para esa fecha aa
        existing = db.query(models.Assistance).filter(
            models.Assistance.student_id == Client.idclient,
            models.Assistance.date == date
        ).first()

        # Si NO existe, lo creamos como False.
        # Si YA existe, NO HACEMOS NADA (así no borramos los "Presente" ya marcados)
        if not existing:
            db.add(models.Assistance(
                student_id=Client.idclient,
                date=date,
                assistance=False
            ))

    db.commit()
    return {"status": "ok", "message": f"Asistencia iniciada para {len(clients)} alumnas"}

@router.get("/scanner/clients-attendance/")
def get_students_attendance(
    plan: str,
    date: date,
    db: Session = Depends(get_db)
):
    if plan not in ["diario", "fin_de_semana", "ejecutivo"]:
        raise HTTPException(status_code=400, detail="Plan inválido")

    # Obtener alumnas activas del plan
    clients = db.query(models.Client).filter(
        models.Client.plan == plan,
        models.Client.is_active.is_(True),
        models.Client.is_graduated.is_(False)
    ).order_by(models.Client.names).all()

    result = []
    for s in clients:
        # Verificar estado de asistencia para la fecha
        attendance_record = db.query(models.Assistance).filter(
            models.Assistance.student_id == s.idclient,
            models.Assistance.date == date
        ).first()

        is_present = attendance_record.assistance if attendance_record else False

        result.append({
            "idclient": s.idclient,
            "names": s.names,
            "lastnames": s.lastnames,
            "photo_url": s.photo_url,
            "is_present": is_present
        })

    return result


@router.post("/assistance/{identifier}")
def update_attendance(
    identifier: str,
    date: date,
    action: str = Query("take", enum=["take", "delete"]),
    db: Session = Depends(get_db)
):
    # Buscar a la alumna por su hash_carnet O por su idclient directamente (manual)
    Client = db.query(models.Client).filter(
        or_(
            models.Client.hash_carnet == identifier,
            models.Client.idclient == identifier
        )
    ).first()

    if not Client:
        raise HTTPException(
            status_code=404, 
            detail="Identificador no reconocido o vehiculo no encontrado"
        )

    if Client.is_paid:
        raise HTTPException(
            status_code=400,
            detail=f"El vehiculo {Client.idclient} ya ha realizado su pago de salida"
        )

    # En lugar de Assistance, usamos la lógica de Payment para "Salida" (Checkout)
    # Buscamos un registro de pago pendiente para este cliente
    record = db.query(models.Payment).filter(
        models.Payment.student_id == Client.idclient,
        models.Payment.is_paid == False
    ).first()

    if not record:
        # Si no existe, lo creamos (esto registra la "hora de salida" actual)
        record = models.Payment(
            student_id=Client.idclient,
            lastscanhour=datetime.datetime.now(),
            is_paid=False
        )
        db.add(record)
    else:
        # Si ya existía, actualizamos la hora de salida (último scan)
        record.lastscanhour = datetime.datetime.now()
        
    # Calcular costo según dos tarifas:
    # Por cada hora tarifa2 de la tabla tarifas
    # Fraccion superior a 15 min paga tarifa 1
    total_calc = 0.0
    if Client.is_created and record.lastscanhour:
        duration = record.lastscanhour - Client.is_created
        seconds = duration.total_seconds()
        hours = int(seconds // 3600)
        remaining_minutes = (seconds % 3600) / 60
        
        # Buscar tarifas en DB
        t1 = db.query(models.Tarifa).filter(models.Tarifa.nombre == "Tarifa 1").first()
        t2 = db.query(models.Tarifa).filter(models.Tarifa.nombre == "Tarifa 2").first()
        
        cost1 = t1.costo if t1 else 5.0  # Fallback
        cost2 = t2.costo if t2 else 10.0 # Fallback
        
        total_calc = hours * cost2
        if remaining_minutes > 15:
            total_calc += cost1
            
        record.total = total_calc
    else:
        total_calc = 0.0

    db.commit()
    
    return {
        "status": "ok",
        "student_id": Client.idclient,
        "client_name": Client.names if Client.names else "Consumidor Final",
        "client_nit": Client.nit if Client.nit else "C/F",
        "lastscanhour": record.lastscanhour.isoformat(),
        "entry_time": Client.is_created.isoformat() if Client.is_created else None,
        "duration_minutes": total_calc, 
        "total": total_calc
    }


app.include_router(router)
