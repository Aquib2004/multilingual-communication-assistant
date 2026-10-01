"""Verification engine.

This package is deliberately **pure Python with no AI dependency**. It imports
only the standard library and ``app.core``. That constraint is what makes fact
extraction, date/time mismatch detection and risk classification testable with
no network, no API key and no model provider - and it guarantees those checks
behave identically no matter which model produced the translation.
"""
