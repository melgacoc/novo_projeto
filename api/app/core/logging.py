import logging

from app.core.config import settings


def setup_logging() -> None:
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    if settings.sentry_dsn:
        import sentry_sdk

        sentry_sdk.init(dsn=settings.sentry_dsn, environment=settings.app_env, traces_sample_rate=0.1)
