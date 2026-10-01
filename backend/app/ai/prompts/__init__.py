"""Prompt templates.

Prompts live here as template strings, never inline in a service function. Every
prompt shares the same four rules:

1. Require a JSON object matching a Pydantic schema.
2. Never invent information; state uncertainty explicitly.
3. Never claim a translation is certified or guaranteed accurate.
4. Respect risk escalation: for high-risk content, recommend the professional
   process instead of producing a final answer.
"""
