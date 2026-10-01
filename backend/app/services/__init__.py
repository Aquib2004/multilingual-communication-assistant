"""Service layer: workflow orchestration.

Services own the business rules and the message state machine. They may depend
on the AI layer, the verification engine, and persistence. They must not import
FastAPI request or routing types.
"""
