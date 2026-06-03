"""Resetea la base de datos local (SQLite) y re-seedea con datos limpios.

Uso:
    python scripts/reset_and_seed.py

Flujo:
  1. Borra el archivo app.db
  2. Crea todas las tablas con SQLAlchemy (Base.metadata.create_all)
  3. Stampa Alembic a 'head' para mantener la cadena de versiones
  4. Ejecuta el seed de datos iniciales
"""
import os
import sys
import subprocess

# Añadir el directorio raíz del backend al path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from app.core.config import settings


def main():
    db_path = settings.SQLITE_PATH
    # Resolve relative to backend dir
    if not os.path.isabs(db_path):
        db_path = os.path.join(backend_dir, db_path)

    # 1. Eliminar DB
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"[OK] Base de datos eliminada: {db_path}")
    else:
        print(f"[INFO] No existía: {db_path}")

    # 2. Crear todas las tablas con SQLAlchemy
    print("\n=== Creando tablas con SQLAlchemy ===")
    from app.core.database import engine, Base
    # Importar todos los modelos para que se registren en Base.metadata
    from app.models import (  # noqa: F401
        AccessLevel, ActivationToken, Area, ArcoRequest, AuditLog,
        Certificate, Credential, DeletionRequest, Document,
        DocumentSignature, MigrantRecord, OtpToken,
        Permission, Role, Template, User,
    )
    Base.metadata.create_all(bind=engine)
    print("[OK] Tablas creadas correctamente.")


    # 3. Stamp Alembic a head
    print("\n=== Stampando Alembic a head ===")
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "stamp", "head"],
        cwd=backend_dir,
        capture_output=True,
        text=True,
    )
    print(result.stdout)
    if result.stderr:
        print(result.stderr)
    if result.returncode != 0:
        print("[WARN] Alembic stamp falló, pero las tablas están creadas.")

    # 4. Re-seedear
    print("\n=== Ejecutando seed ===")
    from scripts.seed_initial_data import seed
    seed()


if __name__ == "__main__":
    main()
