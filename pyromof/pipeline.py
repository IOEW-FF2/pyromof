import os
import subprocess
import sys
from pathlib import Path

pyromof = Path(__file__).parent

# Run optimize
script1 = os.path.join(pyromof, "optimize.py")
result1 = subprocess.run([sys.executable, script1])
if result1.returncode != 0:
    print("optimize.py failed. Aborting.")
    sys.exit(result1.returncode)

# Run postprocessing
script2 = os.path.join(pyromof, "postprocessing.py")
result2 = subprocess.run([sys.executable, script2])
if result2.returncode != 0:
    print("postprocessing.py failed.")
    sys.exit(result2.returncode)


# Run plotting
script3 = os.path.join(pyromof, "plotting.py")
result3 = subprocess.run([sys.executable, script3])
if result3.returncode != 0:
    print("plotting.py failed.")
    sys.exit(result3.returncode)
