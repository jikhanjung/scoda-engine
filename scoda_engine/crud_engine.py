"""
CRUD Engine — generic Create/Read/Update/Delete operations driven by EntitySchema.

All SQL uses parameterized queries. Field names are validated against the schema
whitelist before inclusion in SQL statements.
"""

from __future__ import annotations

import logging
import sqlite3

from .entity_schema import EntitySchema, validate_input

logger = logging.getLogger(__name__)


class CrudEngine:
    def __init__(self, conn: sqlite3.Connection, schema: EntitySchema):
        self.conn = conn
        self.schema = schema

    def create(self, data: dict) -> dict:
        """INSERT a new row and return the created record."""
        errors = validate_input(self.schema, data, 'create')
        if errors:
            raise ValueError('; '.join(errors))

        # FK validation
        fk_errors = self._check_fks(data)
        if fk_errors:
            raise ValueError('; '.join(fk_errors))

        # Constraint check
        constraint_errors = self.check_constraints(data)
        if constraint_errors:
            raise ValueError('; '.join(constraint_errors))

        # Build INSERT — only include fields in schema
        cols = []
        vals = []
        placeholders = []
        for fname, fdef in self.schema.fields.items():
            if fname in data:
                cols.append(fname)
                vals.append(data[fname])
                placeholders.append('?')
            elif fdef.default is not None:
                cols.append(fname)
                vals.append(fdef.default)
                placeholders.append('?')

        sql = (f"INSERT INTO [{self.schema.table}] ({', '.join(cols)}) "
               f"VALUES ({', '.join(placeholders)})")

        cursor = self.conn.cursor()
        cursor.execute(sql, vals)
        pk_value = cursor.lastrowid

        # Execute hooks
        self._execute_hooks(data, 'create')

        self.conn.commit()
        return self.read(pk_value)

    def read(self, pk_value) -> dict | None:
        """SELECT a single row by PK."""
        sql = f"SELECT * FROM [{self.schema.table}] WHERE [{self.schema.pk}] = ?"
        cursor = self.conn.cursor()
        cursor.execute(sql, (pk_value,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def update(self, pk_value, data: dict) -> dict | None:
        """Partial UPDATE — only provided fields are modified."""
        # Verify record exists
        existing = self.read(pk_value)
        if not existing:
            return None

        errors = validate_input(self.schema, data, 'update')
        if errors:
            raise ValueError('; '.join(errors))

        # FK validation
        fk_errors = self._check_fks(data)
        if fk_errors:
            raise ValueError('; '.join(fk_errors))

        # Constraint check (merge existing + new data for uniqueness)
        merged = {**existing, **data}
        constraint_errors = self.check_constraints(merged, pk_value)
        if constraint_errors:
            raise ValueError('; '.join(constraint_errors))

        # Build SET clause — only schema-whitelisted fields
        set_parts = []
        vals = []
        for key, value in data.items():
            if key in self.schema.fields:
                set_parts.append(f"[{key}] = ?")
                vals.append(value)

        if not set_parts:
            return existing

        vals.append(pk_value)
        sql = (f"UPDATE [{self.schema.table}] "
               f"SET {', '.join(set_parts)} "
               f"WHERE [{self.schema.pk}] = ?")

        cursor = self.conn.cursor()
        cursor.execute(sql, vals)

        # Execute hooks
        self._execute_hooks(data, 'update')

        self.conn.commit()
        return self.read(pk_value)

    def delete(self, pk_value) -> bool:
        """DELETE a row by PK. Returns True if deleted."""
        existing = self.read(pk_value)
        if not existing:
            return False

        sql = f"DELETE FROM [{self.schema.table}] WHERE [{self.schema.pk}] = ?"
        cursor = self.conn.cursor()
        cursor.execute(sql, (pk_value,))

        # Execute hooks
        self._execute_hooks(existing, 'delete')

        self.conn.commit()
        return True

    def list(self, filters=None, page=1, per_page=50, search=None) -> dict:
        """List rows with optional filtering, pagination, and search."""
        where_parts = []
        params = []

        if filters:
            for key, value in filters.items():
                if key in self.schema.fields:
                    where_parts.append(f"[{key}] = ?")
                    params.append(value)

        if search:
            search_cols = [f for f, fd in self.schema.fields.items()
                           if fd.type == 'text']
            if search_cols:
                or_parts = [f"[{c}] LIKE ?" for c in search_cols]
                where_parts.append(f"({' OR '.join(or_parts)})")
                params.extend([f"%{search}%"] * len(search_cols))

        where_clause = f" WHERE {' AND '.join(where_parts)}" if where_parts else ""

        # Count
        count_sql = f"SELECT COUNT(*) FROM [{self.schema.table}]{where_clause}"
        cursor = self.conn.cursor()
        cursor.execute(count_sql, params)
        total = cursor.fetchone()[0]

        # Fetch page
        offset = (page - 1) * per_page
        data_sql = (f"SELECT * FROM [{self.schema.table}]{where_clause} "
                    f"ORDER BY [{self.schema.pk}] "
                    f"LIMIT ? OFFSET ?")
        cursor.execute(data_sql, params + [per_page, offset])
        rows = [dict(r) for r in cursor.fetchall()]

        return {
            'rows': rows,
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': (total + per_page - 1) // per_page if per_page > 0 else 0,
        }

    def check_constraints(self, data: dict, pk_value=None) -> list[str]:
        """Check unique_where constraints. Returns list of error messages."""
        errors = []
        cursor = self.conn.cursor()

        for constraint in self.schema.constraints:
            if constraint.get('type') != 'unique_where':
                continue

            where = constraint['where']
            check_fields = constraint.get('fields', [])

            # Build check query
            conditions = []
            params = []
            for f in check_fields:
                if f in data:
                    conditions.append(f"[{f}] = ?")
                    params.append(data[f])

            if not conditions:
                continue

            sql = f"SELECT [{self.schema.pk}] FROM [{self.schema.table}] WHERE {where} AND {' AND '.join(conditions)}"
            if pk_value is not None:
                sql += f" AND [{self.schema.pk}] != ?"
                params.append(pk_value)

            cursor.execute(sql, params)
            if cursor.fetchone():
                msg = constraint.get('message', f"Duplicate: {', '.join(check_fields)}")
                errors.append(msg)

        return errors

    def _check_fks(self, data: dict) -> list[str]:
        """Validate foreign key references exist."""
        errors = []
        cursor = self.conn.cursor()

        for fname, fdef in self.schema.fields.items():
            if fdef.fk and fname in data and data[fname] is not None:
                fk_table, fk_col = fdef.fk.split('.')
                cursor.execute(
                    f"SELECT 1 FROM [{fk_table}] WHERE [{fk_col}] = ?",
                    (data[fname],))
                if not cursor.fetchone():
                    errors.append(
                        f"FK violation: {fname}={data[fname]} not found in {fk_table}.{fk_col}")

        return errors

    def _execute_hooks(self, data: dict, operation: str):
        """Execute post-mutation hooks defined in the schema."""
        cursor = self.conn.cursor()

        for hook in self.schema.hooks:
            # Check trigger_when condition
            trigger_when = hook.get('trigger_when')
            if trigger_when:
                field = trigger_when.get('field')
                value = trigger_when.get('value')
                if field and data.get(field) != value:
                    continue

            # Check operation match
            hook_ops = hook.get('on', ['create', 'update', 'delete'])
            if operation not in hook_ops:
                continue

            sql = hook.get('sql')
            if sql:
                try:
                    cursor.execute(sql)
                except Exception as e:
                    logger.error("Hook '%s' failed: %s", hook.get('name', '?'), e)


    def search(self, query: str, limit: int = 20,
               filters: dict | None = None) -> list[dict]:
        """Search for FK autocomplete — returns matching rows.

        ``filters`` accepts column=value pairs.  A comma-separated value
        is expanded to an ``IN (...)`` clause.
        """
        # Display columns: first 3 non-FK fields (any type, for label display)
        display_cols = [f for f, fd in self.schema.fields.items()
                        if not fd.fk][:3]
        # Search columns: only text fields among display cols (LIKE needs text)
        search_cols = [c for c in display_cols
                       if self.schema.fields[c].type == 'text']
        if not search_cols:
            return []

        or_parts = [f"[{c}] LIKE ?" for c in search_cols]
        where = f"({' OR '.join(or_parts)})"
        params: list = [f"%{query}%"] * len(search_cols)

        # Extra column filters
        if filters:
            all_cols = {self.schema.pk} | set(self.schema.fields.keys())
            for col, val in filters.items():
                if col not in all_cols:
                    continue
                values = [v.strip() for v in val.split(',')]
                placeholders = ', '.join('?' * len(values))
                where += f" AND [{col}] IN ({placeholders})"
                params.extend(values)

        sql = (f"SELECT [{self.schema.pk}], {', '.join(f'[{c}]' for c in display_cols)} "
               f"FROM [{self.schema.table}] "
               f"WHERE {where} "
               f"ORDER BY [{search_cols[0]}] LIMIT ?")
        params.append(limit)

        cursor = self.conn.cursor()
        cursor.execute(sql, params)
        return [dict(r) for r in cursor.fetchall()]
