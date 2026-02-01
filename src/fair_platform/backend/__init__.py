__all__ = ["storage"]

def __getattr__(name: str):
    if name == "storage":
        from fair_platform.backend.data.storage import storage
        return storage
    raise AttributeError(name)
