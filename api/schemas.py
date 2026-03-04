from pydantic import BaseModel
from typing import List, Optional
from datetime import date, datetime



# 2. PAGOS
class PaymentBase(BaseModel):
    lastscanhour: Optional[datetime] = None
    total: float = 0.0
    is_paid: bool = False

class PaymentCreate(PaymentBase):
    Client_id: str

class PaymentSchema(PaymentBase):
    id: int
    Client_id: str

    class Config:
        from_attributes = True

# 3. PARQUEOS Y TARIFAS
class ParqueoBase(BaseModel):
    nombre: str
    capacidad_maxima: int

class ParqueoSchema(ParqueoBase):
    id: int

    class Config:
        from_attributes = True
class ParqueoCreate(ParqueoBase):
    pass

class TarifaBase(BaseModel):
    nombre: str
    costo: float

class TarifaSchema(TarifaBase):
    id: int

    class Config:
        from_attributes = True
        
class TarifaCreate(TarifaBase):
    pass

# 4. ESTUDIANTES (Clientes)
class ClientBase(BaseModel):
    names: Optional[str] = None
    lastnames: Optional[str] = None
    nit: Optional[str] = None
    phone: Optional[str] = None
    parqueo_id: Optional[int] = None

class ClientCreate(ClientBase):
    pass

class ClientSchema(ClientBase):
    idclient: str
    is_created: Optional[datetime] = None
    is_paid: bool = False
    is_active: bool = True
    parqueo: Optional[ParqueoSchema] = None

    class Config:
        from_attributes = True


# 5. EMPLEADOS
class EmpleadoCreate(BaseModel):
    nombres: str
    apellidos: str
    cui: str
    numero: str
    edad: int
    rol: str
    user: str
    password: str

class EmpleadoSchema(BaseModel):
    id: int
    nombres: str
    apellidos: str
    cui: str
    numero: str
    edad: int
    rol: str
    user: str

    class Config:
        from_attributes = True
