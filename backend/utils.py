from datetime import datetime, timezone
from bson import ObjectId


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


def serialize(doc):
    """Recursively convert a MongoDB document into a JSON-safe dict.
    _id -> id (str), ObjectId -> str, datetime -> iso string."""
    if doc is None:
        return None
    if isinstance(doc, list):
        return [serialize(d) for d in doc]
    if not isinstance(doc, dict):
        if isinstance(doc, ObjectId):
            return str(doc)
        if isinstance(doc, datetime):
            return iso(doc)
        return doc
    out = {}
    for k, v in doc.items():
        if k == "_id":
            out["id"] = str(v)
        elif isinstance(v, ObjectId):
            out[k] = str(v)
        elif isinstance(v, datetime):
            out[k] = iso(v)
        elif isinstance(v, dict):
            out[k] = serialize(v)
        elif isinstance(v, list):
            out[k] = [serialize(i) for i in v]
        else:
            out[k] = v
    return out


def oid(value):
    """Safely build an ObjectId; raise 404-friendly error upstream if invalid."""
    try:
        return ObjectId(value)
    except Exception:
        return None
