"""Centralized exception definitions and handlers for SwiftCourier."""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from jose import JWTError


class AppException(Exception):
    """Base application exception."""

    def __init__(self, status_code: int, detail: str, code: str | None = None):
        self.status_code = status_code
        self.detail = detail
        self.code = code or "error"
        super().__init__(detail)


class NotFoundError(AppException):
    def __init__(self, resource: str = "Resource"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource} not found.",
            code="not_found",
        )


class UnauthorizedError(AppException):
    def __init__(self, detail: str = "Authentication required."):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            code="unauthorized",
        )


class ForbiddenError(AppException):
    def __init__(self, detail: str = "You do not have permission to perform this action."):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            code="forbidden",
        )


class ConflictError(AppException):
    def __init__(self, detail: str = "A conflict occurred."):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
            code="conflict",
        )


class BadRequestError(AppException):
    def __init__(self, detail: str = "Bad request."):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            code="bad_request",
        )


class UnprocessableError(AppException):
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
            code="unprocessable",
        )


def _error_response(status_code: int, detail: str, code: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"success": False, "error": {"code": code, "message": detail}},
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Attach global exception handlers to the FastAPI app."""

    @app.exception_handler(AppException)
    async def app_exception_handler(_request: Request, exc: AppException) -> JSONResponse:
        return _error_response(exc.status_code, exc.detail, exc.code)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errors = []
        for err in exc.errors():
            loc = ".".join(str(l) for l in err.get("loc", []))
            errors.append({"field": loc, "message": err["msg"]})
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "success": False,
                "error": {"code": "validation_error", "message": "Input validation failed.", "details": errors},
            },
        )

    @app.exception_handler(JWTError)
    async def jwt_exception_handler(_request: Request, _exc: JWTError) -> JSONResponse:
        return _error_response(
            status.HTTP_401_UNAUTHORIZED, "Invalid or expired token.", "token_invalid"
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
        return _error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "An internal server error occurred.",
            "internal_error",
        )
