from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
import os

SQLALCHEMY_DATABASE_URL = os.getenv("SQLALCHEMY_DATABASE_URL")

if SQLALCHEMY_DATABASE_URL and SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

if not SQLALCHEMY_DATABASE_URL:
    raise ValueError("La variable SQLALCHEMY_DATABASE_URL no está configurada en Vercel")

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,
    poolclass=NullPool,
    connect_args={"connect_timeout": 10}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def init_db():
    """Crea todas las tablas y carga los datos semilla si aún no existen."""
    from . import models
    Base.metadata.create_all(bind=engine)
    
    # Alternar restricciones de llave foránea en PostgreSQL para apuntar a client_requests
    try:
        with engine.connect() as conn:
            # Dropear constraints viejas que apuntan a clients
            conn.execute(text("ALTER TABLE entradas_salidas DROP CONSTRAINT IF EXISTS entradas_salidas_client_id_fkey;"))
            conn.execute(text("ALTER TABLE transacciones DROP CONSTRAINT IF EXISTS transacciones_client_id_fkey;"))
            # Crear nuevas constraints que apuntan a client_requests (permite entradas previas a registro)
            conn.execute(text("ALTER TABLE entradas_salidas DROP CONSTRAINT IF EXISTS entradas_salidas_client_id_requests_fkey;"))
            conn.execute(text("ALTER TABLE entradas_salidas ADD CONSTRAINT entradas_salidas_client_id_requests_fkey FOREIGN KEY (client_id) REFERENCES client_requests(client_id) ON DELETE CASCADE;"))
            conn.execute(text("ALTER TABLE transacciones DROP CONSTRAINT IF EXISTS transacciones_client_id_requests_fkey;"))
            conn.execute(text("ALTER TABLE transacciones ADD CONSTRAINT transacciones_client_id_requests_fkey FOREIGN KEY (client_id) REFERENCES client_requests(client_id) ON DELETE CASCADE;"))
            conn.commit()
    except Exception as e:
        print(f"Advertencia al ajustar constraints de DB: {e}")
        
    _seed(models)


def _seed(models):
    """Inserta datos por defecto solo si la tabla está vacía."""
    db = SessionLocal()
    try:
        # ── tipos_vehiculo ───────────────────────────────────────────────────
        if db.query(models.TipoVehiculo).count() == 0:
            for nombre in ["Carro", "Moto", "Pesado"]:
                db.add(models.TipoVehiculo(nombre=nombre))
            db.commit()

        # ── unidades_tiempo ──────────────────────────────────────────────────
        if db.query(models.UnidadTiempo).count() == 0:
            for nombre in ["Fraccion", "Hora", "Dia", "Mes"]:
                db.add(models.UnidadTiempo(nombre=nombre))
            db.commit()

        # ── roles ────────────────────────────────────────────────────────────
        if db.query(models.Rol).count() == 0:
            for rol in ["Gerente", "Maquina", "Seguridad"]:
                db.add(models.Rol(rol=rol))
            db.commit()

        # ── empleado + credencial de Arturo Maldonado (Gerente) ──────────────
        if db.query(models.Empleado).count() == 0:
            rol_gerente = db.query(models.Rol).filter(models.Rol.rol == "Gerente").first()
            arturo = models.Empleado(
                nombres="Arturo",
                apellidos="Maldonado",
                cui="274599",
                edad=21,
                rol_id=rol_gerente.id
            )
            db.add(arturo)
            db.flush()  # Para obtener arturo.id antes del commit

            cred = models.Credential(
                empleado_id=arturo.id,
                user="Mcfly",
                # Hash argon2id generado con hash.py
                passwd=(
                    "$argon2id$v=19$m=65536,t=3,p=4"
                    "$Gct4tOkBsWW7njs56WDrBg"
                    "$mMLZZxe04g8OeBSxLldb4ZtSgjtMNZuAw26ZZWzAtlA"
                )
            )
            db.add(cred)
            db.commit()

    except Exception as e:
        db.rollback()
        print(f"[SEED ERROR] {e}")
    finally:
        db.close()