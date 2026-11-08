"""Routers live one-per-module here; any module exposing `router` is auto-registered."""
import importlib
import pkgutil

from fastapi import FastAPI


def include_all(app: FastAPI) -> None:
    for mod in pkgutil.iter_modules(__path__):
        router = getattr(importlib.import_module(f"{__name__}.{mod.name}"), "router", None)
        if router is not None:
            app.include_router(router)
