"""Compatibility entry point for the canonical API."""
if __package__:
    from .app.main import app
else:
    from app.main import app
