"""Quality statement for every automatically computed metric
(STECKBRIEF_MODUL §2, guideline 3): below a defined threshold the metric
shows "nicht belastbar messbar" instead of a value."""
from __future__ import annotations

from dataclasses import dataclass

NICHT_BELASTBAR = "nicht belastbar messbar"


@dataclass(frozen=True)
class Kennzahl:
    """A metric with its quality.

    wert: None when not reliable (the reason is in grund).
    qualitaet: 0 to 1; belastbar: qualitaet reached the threshold.
    """

    wert: float | None
    qualitaet: float
    belastbar: bool
    einheit: str = ""
    grund: str | None = None

    @classmethod
    def bewertet(cls, wert: float | None, qualitaet: float, schwelle: float, einheit: str = "", grund: str | None = None) -> "Kennzahl":
        """Value only if the quality reaches the threshold."""
        q = float(max(0.0, min(1.0, qualitaet)))
        if wert is None or q < schwelle:
            return cls(None, q, False, einheit, grund or NICHT_BELASTBAR)
        return cls(float(wert), q, True, einheit, None)

    @classmethod
    def fehlt(cls, grund: str, einheit: str = "") -> "Kennzahl":
        return cls(None, 0.0, False, einheit, grund)

    @property
    def anzeige(self) -> str | float:
        """Value for the Steckbrief, or the fixed text."""
        return self.wert if self.belastbar and self.wert is not None else NICHT_BELASTBAR
