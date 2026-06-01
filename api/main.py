import os
import datetime
import urllib.parse

from fastapi import FastAPI, Depends, HTTPException, Request, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from pydantic import BaseModel
from typing import List

from . import database, schemas, models
from .database import SessionLocal, init_db
from .seqcode import generar_codigo_verificacion
from .idticket import generate_idticket
from .qr import generar_qr
from .imagenticket import generar_imgticket
from .cloudinarylogic import subir_imagen


# ── Helpers ──────────────────────────────────────────────────────────────────

def get_now_gt() -> datetime.datetime:
    """Hora actual en UTC-6 (Guatemala) sin tzinfo."""
    return datetime.datetime.now(
        datetime.timezone(datetime.timedelta(hours=-6))
    ).replace(tzinfo=None)


ph = PasswordHasher()


# ── App & Middleware ──────────────────────────────────────────────────────────

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

secret_key = os.getenv("SECRET_KEY", "fallback-dev-secret")
app.add_middleware(SessionMiddleware, secret_key=secret_key)

# Archivos estáticos
static_dirs = {
    "/css":    os.path.join(os.path.dirname(__file__), "..", "css"),
    "/js":     os.path.join(os.path.dirname(__file__), "..", "js"),
    "/assets": os.path.join(os.path.dirname(__file__), "..", "assets"),
    "/img":    os.path.join(os.path.dirname(__file__), "..", "assets"),
}
for mount_path, directory in static_dirs.items():
    if os.path.exists(directory):
        app.mount(mount_path, StaticFiles(directory=directory), name=mount_path[1:])
    else:
        print(f"WARNING: Carpeta {directory} no encontrada. Saltando montaje.")

# Inicializar DB y seed
init_db()

router = APIRouter(prefix="/api")


# ── DB Dependency ─────────────────────────────────────────────────────────────

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ═════════════════════════════════════════════════════════════════════════════
# PÁGINAS
# ═════════════════════════════════════════════════════════════════════════════

@app.get("/")
def read_index():
    path = os.path.join(os.path.dirname(__file__), "..", "index.html")
    return FileResponse(path)


@app.get("/dashboard")
def read_dashboard(request: Request):
    if not request.session.get("session_user"):
        return RedirectResponse(url="/", status_code=303)
    path = os.path.join(os.path.dirname(__file__), "..", "dashboard.html")
    return FileResponse(path)


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)


# ═════════════════════════════════════════════════════════════════════════════
# HEALTH
# ═════════════════════════════════════════════════════════════════════════════

@router.get("/ping")
def ping():
    return {"status": "ok"}


# ═════════════════════════════════════════════════════════════════════════════
# AUTH
# ═════════════════════════════════════════════════════════════════════════════

