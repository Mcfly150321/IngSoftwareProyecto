from pydantic import BaseModel
from typing import List, Optional
from datetime import date, datetime

# 1. MODULOS (Definidos primero para que otros puedan usarlos)
class ModulosBase(BaseModel):
    month: int
    year: int
    Modulos: str
    is_approved: bool = False

class ModulosCreate(ModulosBase):
    student_id: str

class ModulosSchema(ModulosBase):
    id: int
    student_id: str

    class Config:
        from_attributes = True

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

# 4. INVENTARIO Y PRODUCTOS
class ProductBase(BaseModel):
    code: str
    description: str
    cost: float
    units: int
    alert_threshold: int = 5

class ProductCreate(ProductBase):
    pass

class ProductSchema(ProductBase):
    id: int

    class Config:
        from_attributes = True

# 5. PAQUETES Y TALLERES
class PackageProductBase(BaseModel):
    product_id: int
    quantity: int

class PackageProductCreate(PackageProductBase):
    pass

class PackageProductSchema(PackageProductBase):
    id: int
    product_description: Optional[str] = None

    class Config:
        from_attributes = True

class WorkshopBase(BaseModel):
    name: str
    description: str
    is_active: bool = True

class WorkshopCreate(WorkshopBase):
    pass

class WorkshopSchema(WorkshopBase):
    id: int
    is_active: bool

    class Config:
        from_attributes = True

class PackageBase(BaseModel):
    name: str
    description: str
    is_active: bool = True

class PackageCreate(PackageBase):
    products: Optional[List[PackageProductCreate]] = []

class PackageSchema(PackageBase):
    id: int
    products: List[PackageProductSchema] = []

    class Config:
        from_attributes = True

class WorkshopStudentSchema(BaseModel):
    student_id: str
    idclient: str 
    names: str
    lastnames: str
    photo_url: Optional[str] = None
    is_active: bool = True
    workshop_paid: bool
    package_paid: bool
    package_id: Optional[int] = None

    class Config:
        from_attributes = True

# 6. OTROS (Búsqueda y Asistencia)

class AssistanceBase(BaseModel):
    student_id: str
    date: date
    assistance: bool

class AssistanceCreate(AssistanceBase):
    pass

class AssistanceSchema(AssistanceBase):
    id: int

    class Config:
        from_attributes = True