from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Float, UniqueConstraint, Date, DateTime, func
from sqlalchemy.orm import relationship
from .database import Base

class Client(Base):
    __tablename__ = "clients"

    idclient = Column(String, primary_key=True, index=True)
    names = Column(String)
    lastnames = Column(String)
    nit = Column(String, unique=False, index=True)
    cui = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    
    is_created = Column(DateTime, default=func.now())
    is_paid = Column(Boolean, default=False)
    
    parqueo_id = Column(Integer, ForeignKey("parqueos.id"))
    
    registration_date = Column(String, nullable=True)
    carnet_pdf_url = Column(String, nullable=True)
    
    parqueo = relationship("Parqueo", back_populates="clients")
    payments = relationship("Payment", back_populates="Client", cascade="all, delete-orphan")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String, ForeignKey("clients.idclient"))
    lastscanhour = Column(DateTime)
    total = Column(Float, default=0.0)
    is_paid = Column(Boolean, default=False)

    Client = relationship("Client", back_populates="payments")

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

