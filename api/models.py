from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from .database import Base


# ─────────────────────────────────────────────
# A. MÓDULO DE PARQUEOS Y RECURSOS
# ─────────────────────────────────────────────

class Parqueo(Base):
    __tablename__ = "parqueos"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, unique=True, nullable=False)
    capacidad = Column(Integer, nullable=False)


class TipoVehiculo(Base):
    __tablename__ = "tipos_vehiculo"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, unique=True, nullable=False)  # Carro, Moto, Pesado

    tarifas = relationship("Tarifa", back_populates="tipo_vehiculo")
    clients = relationship("Client", back_populates="tipo_vehiculo")


class UnidadTiempo(Base):
    __tablename__ = "unidades_tiempo"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, unique=True, nullable=False)  # Fraccion, Hora, Dia, Mes

    tarifas = relationship("Tarifa", back_populates="unidad_tiempo")


class Tarifa(Base):
    __tablename__ = "tarifas"

    id = Column(Integer, primary_key=True, index=True)
    tipo_vehiculo_id = Column(Integer, ForeignKey("tipos_vehiculo.id"), nullable=False)
    unidad_tiempo_id = Column(Integer, ForeignKey("unidades_tiempo.id"), nullable=False)
    costo = Column(Numeric(10, 2), nullable=False)

    tipo_vehiculo = relationship("TipoVehiculo", back_populates="tarifas")
    unidad_tiempo = relationship("UnidadTiempo", back_populates="tarifas")


# ─────────────────────────────────────────────
# B. MÓDULO DE PERSONAL Y SEGURIDAD
# ─────────────────────────────────────────────

class Rol(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    rol = Column(String, unique=True, nullable=False)  # Gerente, Maquina, Seguridad

    empleados = relationship("Empleado", back_populates="rol_rel")


class Empleado(Base):
    __tablename__ = "empleados"

    id = Column(Integer, primary_key=True, index=True)
    nombres = Column(String, nullable=False)
    apellidos = Column(String, nullable=False)
    cui = Column(String, unique=True, nullable=False)
    edad = Column(Integer, nullable=False)
    rol_id = Column(Integer, ForeignKey("roles.id"), nullable=False)

    rol_rel = relationship("Rol", back_populates="empleados")
    credential = relationship("Credential", back_populates="empleado", uselist=False)


class Credential(Base):
    __tablename__ = "credentials"

    id = Column(Integer, primary_key=True, index=True)
    empleado_id = Column(Integer, ForeignKey("empleados.id"), nullable=False)
    user = Column(String, unique=True, nullable=False)
    passwd = Column(String, nullable=False)  # hash argon2

    empleado = relationship("Empleado", back_populates="credential")


# ─────────────────────────────────────────────
# C. MÓDULO DE OPERACIONES
# ─────────────────────────────────────────────

class ClientRequest(Base):
    """Solicitud previa que genera el seqcode y el client_id antes del registro."""
    __tablename__ = "client_requests"

    id = Column(Integer, primary_key=True, index=True)
    security_code = Column(String, nullable=False)   # 6 dígitos de seqcode.py
    client_id = Column(String, unique=True, nullable=False)  # UUID/idticket generado

    client = relationship("Client", back_populates="request", uselist=False)


class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    nombres = Column(String, nullable=False)
    apellidos = Column(String, nullable=False)
    dpi = Column(String, nullable=False)
    client_id = Column(String, ForeignKey("client_requests.client_id"), unique=True, nullable=False)
    tipo_vehiculo_id = Column(Integer, ForeignKey("tipos_vehiculo.id"), nullable=False, default=1)  # default: Carro
    placa = Column(String, nullable=False)
    numero = Column(Integer, nullable=True)
    ticket_url = Column(String, nullable=True)

    request = relationship("ClientRequest", back_populates="client")
    tipo_vehiculo = relationship("TipoVehiculo", back_populates="clients")
    entradas_salidas = relationship("EntradaSalida", back_populates="client")
    transacciones = relationship("Transaccion", back_populates="client")


class EntradaSalida(Base):
    __tablename__ = "entradas_salidas"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(String, ForeignKey("client_requests.client_id"), nullable=False)
    fecha_hora = Column(DateTime, nullable=False)
    tipo = Column(String, nullable=False)  # "entrada" | "salida"

    client = relationship("Client", back_populates="entradas_salidas")


# ─────────────────────────────────────────────
# D. MÓDULO FINANCIERO
# ─────────────────────────────────────────────

class Transaccion(Base):
    __tablename__ = "transacciones"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(String, ForeignKey("client_requests.client_id"), nullable=False)
    monto = Column(Numeric(10, 2), nullable=False)
    tipo_transaccion = Column(String, nullable=False)  # "recarga" | "cobro"
    fecha_hora = Column(DateTime, nullable=False)

    client = relationship("Client", back_populates="transacciones")
