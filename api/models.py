from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Float, UniqueConstraint, Date, DateTime, func
from sqlalchemy.orm import relationship
from .database import Base

class Client(Base):
    __tablename__ = "clients"

    idclient = Column(String, primary_key=True, index=True)
    names = Column(String)
    lastnames = Column(String)
    nit = Column(String, unique=True, index=True)
    age = Column(Integer, nullable=True)
    cui = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    plan = Column(String, default="diario")
    is_adult = Column(Boolean, default=True)
    guardian1_name = Column(String, nullable=True)
    guardian1_phone = Column(String, nullable=True)
    guardian2_name = Column(String, nullable=True)
    guardian2_phone = Column(String, nullable=True)
    attendance_percentage = Column(Float, default=0.0)
    
    is_created = Column(DateTime, default=func.now())
    is_paid = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    is_graduated = Column(Boolean, default=False)
    
    parqueo_id = Column(Integer, ForeignKey("parqueos.id"))
    
    photo_url = Column(String, nullable=True)
    hash_carnet = Column(String, index=True)
    registration_date = Column(String, nullable=True)
    carnet_pdf_url = Column(String, nullable=True)
    
    parqueo = relationship("Parqueo", back_populates="clients")
    assistances = relationship(
        "Assistance",
        back_populates="Client",
        cascade="all, delete-orphan"
    )
    payments = relationship("Payment", back_populates="Client", cascade="all, delete-orphan")
    workshops = relationship("WorkshopStudent", back_populates="Client", cascade="all, delete-orphan")
    Modulos = relationship("Modulos", back_populates="Client", cascade="all, delete-orphan")

class Assistance(Base):
    __tablename__ = "assistance"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String, ForeignKey("clients.idclient"))
    date = Column(Date)
    assistance = Column(Boolean, default=False)

    Client = relationship("Client", back_populates="assistances")

    __table_args__ = (
        UniqueConstraint('student_id', 'date', name='_assistance_student_date_uc'),
    )


class Modulos(Base):
    __tablename__ = "Modulos"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String, ForeignKey("clients.idclient"))
    month = Column(Integer)
    year = Column(Integer)
    Modulos = Column(String)
    is_approved = Column(Boolean, default=False)

    Client = relationship("Client", back_populates="Modulos")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String, ForeignKey("clients.idclient"))
    lastscanhour = Column(DateTime)
    total = Column(Float, default=0.0)
    is_paid = Column(Boolean, default=False)

    Client = relationship("Client", back_populates="payments")

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True)
    description = Column(String)
    cost = Column(Float)
    units = Column(Integer)
    alert_threshold = Column(Integer, default=5)

class Workshop(Base):
    __tablename__ = "workshops"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    description = Column(String)
    is_active = Column(Boolean, default=True) # Para culminar taller sin borrar

    clients = relationship("WorkshopStudent", back_populates="workshop", cascade="all, delete-orphan")
    packages = relationship("Package", secondary="workshop_packages", back_populates="workshops")
    snapshots = relationship("WorkshopStudentPackageSnapshot", cascade="all, delete-orphan")

class WorkshopPackage(Base):
    __tablename__ = "workshop_packages"
    workshop_id = Column(Integer, ForeignKey("workshops.id"), primary_key=True)
    package_id = Column(Integer, ForeignKey("packages.id"), primary_key=True)

class WorkshopStudent(Base):
    __tablename__ = "workshop_students"

    id = Column(Integer, primary_key=True, index=True)
    workshop_id = Column(Integer, ForeignKey("workshops.id"))
    student_id = Column(String, ForeignKey("clients.idclient"))
    package_paid = Column(Boolean, default=False)
    workshop_paid = Column(Boolean, default=False)
    package_id = Column(Integer, ForeignKey("packages.id"), nullable=True)

    workshop = relationship("Workshop", back_populates="clients")
    Client = relationship("Client", back_populates="workshops")
    package = relationship("Package")

class Package(Base):
    __tablename__ = "packages"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    description = Column(String)
    is_active = Column(Boolean, default=True)

    workshops = relationship("Workshop", secondary="workshop_packages", back_populates="packages")
    products = relationship("PackageProduct", back_populates="package", cascade="all, delete-orphan")

class PackageProduct(Base):
    __tablename__ = "package_products"

    id = Column(Integer, primary_key=True, index=True)
    package_id = Column(Integer, ForeignKey("packages.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer)

    package = relationship("Package", back_populates="products")
    product = relationship("Product")

    @property
    def product_description(self):
        return self.product.description if self.product else None

class WorkshopStudentPackageSnapshot(Base):
    """
    Stores the exact quantity of each product when a package payment is made.
    This prevents phantom products when package is edited after payment.
    """
    __tablename__ = "workshop_student_package_snapshots"
    
    id = Column(Integer, primary_key=True, index=True)
    workshop_id = Column(Integer, ForeignKey("workshops.id"))
    student_id = Column(String, ForeignKey("clients.idclient"))
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer)  # Quantity at time of payment
    
    __table_args__ = (
        UniqueConstraint('workshop_id', 'student_id', 'product_id', name='_workshop_student_product_uc'),
    )

class Parqueo(Base):
    __tablename__ = "parqueos"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, unique=True)
    capacidad_maxima = Column(Integer)

    clients = relationship("Client", back_populates="parqueo")

class Tarifa(Base):
    __tablename__ = "tarifas"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, unique=True) # Tarifa 1, Tarifa 2
    costo = Column(Float)

