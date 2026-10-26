from starlette.middleware.gzip import GZipMiddleware

from fair_platform.backend.main import app


def test_application_compresses_large_responses() -> None:
    middleware = next(
        item for item in app.user_middleware if item.cls is GZipMiddleware
    )

    assert middleware.kwargs == {"minimum_size": 500, "compresslevel": 6}
