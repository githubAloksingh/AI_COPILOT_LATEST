from importlib import import_module

__all__ = ["router"]


def __getattr__(name):
    if name == "router":
        module = import_module(".routes", __name__)
        value = module.router
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
