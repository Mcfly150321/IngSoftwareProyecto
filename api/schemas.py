from pydantic import BaseModel
from typing import List, Optional
from datetime import date, datetime



# 2. PAGOS
class PaymentBase(BaseModel):
    lastscanhour: Optional[datetime] = None
    total: float = 0.0
    is_paid: bool = False

class PaymentCreate(PaymentBase):
    student_id: str

class PaymentSchema(PaymentBase):
    id: int
    student_id: str

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

class TarifaBase(BaseModel):
    nombre: str
    costo: float

class TarifaSchema(TarifaBase):
    id: int

    class Config:
        from_attributes = True

# 4. ESTUDIANTES (Clientes)
class StudentBase(BaseModel):
    names: Optional[str] = None
    lastnames: Optional[str] = None
    nit: Optional[str] = None
    phone: Optional[str] = None
    parqueo_id: Optional[int] = None

class StudentCreate(StudentBase):
    pass

class StudentSchema(StudentBase):
    idclient: str
    is_created: Optional[datetime] = None
    is_paid: bool = False
    parqueo: Optional[ParqueoSchema] = None

    class Config:
        from_attributes = True

