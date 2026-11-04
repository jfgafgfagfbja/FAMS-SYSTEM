"""Migration Alembic tren database TRONG phai tao ra dung schema ma models.py mo ta.

Bo test con lai tao bang bang Base.metadata.create_all (nhanh), nen can mot test rieng de chac
rang `alembic upgrade head` - cach production tao/nang cap schema - khong lech voi models.
"""
import re
from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text

from app.core.config import settings
from app.db import models  # noqa: F401  (dang ky bang vao metadata)
from app.db.database import Base

SERVER_DIR = Path(__file__).resolve().parents[1]
MIG_DB_NAME = "fams_system_migtest"
MIG_DB_URL = re.sub(r"/[^/]+$", f"/{MIG_DB_NAME}", settings.DATABASE_URL)
ADMIN_DB_URL = re.sub(r"/[^/]+$", "/postgres", settings.DATABASE_URL)


def _alembic_config(connection) -> Config:
    cfg = Config(str(SERVER_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(SERVER_DIR / "alembic"))
    cfg.attributes["connection"] = connection
    cfg.attributes["configure_logger"] = False
    return cfg


@pytest.fixture()
def empty_db():
    admin = create_engine(ADMIN_DB_URL, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f"DROP DATABASE IF EXISTS {MIG_DB_NAME}"))
        conn.execute(text(f"CREATE DATABASE {MIG_DB_NAME}"))
    engine = create_engine(MIG_DB_URL)
    yield engine
    engine.dispose()
    with admin.connect() as conn:
        conn.execute(text(f"DROP DATABASE IF EXISTS {MIG_DB_NAME}"))
    admin.dispose()


def _upgrade(engine, target="head"):
    with engine.begin() as conn:
        command.upgrade(_alembic_config(conn), target)


def test_single_head():
    heads = ScriptDirectory.from_config(_alembic_config(None)).get_heads()
    assert len(heads) == 1, heads


def test_upgrade_head_on_empty_database_matches_models(empty_db):
    _upgrade(empty_db)
    with empty_db.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    assert diff == [], "\n".join(map(str, diff))


def test_upgrade_is_idempotent_and_downgrade_one_step(empty_db):
    _upgrade(empty_db)
    _upgrade(empty_db)  # da o head: khong lam gi, khong loi
    with empty_db.begin() as conn:
        command.downgrade(_alembic_config(conn), "-1")
    _upgrade(empty_db)
    with empty_db.connect() as conn:
        version = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
    assert version == ScriptDirectory.from_config(_alembic_config(None)).get_current_head()
