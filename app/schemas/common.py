"""Shared pagination, response wrappers, and common schemas."""

from typing import Generic, TypeVar
from pydantic import BaseModel, Field

DataT = TypeVar("DataT")


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1, description="Page number (1-based)")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class PaginatedResponse(BaseModel, Generic[DataT]):
    success: bool = True
    data: list[DataT]
    total: int
    page: int
    page_size: int
    total_pages: int

    @classmethod
    def build(
        cls,
        data: list,
        total: int,
        page: int,
        page_size: int,
    ) -> "PaginatedResponse":
        total_pages = max(1, (total + page_size - 1) // page_size)
        return cls(
            data=data,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )


class SuccessResponse(BaseModel):
    success: bool = True
    message: str


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail
