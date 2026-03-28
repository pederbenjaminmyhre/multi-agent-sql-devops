import json
from pathlib import Path
from langchain_core.tools import tool

_DEFAULT_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schema" / "Schema.json"
_schema_cache: dict | None = None


def load_schema(path: Path | None = None) -> dict:
    global _schema_cache
    if path is not None:
        with open(path) as f:
            return json.load(f)
    if _schema_cache is None:
        with open(_DEFAULT_SCHEMA_PATH) as f:
            _schema_cache = json.load(f)
    return _schema_cache


def _tables(schema: dict | None = None) -> dict:
    return (schema or load_schema()).get("tables", {})


@tool
def get_table_columns(table_name: str) -> str:
    """Return column definitions for a table from the schema dictionary."""
    tables = _tables()
    if table_name not in tables:
        return f"Table '{table_name}' not found in schema."
    cols = tables[table_name]["columns"]
    lines = [f"  {name}: {info['type']} {'NULL' if info['nullable'] else 'NOT NULL'}"
             for name, info in cols.items()]
    return f"Columns for {table_name}:\n" + "\n".join(lines)


@tool
def get_indexes(table_name: str) -> str:
    """Return existing indexes for a table from the schema dictionary."""
    tables = _tables()
    if table_name not in tables:
        return f"Table '{table_name}' not found in schema."
    indexes = tables[table_name]["indexes"]
    if not indexes:
        return f"No indexes defined for {table_name}."
    lines = [f"  {ix['name']}: ({', '.join(ix['columns'])}) {'UNIQUE' if ix['is_unique'] else ''}"
             for ix in indexes]
    return f"Indexes for {table_name}:\n" + "\n".join(lines)


@tool
def check_column_indexed(table_name: str, column_name: str) -> str:
    """Check whether a specific column is covered by an existing index."""
    tables = _tables()
    if table_name not in tables:
        return f"Table '{table_name}' not found in schema."
    for ix in tables[table_name]["indexes"]:
        if column_name in ix["columns"]:
            return f"Column '{column_name}' on '{table_name}' IS indexed by {ix['name']}."
    return f"Column '{column_name}' on '{table_name}' is NOT indexed."


@tool
def get_foreign_keys(table_name: str) -> str:
    """Return foreign key relationships for a table."""
    tables = _tables()
    if table_name not in tables:
        return f"Table '{table_name}' not found in schema."
    fks = tables[table_name]["foreign_keys"]
    if not fks:
        return f"No foreign keys defined for {table_name}."
    lines = [f"  {fk['column']} -> {fk['references']['table']}.{fk['references']['column']}"
             for fk in fks]
    return f"Foreign keys for {table_name}:\n" + "\n".join(lines)


SCHEMA_TOOLS = [get_table_columns, get_indexes, check_column_indexed, get_foreign_keys]
