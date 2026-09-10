"""Fixtures compartidas."""
from pathlib import Path
import pytest
from parser import Extraccion


@pytest.fixture
def datos() -> Extraccion:
    return Extraccion()


@pytest.fixture
def ruta() -> Path:
    return Path("documento.pdf")
