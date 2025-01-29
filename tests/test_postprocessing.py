import sys
from pathlib import Path

ROOT_PATH = Path(__file__).parent.parent
sys.path.append(ROOT_PATH)
# from pyromof import postprocessing  -
# This executes all code in postprocessing, which doesn't work on github because there's not dumping space.


def test_list_int():
    """
    Test that it can sum a list of integers
    """
    assert sum((1, 2, 3)) == 6