class LoginData(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(datos: LoginData, request: Request, db: Session = Depends(get_db)):
    # Buscar credencial por username
    cred = db.query(models.Credential).filter(
        models.Credential.user == datos.username
    ).first()

    if not cred:
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")

    try:
        ph.verify(cred.passwd, datos.password)
    except VerifyMismatchError:
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Error al verificar credenciales: {e}")

    empleado = cred.empleado
    rol_nombre = empleado.rol_rel.rol if empleado.rol_rel else ""

    request.session["session_user"] = cred.user
    return {
        "success": True,
        "mensaje": "Login exitoso",
        "username": cred.user,
        "first_name": empleado.nombres.strip().split()[0],
        "rol": rol_nombre,
    }


# ═════════════════════════════════════════════════════════════════════════════
# DASHBOARD STATS
# ═════════════════════════════════════════════════════════════════════════════

@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    # Vehículos activos = tienen entrada pero no salida (última entrada sin salida posterior)
    # Simplificado: contamos clients que tienen al menos una entrada y ninguna salida posterior
    from sqlalchemy import func

    # Subquery: clients con al menos una entrada
    entradas = (
        db.query(models.EntradaSalida.client_id)
        .filter(models.EntradaSalida.tipo == "entrada")
        .subquery()
    )
    salidas = (
        db.query(models.EntradaSalida.client_id)
        .filter(models.EntradaSalida.tipo == "salida")
        .subquery()
    )
    # Activos = tienen entrada pero no están en salidas
    active_ids = (
        db.query(models.Client.client_id)
        .filter(models.Client.client_id.in_(
            db.query(entradas.c.client_id)
        ))
        .filter(models.Client.client_id.notin_(
            db.query(salidas.c.client_id)
        ))
        .all()
    )
    active_count = len(active_ids)

    # Parqueos para gráficos (usamos capacidad vs activos por parqueo — no hay FK de parqueo en client ahora)
    parqueos = db.query(models.Parqueo).all()
    charts_data = {
        "labels": [p.nombre for p in parqueos],
        "values": [0] * len(parqueos),  # sin FK a parqueo en client, se deja para futura expansión
    }

    now_gt = get_now_gt()
    return {
        "clients": active_count,
        "charts_data": charts_data,
        "server_datetime": now_gt.strftime("%d/%m/%Y %I:%M:%S %p"),
    }


# ═════════════════════════════════════════════════════════════════════════════
# PARQUEOS
# ═════════════════════════════════════════════════════════════════════════════

@router.get("/parqueos/", response_model=List[schemas.ParqueoSchema])
def list_parqueos(db: Session = Depends(get_db)):
    return db.query(models.Parqueo).all()


@router.post("/parqueos/", response_model=schemas.ParqueoSchema)
def create_parqueo(parqueo: schemas.ParqueoCreate, db: Session = Depends(get_db)):
    db_p = models.Parqueo(nombre=parqueo.nombre, capacidad=parqueo.capacidad)
    db.add(db_p)
    db.commit()
    db.refresh(db_p)
    return db_p


@router.put("/parqueos/{parqueo_id}", response_model=schemas.ParqueoSchema)
def update_parqueo(parqueo_id: int, parqueo: schemas.ParqueoCreate, db: Session = Depends(get_db)):
    db_p = db.query(models.Parqueo).filter(models.Parqueo.id == parqueo_id).first()
    if not db_p:
        raise HTTPException(status_code=404, detail="Parqueo no encontrado")
    db_p.nombre = parqueo.nombre
    db_p.capacidad = parqueo.capacidad
    db.commit()
    db.refresh(db_p)
    return db_p


# ═════════════════════════════════════════════════════════════════════════════
# TIPOS DE VEHÍCULO
# ═════════════════════════════════════════════════════════════════════════════

@router.get("/tipos-vehiculo/", response_model=List[schemas.TipoVehiculoSchema])
def list_tipos_vehiculo(db: Session = Depends(get_db)):
    return db.query(models.TipoVehiculo).all()


# ═════════════════════════════════════════════════════════════════════════════
# UNIDADES DE TIEMPO
# ═════════════════════════════════════════════════════════════════════════════

@router.get("/unidades-tiempo/", response_model=List[schemas.UnidadTiempoSchema])
def list_unidades_tiempo(db: Session = Depends(get_db)):
    return db.query(models.UnidadTiempo).all()


# ═════════════════════════════════════════════════════════════════════════════
# TARIFAS
# ═════════════════════════════════════════════════════════════════════════════

@router.get("/tarifas/", response_model=List[schemas.TarifaSchema])
def list_tarifas(db: Session = Depends(get_db)):
    return db.query(models.Tarifa).all()


@router.post("/tarifas/", response_model=schemas.TarifaSchema)
def create_tarifa(tarifa: schemas.TarifaCreate, db: Session = Depends(get_db)):
    db_t = models.Tarifa(
        tipo_vehiculo_id=tarifa.tipo_vehiculo_id,
        unidad_tiempo_id=tarifa.unidad_tiempo_id,
        costo=tarifa.costo,
    )
    db.add(db_t)
    db.commit()
    db.refresh(db_t)
    return db_t


@router.put("/tarifas/{tarifa_id}", response_model=schemas.TarifaSchema)
def update_tarifa(tarifa_id: int, tarifa: schemas.TarifaCreate, db: Session = Depends(get_db)):
    db_t = db.query(models.Tarifa).filter(models.Tarifa.id == tarifa_id).first()
    if not db_t:
        raise HTTPException(status_code=404, detail="Tarifa no encontrada")
    db_t.tipo_vehiculo_id = tarifa.tipo_vehiculo_id
    db_t.unidad_tiempo_id = tarifa.unidad_tiempo_id
    db_t.costo = tarifa.costo
    db.commit()
    db.refresh(db_t)
    return db_t


# ═════════════════════════════════════════════════════════════════════════════
# EMPLEADOS
# ═════════════════════════════════════════════════════════════════════════════

@router.get("/roles/", response_model=List[schemas.RolSchema])
def list_roles(db: Session = Depends(get_db)):
    return db.query(models.Rol).all()


@router.get("/empleados/", response_model=List[schemas.EmpleadoSchema])
def list_empleados(db: Session = Depends(get_db)):
    return db.query(models.Empleado).all()


@router.post("/empleados/", response_model=schemas.EmpleadoSchema)
def create_empleado(empleado: schemas.EmpleadoCreate, db: Session = Depends(get_db)):
    # Verificar unicidad de CUI y user
    if db.query(models.Empleado).filter(models.Empleado.cui == empleado.cui).first():
        raise HTTPException(status_code=400, detail="El CUI ya existe en el sistema")
    if db.query(models.Credential).filter(models.Credential.user == empleado.user).first():
        raise HTTPException(status_code=400, detail="El usuario ya existe en el sistema")

    db_emp = models.Empleado(
        nombres=empleado.nombres,
        apellidos=empleado.apellidos,
        cui=empleado.cui,
        edad=empleado.edad,
        rol_id=empleado.rol_id,
    )
    db.add(db_emp)
    db.flush()

    cred = models.Credential(
        empleado_id=db_emp.id,
        user=empleado.user,
        passwd=ph.hash(empleado.password),
    )
    db.add(cred)
    db.commit()
    db.refresh(db_emp)
    return db_emp


# ═════════════════════════════════════════════════════════════════════════════
# ENDPOINTS AUTÓMATA
# Prefijo: /api/automata/
# Consumidos desde sistemas externos (máquinas, kioscos, etc.)
# Solo devuelven ok o error, excepto el primero que también devuelve seqcode/client_id
# ═════════════════════════════════════════════════════════════════════════════

automata = APIRouter(prefix="/api/automata")


@automata.post("/client-request", response_model=schemas.ClientRequestResponse)
def create_client_request(db: Session = Depends(get_db)):
    """
    Crea una solicitud de cliente.
    No recibe body. Genera seqcode y client_id.
    Devuelve: { seqcode, client_id } o error.
    """
    seqcode = generar_codigo_verificacion()
    client_id = generate_idticket(db)

    req = models.ClientRequest(
        security_code=seqcode,
        client_id=client_id,
    )
    db.add(req)
    db.commit()
    db.refresh(req)

    return schemas.ClientRequestResponse(seqcode=seqcode, client_id=client_id)


@automata.post("/client")
def create_client(data: schemas.ClientCreate, db: Session = Depends(get_db)):
    """
    Registra un cliente.
    Valida que seqcode + client_id existan y hagan match en client_requests.
    Devuelve: ok o error.
    """
    req = db.query(models.ClientRequest).filter(
        models.ClientRequest.client_id == data.client_id,
        models.ClientRequest.security_code == data.seqcode,
    ).first()

    if not req:
        raise HTTPException(
            status_code=400,
            detail="seqcode y client_id no coinciden con ninguna solicitud registrada"
        )

    # Verificar que no exista ya un cliente con este client_id
    if db.query(models.Client).filter(models.Client.client_id == data.client_id).first():
        raise HTTPException(status_code=400, detail="Este client_id ya tiene un cliente registrado")

    db_client = models.Client(
        nombres=data.nombres,
        apellidos=data.apellidos,
        dpi=data.dpi,
        client_id=data.client_id,
        tipo_vehiculo_id=data.tipo_vehiculo_id,
        placa=data.placa,
    )
    db.add(db_client)
    db.commit()

    return {"status": "ok"}


@automata.post("/entrada-salida/{client_id}")
def create_entrada_salida(client_id: str, data: schemas.EntradaSalidaCreate, db: Session = Depends(get_db)):
    """
    Registra una entrada o salida.
    El tipo lo envía el sistema ("entrada" o "salida").
    La hora la pone el sistema.
    Devuelve: ok o error.
    """
    if data.tipo not in ("entrada", "salida"):
        raise HTTPException(status_code=400, detail="tipo debe ser 'entrada' o 'salida'")

    client = db.query(models.Client).filter(
        models.Client.client_id == client_id
    ).first()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    registro = models.EntradaSalida(
        client_id=client_id,
        fecha_hora=get_now_gt(),
        tipo=data.tipo,
    )
    db.add(registro)
    db.commit()

    return {"status": "ok", "tipo": data.tipo}


def _calcular_monto(client_id: str, db: Session):
    client = db.query(models.Client).filter(models.Client.client_id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    ultima_entrada = (
        db.query(models.EntradaSalida)
        .filter(models.EntradaSalida.client_id == client_id, models.EntradaSalida.tipo == "entrada")
        .order_by(models.EntradaSalida.fecha_hora.desc())
        .first()
    )

    if not ultima_entrada:
        raise HTTPException(status_code=400, detail="El cliente no tiene ninguna entrada registrada")
    
    ahora = get_now_gt()
    diferencia = ahora - ultima_entrada.fecha_hora
    minutos_totales = int(diferencia.total_seconds() / 60)
    
    mapa_tiempos = {"Fraccion": 15, "Hora": 60, "Dia": 1440, "Mes": 43200}
    tarifas = db.query(models.Tarifa).filter(models.Tarifa.tipo_vehiculo_id == client.tipo_vehiculo_id).all()
    
    total_cobro = 0.0
    if tarifas:
        tarifas_min = []
        for t in tarifas:
            mins = mapa_tiempos.get(t.unidad_tiempo.nombre, 60)
            tarifas_min.append((mins, t.costo))
        
        tarifas_min.sort(key=lambda x: x[0], reverse=True)
        
        minutos_restantes = minutos_totales
        for mins, costo in tarifas_min:
            if mins > 0:
                ciclos = minutos_restantes // mins
                total_cobro += ciclos * float(costo)
                minutos_restantes = minutos_restantes % mins
                
        if minutos_restantes > 0 and tarifas_min:
            tarifa_min = min(tarifas_min, key=lambda x: x[0])
            total_cobro += float(tarifa_min[1])

    return client, ultima_entrada, minutos_totales, total_cobro

@automata.get("/calcular-cobro/{client_id}")
def calcular_cobro(client_id: str, db: Session = Depends(get_db)):
    """
    Calcula el cobro buscando la última 'entrada' y generando un (ahora - tiempo_ultima_entrada).
    Calcula en base a las tarifas registradas para el tipo_vehiculo del cliente.
    """
    client, ultima_entrada, minutos_totales, total_cobro = _calcular_monto(client_id, db)

    return {
        "status": "ok",
        "client_id": client.client_id,
        "nombres": client.nombres,
        "ultima_entrada": ultima_entrada.fecha_hora,
        "minutos_totales": minutos_totales,
        "total_cobrar": round(total_cobro, 2)
    }

@automata.post("/cobrar/{client_id}")
def cobrar_automatico(client_id: str, db: Session = Depends(get_db)):
    """
    Calcula el cobro automáticamente y registra la transacción (tipo 'cobro') en un solo paso.
    """
    client, ultima_entrada, minutos_totales, total_cobro = _calcular_monto(client_id, db)

    tx = models.Transaccion(
        client_id=client.client_id,
        monto=total_cobro,
        tipo_transaccion="cobro",
        fecha_hora=get_now_gt(),
    )
    db.add(tx)
    db.commit()

    return {
        "status": "ok",
        "client_id": client.client_id,
        "nombres": client.nombres,
        "monto_cobrado": round(total_cobro, 2)
    }


@automata.post("/transaccion/{client_id}")
def create_transaccion(client_id: str, data: schemas.TransaccionCreate, db: Session = Depends(get_db)):
    """
    Registra una transacción (recarga o cobro).
    Devuelve: ok o error.
    """
    if data.tipo_transaccion not in ("recarga", "cobro"):
        raise HTTPException(
            status_code=400,
            detail="tipo_transaccion debe ser 'recarga' o 'cobro'"
        )

    client = db.query(models.Client).filter(
        models.Client.client_id == client_id
    ).first()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    tx = models.Transaccion(
        client_id=client_id,
        monto=data.monto,
        tipo_transaccion=data.tipo_transaccion,
        fecha_hora=get_now_gt(),
    )
    db.add(tx)
    db.commit()

    return {"status": "ok"}


# ═════════════════════════════════════════════════════════════════════════════
# CLIENTES (consultas desde el dashboard)
# ═════════════════════════════════════════════════════════════════════════════

@router.get("/clients/", response_model=List[schemas.ClientSchema])
def list_clients(db: Session = Depends(get_db)):
    return db.query(models.Client).all()


@router.get("/clients/{client_id}", response_model=schemas.ClientSchema)
def get_client(client_id: str, db: Session = Depends(get_db)):
    client = db.query(models.Client).filter(models.Client.client_id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return client


# ═════════════════════════════════════════════════════════════════════════════
# ENTRADAS / SALIDAS (consultas desde el dashboard)
# ═════════════════════════════════════════════════════════════════════════════

@router.get("/entradas-salidas/", response_model=List[schemas.EntradaSalidaSchema])
def list_entradas_salidas(db: Session = Depends(get_db)):
    return (
        db.query(models.EntradaSalida)
        .order_by(models.EntradaSalida.fecha_hora.desc())
        .limit(200)
        .all()
    )


# ═════════════════════════════════════════════════════════════════════════════
# TRANSACCIONES (consultas desde el dashboard)
# ═════════════════════════════════════════════════════════════════════════════

@router.get("/transacciones/", response_model=List[schemas.TransaccionSchema])
def list_transacciones(db: Session = Depends(get_db)):
    return (
        db.query(models.Transaccion)
        .order_by(models.Transaccion.fecha_hora.desc())
        .limit(200)
        .all()
    )


# ═════════════════════════════════════════════════════════════════════════════
# Registrar routers
# ═════════════════════════════════════════════════════════════════════════════

app.include_router(router)
app.include_router(automata)
