"""
Entity Schema — parse manifest editable_entities into validated schemas.

Provides FieldDef/EntitySchema dataclasses and validation utilities
for the manifest-driven CRUD framework.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class FieldDef:
    name: str
    type: str = 'text'         # 'text', 'integer', 'boolean', 'json', 'real'
    required: bool = False
    enum: list | None = None
    fk: str | None = None      # 'table.column'
    default: Any = None
    label: str | None = None
    readonly_on_edit: bool = False

    VALID_TYPES = {'text', 'integer', 'boolean', 'json', 'real'}


@dataclass
class EntitySchema:
    name: str
    table: str
    pk: str
    operations: set
    fields: dict[str, FieldDef]
    constraints: list = field(default_factory=list)
    hooks: list = field(default_factory=list)
    list_query: str | None = None
    detail_query: str | None = None


def parse_editable_entities(manifest: dict) -> dict[str, EntitySchema]:
    """Parse the editable_entities section of a manifest into EntitySchema objects.

    Args:
        manifest: Full manifest dict (must contain 'editable_entities' key)

    Returns:
        Dict mapping entity name to EntitySchema
    """
    entities_def = manifest.get('editable_entities', {})
    schemas = {}

    for name, edef in entities_def.items():
        fields = {}
        for fname, fdef in edef.get('fields', {}).items():
            if isinstance(fdef, str):
                fields[fname] = FieldDef(name=fname, type=fdef)
            else:
                fields[fname] = FieldDef(
                    name=fname,
                    type=fdef.get('type', 'text'),
                    required=fdef.get('required', False),
                    enum=fdef.get('enum'),
                    fk=fdef.get('fk'),
                    default=fdef.get('default'),
                    label=fdef.get('label'),
                    readonly_on_edit=fdef.get('readonly_on_edit', False),
                )

        schemas[name] = EntitySchema(
            name=name,
            table=edef['table'],
            pk=edef.get('pk', 'id'),
            operations=set(edef.get('operations', ['create', 'read', 'update', 'delete'])),
            fields=fields,
            constraints=edef.get('constraints', []),
            hooks=edef.get('hooks', []),
            list_query=edef.get('list_query'),
            detail_query=edef.get('detail_query'),
        )

    return schemas


def validate_input(schema: EntitySchema, data: dict, operation: str) -> list[str]:
    """Validate input data against an entity schema.

    Args:
        schema: The entity schema
        data: Input data dict
        operation: 'create' or 'update'

    Returns:
        List of error messages (empty = valid)
    """
    errors = []

    # Check for unknown fields
    for key in data:
        if key not in schema.fields and key != schema.pk:
            errors.append(f"Unknown field: {key}")

    for fname, fdef in schema.fields.items():
        value = data.get(fname)

        # Required check (only on create; update is partial)
        if operation == 'create' and fdef.required and value is None and fdef.default is None:
            errors.append(f"Required field missing: {fname}")
            continue

        if value is None:
            continue

        # Type check
        if fdef.type == 'integer':
            if not isinstance(value, int) and not (isinstance(value, str) and value.lstrip('-').isdigit()):
                errors.append(f"Field '{fname}' must be an integer")
        elif fdef.type == 'real':
            try:
                float(value)
            except (ValueError, TypeError):
                errors.append(f"Field '{fname}' must be a number")
        elif fdef.type == 'boolean':
            if value not in (True, False, 0, 1, '0', '1'):
                errors.append(f"Field '{fname}' must be a boolean")

        # Enum check
        if fdef.enum is not None and value not in fdef.enum:
            errors.append(f"Field '{fname}' must be one of: {fdef.enum}")

    return errors
