from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from decimal import Decimal


# ─────────────────────────────────────────────
# A. PARQUEOS Y RECURSOS
# ─────────────────────────────────────────────

class ParqueoBase(BaseModel):
    nombre: str
    capacidad: int

class ParqueoCreate(ParqueoBase):
    pass

class ParqueoSchema(ParqueoBase):
    id: int

    class Config:
        from_attributes = True


class TipoVehiculoSchema(BaseModel):
    id: int
    nombre: str

    class Config:
        from_attributes = True


class UnidadTiempoSchema(BaseModel):
    id: int
    nombre: str

    class Config:
        from_attributes = True


class TarifaBase(BaseModel):
    tipo_vehiculo_id: int
    unidad_tiempo_id: int
    costo: Decimal

class TarifaCreate(TarifaBase):
    pass

class TarifaSchema(TarifaBase):
    id: int
    tipo_vehiculo: Optional[TipoVehiculoSchema] = None
    unidad_tiempo: Optional[UnidadTiempoSchema] = None

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────
# B. PERSONAL Y SEGURIDAD
# ─────────────────────────────────────────────

class RolSchema(BaseModel):
    id: int
    rol: str

    class Config:
        from_attributes = True


class EmpleadoCreate(BaseModel):
    nombres: str
    apellidos: str
    cui: str
    edad: int
    rol_id: int
    # Credenciales
    user: str
    password: str

class EmpleadoSchema(BaseModel):
    id: int
    nombres: str
    apellidos: str
    cui: str
    edad: int
    rol_id: int

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────
# C. OPERACIONES
# ─────────────────────────────────────────────

class ClientRequestResponse(BaseModel):
    """Respuesta al crear una solicitud de cliente (endpoint autómata)."""
    seqcode: str
    client_id: str


class ClientCreate(BaseModel):
    """Datos para registrar un cliente desde el autómata. Requiere seqcode + client_id para validar contra client_requests."""
    seqcode: str
    client_id: str
    nombres: str
    apellidos: str
    dpi: str
    placa: str
    tipo_vehiculo_id: Optional[int] = 1  # default Carro


class ClientCreateDashboard(BaseModel):
    """Datos para registrar un cliente desde el dashboard. El backend genera seqcode y client_id."""
    nombres: str
    apellidos: str
    dpi: str
    placa: str
    tipo_vehiculo_id: Optional[int] = 1  # default Carro
    numero: Optional[int] = None

class ClientSchema(BaseModel):
    id: int
    nombres: str
    apellidos: str
    dpi: str
    client_id: str
    tipo_vehiculo_id: int
    placa: str
    numero: Optional[int] = None
    ticket_url: Optional[str] = None

    class Config:
        from_attributes = True


class EntradaSalidaCreate(BaseModel):
    """Endpoint autómata — necesita tipo, la hora la pone el sistema. El client_id va en la URL."""
    tipo: str


class EntradaSalidaDashboard(BaseModel):
    """Endpoint dashboard — client_id va en el body junto al tipo."""
    client_id: str
    tipo: str


class EntradaSalidaSchema(BaseModel):
    id: int
    client_id: str
    fecha_hora: datetime
    tipo: str

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────
# D. FINANCIERO
# ─────────────────────────────────────────────

class TransaccionCreate(BaseModel):
    """Endpoint autómata — lleva tipo y monto. El client_id va en la URL."""
    tipo_transaccion: str   # "recarga" | "cobro"
    monto: Decimal

class TransaccionSchema(BaseModel):
    id: int
    client_id: str
    monto: Decimal
    tipo_transaccion: str
    fecha_hora: datetime

    class Config:
        from_attributes = True
