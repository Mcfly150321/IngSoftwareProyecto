from fastapi import FastAPI, Depends, HTTPException, Query, APIRouter, Request
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
import urllib.parse
from .pdf import generar_pdf
from .qr import generar_qr
from .border import photo_rounded
from .hash import hashear_carnet
from .imagenticket import generar_imgticket
from .cloudinarylogic import subir_imagen

def get_now_gt():
    """Retorna la hora actual en UTC-6 (Guatemala) como datetime ingenua."""
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-6))).replace(tzinfo=None)


import webbrowser


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

# Dependency to get the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/ping")
def ping():
    return {"status": "ok"}


@router.post("/clients/")
async def create_student(
    client: schemas.StudentCreate,
    db: Session = Depends(get_db)
):
    # 1. Inicializamos las variables para evitar UnboundLocalError
    pdf_cloudinary_url = None
    url = ""

    db_student = models.Client(
        names=client.names,
        lastnames=client.lastnames,
        nit=client.nit,
        phone=client.phone,
        parqueo_id=client.parqueo_id,
        is_created=get_now_gt()
    )
    db_student.idclient = f"2026{str(random.randint(100000, 999999))}"
    db_student.registration_date = get_now_gt().strftime("%Y-%m")
    db_student.is_created = get_now_gt()
    
    db.add(db_student)
    db.commit()
    db.refresh(db_student)

    # --- LÓGICA DE PROCESAMIENTO ---
    tmp_images_dir = "/tmp/images"
    os.makedirs(tmp_images_dir, exist_ok=True)

    try:
        qr_path = generar_qr(db_student.idclient)
        img_path = generar_imgticket(db_student.idclient, qr_path)
        img_cloudinary_url = subir_imagen(img_path)
        db_student.carnet_img_url = img_cloudinary_url

        # MENSAJE DE WHATSAPP (Aquí ya no fallará porque importamos urllib)
        nombremensaje = client.names.strip().split()[0]
        waMessage = f"Hola, {nombremensaje} \n Aca tienes tu Ticket de Parqueo:\n{img_cloudinary_url}"
        mensaje_limpio = urllib.parse.quote(waMessage)
        url = f"https://wa.me/502{client.phone}?text={mensaje_limpio}"
        
        db.commit()

        # ... (Tu lógica de módulos se mantiene igual) ...
        for module_name in MODULES_LIST:
            # ... tu código de módulos ...
            pass

        # Limpieza de archivos
        for p in [qr_path, img_path]:
            try:
                if os.path.exists(p): os.remove(p)
            except: pass

    except Exception as e:
        print(f"ERROR en procesamiento post-registro: {str(e)}")
    
    # El return ahora siempre encontrará las variables, aunque estén vacías si falló el try
    return {
        "idclient": db_student.idclient,
        "names": db_student.names,
        "lastnames": db_student.lastnames,
        "carnet_pdf_url": pdf_cloudinary_url,
        "url": url 
    }



@router.get("/clients/{idclient}/idclient-url")
def get_carnet_url(idclient: str, db: Session = Depends(get_db)):
    Client = db.query(models.Client.carnet_pdf_url).filter(models.Client.idclient == idclient).first()
    if not Client:
        raise HTTPException(status_code=404, detail="Client not found")
    return {"carnet_pdf_url": Client[0]}



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
    # Por cada 5 minutos cobramos tarifa2
    # Fraccion superior a 2 min paga tarifa 1 adicional
    duration = payment.lastscanhour - client.is_created
    seconds = int(duration.total_seconds())
    
    # Ciclo de 5 minutos (300 segundos)
    ciclos_5min = seconds // 300
    minutos_restantes = (seconds % 300) / 60
    
    # Buscar tarifas en DB
    t1 = db.query(models.Tarifa).filter(models.Tarifa.nombre == "Tarifa1").first()
    t2 = db.query(models.Tarifa).filter(models.Tarifa.nombre == "Tarifa2").first()
    
    cost1 = t1.costo if t1 else 5.0  # Fallback
    cost2 = t2.costo if t2 else 10.0 # Fallback
    
    total_calc = ciclos_5min * cost2
    if minutos_restantes > 2:
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
    now_gt = get_now_gt()
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
admin_user = os.getenv("USER")
admin_password_hash = os.getenv("PASSWORD")

class LoginData(BaseModel): 
    username: str
    password: str

@router.post("/login")
def login(datos: LoginData, request: Request):
    # Validar que las variables de entorno estén configuradas
    if not admin_user or not admin_password_hash:
        print("ERROR: USER o PASSWORD no configurados en las variables de entorno.")
        raise HTTPException(
            status_code=500,
            detail="Error de configuración del servidor: faltan credenciales."
        )

    # 1. Validar primero el usuario (¡Muy importante!)
    if datos.username != admin_user:
        raise HTTPException(
            status_code=401,
            detail="Usuario o contraseña incorrectos"
        )

    # Comparar password con hash
    try:
        # Log para depuración (¡No imprimir el hash completo ni el password en producción!)
        print(f"DEBUG: Intentando login para usuario: {datos.username}")
        if not admin_password_hash:
            print("DEBUG: admin_password_hash es None o vacío")
        else:
            print(f"DEBUG: admin_password_hash cargado (empieza con {admin_password_hash[:10]}...)")
            
        ph.verify(admin_password_hash, datos.password)
        
        # ✅ Login exitoso: Seteamos la sesión firmada
        request.session["session_user"] = admin_user
        
        return {
            "success": True,
            "mensaje": "Login exitoso",
            "username": admin_user
        }
        
    except VerifyMismatchError:
        # ❌ Contraseña incorrecta
        raise HTTPException(
            status_code=401,
            detail="Contraseña incorrecta"
        )
    except Exception as e:
        # Cualquier otro error (ej: hash malformado)
        import traceback
        error_trace = traceback.format_exc()
        print(f"Login error detail: {str(e)}")
        print(f"Full traceback: {error_trace}")
        raise HTTPException(
            status_code=401,
            detail=f"Error al verificar credenciales: {str(e)}"
        )
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
            # Photo removed
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
    # Buscar al cliente por su idclient directamente
    Client = db.query(models.Client).filter(
        models.Client.idclient == identifier
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
            lastscanhour=get_now_gt(),
            is_paid=False
        )
        db.add(record)
    else:
        # Si ya existía, actualizamos la hora de salida (último scan)
        record.lastscanhour = get_now_gt()
        
    # Calcular costo según dos tarifas:
    # Por cada 5 minutos cobramos tarifa2
    # Fraccion superior a 2 min paga tarifa 1 adicional
    total_calc = 0.0
    if Client.is_created and record.lastscanhour:
        duration = record.lastscanhour - Client.is_created
        seconds = int(duration.total_seconds())
        
        # Ciclo de 5 minutos (300 segundos)
        ciclos_5min = seconds // 300
        minutos_restantes = (seconds % 300) / 60
        
        # Buscar tarifas en DB
        t1 = db.query(models.Tarifa).filter(models.Tarifa.nombre == "Tarifa1").first()
        t2 = db.query(models.Tarifa).filter(models.Tarifa.nombre == "Tarifa2").first()
        
        cost1 = t1.costo if t1 else 5.0  # Fallback
        cost2 = t2.costo if t2 else 10.0 # Fallback
        
        total_calc = ciclos_5min * cost2
        if minutos_restantes > 2:
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
