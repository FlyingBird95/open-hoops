from typing import Any


def resource_object(
    type: str,
    uid: str,
    attributes: dict[str, Any],
    relationships: dict[str, Any] | None = None,
) -> dict[str, Any]:
    obj: dict[str, Any] = {"type": type, "uid": uid, "attributes": attributes}
    if relationships:
        obj["relationships"] = relationships
    return obj


def relationship_linkage(type: str, uid: str) -> dict[str, Any]:
    return {"data": {"type": type, "uid": uid}}


def null_relationship() -> dict[str, Any]:
    return {"data": None}


def document(data: dict | list, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    doc: dict[str, Any] = {"data": data, "jsonapi": {"version": "1.1"}}
    if meta:
        doc["meta"] = meta
    return doc


def error_response(
    status: int, title: str, detail: str, source: dict | None = None
) -> dict[str, Any]:
    error: dict[str, Any] = {"status": str(status), "title": title, "detail": detail}
    if source:
        error["source"] = source
    return {"errors": [error]}
