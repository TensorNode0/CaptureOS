import re
import uuid as uuidlib
from datetime import datetime, timezone
from decimal import Decimal


def now_utc():
    return datetime.now(timezone.utc)


def iso(dt):
    if dt is None:
        return None
    if isinstance(dt, str):
        return dt
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


_SNAKE_RE = re.compile(r"_([a-z0-9])")


def to_camel(s: str) -> str:
    return _SNAKE_RE.sub(lambda m: m.group(1).upper(), s)


def serialize(value):
    """Convert a DB row (dict) into the JSON shape the frontend expects:
    snake_case column names -> camelCase keys, UUID -> str, datetime -> ISO,
    Decimal -> float. Values inside JSONB payloads are stored camelCase
    already and pass through untouched (their keys contain no underscores)."""
    if value is None:
        return None
    if isinstance(value, list):
        return [serialize(v) for v in value]
    if isinstance(value, dict):
        return {to_camel(k): serialize(v) for k, v in value.items()}
    if isinstance(value, uuidlib.UUID):
        return str(value)
    if isinstance(value, datetime):
        return iso(value)
    if isinstance(value, Decimal):
        f = float(value)
        return int(f) if f.is_integer() else f
    return value


def as_uuid(value):
    """Parse a UUID string; returns uuid.UUID or None if invalid."""
    if isinstance(value, uuidlib.UUID):
        return value
    try:
        return uuidlib.UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        return None
