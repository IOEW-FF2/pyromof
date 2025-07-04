import subprocess
import sys
import os
from pathlib import Path

pyromof = Path(__file__).parent

# Run first script
script1 = os.path.join(pyromof, "optimize.py")
result1 = subprocess.run([sys.executable, script1])
if result1.returncode != 0:
    print("optimize.py failed. Aborting.")
    sys.exit(result1.returncode)

# Run second script
script2 = os.path.join(pyromof, "postprocessing.py")
result2 = subprocess.run([sys.executable, script2])
if result2.returncode != 0:
    print("postprocessing.py failed.")
    sys.exit(result2.returncode)
