from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from ..ir.schemas import DimensionScore, GastronomyIR

if TYPE_CHECKING:
    pass


class FlavorModule(ABC):
    """Base class for a single-dimension flavor assessment module.

    Analogous to ErisML EthicalModule.  Each module reads the extracted
    GastronomyIR and emits a DimensionScore for its assigned dimension.
    """

    dimension: str  # one of FLAVOR_DIMENSIONS

    @abstractmethod
    def score(self, ir: GastronomyIR) -> DimensionScore:
        ...
