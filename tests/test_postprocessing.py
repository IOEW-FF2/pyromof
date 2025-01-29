import sys
import os
import pytest
from pathlib import Path
ROOT_PATH = Path(__file__).parent.parent
sys.path.append(ROOT_PATH)
from scripts import postprocessing


def test_list_int():
        """
        Test that it can sum a list of integers
        """
        assert sum((1, 2, 3)) == 6