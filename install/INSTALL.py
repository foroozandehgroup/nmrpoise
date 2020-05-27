import platform
import subprocess
from pathlib import Path
import sys

osname = platform.system()
p = Path(__file__).parent.resolve()

if osname in ["Darwin", "Linux"]:
    sh_path = p / "install.sh"
    print("calling {}".format(sh_path))
    subprocess.run([str(sh_path)], check=True)
elif osname in ["Windows"]:
    ps1_path = p / "install.ps1"
    print("calling {}".format(ps1_path))
    subprocess.run(["powershell.exe", "-executionpolicy", "bypass",
                    "-File", str(ps1_path)], check=True)
else:
    raise ValueError("Unsupported operating system. "
                     "Please perform a manual installation.")
