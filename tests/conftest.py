import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.db.connection import get_connection


@pytest.fixture
def con():
    connection = get_connection(":memory:")
    yield connection
    connection.close()
