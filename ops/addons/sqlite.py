"""SQLite database management plugin."""

from __future__ import annotations

import os
import sqlite3
import json
from contextlib import closing

from kernel.registry import tool


@tool(name="sqlitelisttables", category="database", desc="List all tables in an SQLite database")
def sqlitelisttables(db_path: str) -> str:
    """Lists all tables present in the specified SQLite database.

    Args:
        db_path: Absolute or relative path to the SQLite database file.
    """
    if not os.path.exists(db_path):
        return f"Error: Database file not found at {db_path}"

    try:
        with closing(sqlite3.connect(db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]
            if not tables:
                return "No tables found in this database."
            return "Tables:\n- " + "\n- ".join(tables)
    except Exception as e:
        return f"Database error: {e}"


@tool(name="sqlitegetschema", category="database", desc="Get schema for a specific SQLite table")
def sqlitegetschema(db_path: str, table_name: str) -> str:
    """Retrieves the schema definition (columns and types) for a specified table.

    Args:
        db_path: Path to the SQLite database.
        table_name: Name of the table to inspect.
    """
    if not os.path.exists(db_path):
        return f"Error: Database file not found at {db_path}"

    try:
        with closing(sqlite3.connect(db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            
            if not columns:
                return f"Error: Table '{table_name}' does not exist or has no columns."
            
            # format: (cid, name, type, notnull, dflt_value, pk)
            schema = [f"Table: {table_name}"]
            schema.append(f"{'CID':<5} | {'Name':<20} | {'Type':<15} | {'Not Null':<10} | {'Default':<15} | {'PK':<5}")
            schema.append("-" * 80)
            
            for col in columns:
                schema.append(f"{col[0]:<5} | {col[1]:<20} | {col[2]:<15} | {str(bool(col[3])):<10} | {str(col[4]):<15} | {str(bool(col[5])):<5}")
                
            return "\n".join(schema)
    except Exception as e:
        return f"Database error: {e}"


@tool(name="sqlitequery", category="database", desc="Execute a SELECT query and fetch results")
def sqlitequery(db_path: str, query: str, max_rows: int = 100) -> str:
    """Executes a SQL SELECT query against the SQLite database and returns the results.
    Do NOT use this for structural changes or writes. Use sqliteexecute for that.

    Args:
        db_path: Path to the SQLite database.
        query: The SQL SELECT query to execute.
        max_rows: Maximum number of rows to return (default: 100) to prevent output flooding.
    """
    if not os.path.exists(db_path):
        return f"Error: Database file not found at {db_path}"

    if not query.strip().upper().startswith("SELECT") and not query.strip().upper().startswith("PRAGMA"):
        return "Error: sqlitequery only supports SELECT or PRAGMA statements. Use sqliteexecute for modifications."

    try:
        with closing(sqlite3.connect(db_path)) as conn:
            # Enable dictionary cursor for better JSON formatting
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute(query)
            rows = cursor.fetchmany(max_rows)
            
            if not rows:
                return "Query executed successfully, but returned no rows."
                
            # Convert to dicts for JSON output
            result_dicts = [dict(row) for row in rows]
            return json.dumps(result_dicts, indent=2, default=str)
            
    except Exception as e:
        return f"Database error: {e}"


@tool(name="sqliteexecute", category="database", desc="Execute a modifying SQL statement (INSERT, UPDATE, DELETE, CREATE, DROP)")
def sqliteexecute(db_path: str, query: str, confirm_destructive: bool = False) -> str:
    """Executes a modifying SQL statement and commits the transaction.

    Args:
        db_path: Path to the SQLite database.
        query: The modifying SQL query (e.g. INSERT, UPDATE, DELETE).
        confirm_destructive: MUST be set to True if the query contains 'DROP', 'DELETE', or 'TRUNCATE'.
    """
    if not os.path.exists(db_path):
        # Allow CREATE statements to implicitly create the database if needed,
        # but only if the user provides an absolute or valid relative path.
        if "CREATE" not in query.strip().upper():
            return f"Error: Database file not found at {db_path}"

    upper_query = query.strip().upper()
    is_destructive = any(word in upper_query for word in ["DROP", "DELETE", "TRUNCATE"])
    
    if is_destructive and not confirm_destructive:
        return "Error: Query appears destructive. You must set confirm_destructive=True to execute it."

    if upper_query.startswith("SELECT") or upper_query.startswith("PRAGMA"):
        return "Warning: You are using sqliteexecute for a SELECT/PRAGMA query. No results will be returned. Use sqlitequery instead."

    try:
        with closing(sqlite3.connect(db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            conn.commit()
            
            affected = cursor.rowcount
            return f"Query executed successfully. Rows affected: {affected}"
    except Exception as e:
        return f"Database error: {e}"
