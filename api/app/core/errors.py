"""Padrão de erros da API: { "error": { "code", "message", "details"? } }."""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("app.errors")


class AppError(Exception):
    def __init__(self, status: int, code: str, message: str, details: dict | None = None):
        self.status = status
        self.code = code
        self.message = message
        self.details = details
        super().__init__(message)


def not_found(what: str = "Recurso") -> AppError:
    return AppError(404, "not_found", f"{what} não encontrado")


def forbidden(message: str = "Sem permissão") -> AppError:
    return AppError(403, "forbidden", message)


def bad_request(code: str, message: str, details: dict | None = None) -> AppError:
    return AppError(400, code, message, details)


def conflict(code: str, message: str, details: dict | None = None) -> AppError:
    return AppError(409, code, message, details)


def _body(code: str, message: str, details=None) -> dict:
    err: dict = {"code": code, "message": message}
    if details:
        err["details"] = details
    return {"error": err}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError):
        return JSONResponse(status_code=exc.status, content=_body(exc.code, exc.message, exc.details))

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException):
        code = {401: "unauthorized", 403: "forbidden", 404: "not_found", 405: "method_not_allowed"}.get(
            exc.status_code, "http_error"
        )
        return JSONResponse(status_code=exc.status_code, content=_body(code, str(exc.detail)))

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        details = [
            {"loc": [str(p) for p in e.get("loc", [])], "msg": e.get("msg")} for e in exc.errors()
        ]
        return JSONResponse(
            status_code=422, content=_body("validation_error", "Dados inválidos", {"fields": details})
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception):
        # nunca expõe stack trace: o detalhe vai para o log (e para o Sentry, se configurado)
        log.exception("erro não tratado em %s %s", request.method, request.url.path)
        return JSONResponse(status_code=500, content=_body("internal_error", "Erro interno"))
