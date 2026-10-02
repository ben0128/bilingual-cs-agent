"""Cloudflare Workers entrypoint.

All app logic lives in api.py so tests can import it without the Workers runtime.
"""
from workers import asgi

from api import app

Default = asgi.entrypoint(app)
