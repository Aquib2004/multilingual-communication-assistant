"""Pydantic request/response models.

These are the API contract. They are intentionally separate from the SQLAlchemy
models in ``app.models`` so the persistence schema and the public API can evolve
independently.
"""
