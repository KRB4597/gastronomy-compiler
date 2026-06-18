from __future__ import annotations

from abc import ABC, abstractmethod

from ..ir.schemas import GastronomyIR, ProjectionResult


class BaseProjection(ABC):
    projection_id: str

    @abstractmethod
    def project(self, ir: GastronomyIR) -> ProjectionResult:
        ...
