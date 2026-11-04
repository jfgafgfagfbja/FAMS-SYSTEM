"""Sinh so do quan he CSDL (Mermaid erDiagram) tu chinh models.py -> docs/database/erd.mermaid.

    server/venv/Scripts/python scripts/export_erd.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))

from app.db import models  # noqa: E402,F401  (dang ky bang)
from app.db.database import Base  # noqa: E402


def type_name(col) -> str:
    name = type(col.type).__name__.lower()
    return {"varchar": "string", "string": "string", "text": "text", "integer": "int",
            "boolean": "bool", "float": "float", "datetime": "datetime", "date": "date",
            "time": "time", "vector": "vector512"}.get(name, name)


def main() -> None:
    lines = ["erDiagram"]
    tables = Base.metadata.sorted_tables
    for table in tables:
        for col in table.columns:
            for fk in col.foreign_keys:
                parent = fk.column.table.name.upper()
                card = "|o--o{" if col.nullable else "||--o{"
                if col.unique:
                    card = "|o--o|" if col.nullable else "||--o|"
                lines.append(f'    {parent} {card} {table.name.upper()} : "{col.name}"')
    lines.append("")
    for table in tables:
        uniques = {c.name for c in table.columns if c.unique}
        for cons in table.constraints:
            cols = getattr(cons, "columns", None)
            if cons.__class__.__name__ == "UniqueConstraint" and cols is not None and len(cols) == 1:
                uniques.update(c.name for c in cols)
        lines.append(f"    {table.name.upper()} {{")
        for col in table.columns:
            keys = []
            if col.primary_key:
                keys.append("PK")
            if col.foreign_keys:
                keys.append("FK")
            if col.name in uniques and not col.primary_key:
                keys.append("UK")
            lines.append(f"        {type_name(col)} {col.name}{(' ' + ','.join(keys)) if keys else ''}")
        lines.append("    }")
    out = ROOT / "docs" / "database" / "erd.mermaid"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Da ghi {out} ({len(tables)} bang)")


if __name__ == "__main__":
    main()
