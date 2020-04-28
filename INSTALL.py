import platform
import subprocess
from pathlib import Path
import sys

osname = platform.system()
p = Path(__file__).parent.resolve()

if osname in ["Darwin", "Linux"]:
    sh_path = p / "bin" / "install.sh"
    print("calling bin/install.sh")
    subprocess.run([str(sh_path)])
elif osname in ["Windows"]:
    ps1_path = p / "bin" / "install.ps1"
    print("calling bin/install.ps1")
    subprocess.run(["powershell.exe", "-executionpolicy", "bypass",
                    "-File", str(ps1_path)])
else:
    print("Unsupported operating system. "
          "Please perform a manual installation.")
    sys.exit(1)

input("Press Enter to exit.")  # don't close the window so quickly
