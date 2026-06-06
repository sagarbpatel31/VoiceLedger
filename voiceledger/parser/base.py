"""Parser abstractions for VoiceLedger."""

from __future__ import annotations

from abc import ABC, abstractmethod

from voiceledger.parser.schema import Transaction


class Parser(ABC):
    """Base parser interface for transaction text."""

    @abstractmethod
    def parse(self, text: str) -> Transaction:
        """Parse user text into a validated transaction."""
