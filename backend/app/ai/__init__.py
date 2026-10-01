"""AI provider abstraction.

The service layer depends on :class:`AIProvider`, never on a vendor SDK. Adding
a provider means implementing this interface and registering it in
``app/ai/factory.py``; no service code changes.
"""
