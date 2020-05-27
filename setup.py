import sys
import subprocess
from pathlib import Path
from setuptools import setup, find_packages
from setuptools.command.install import install


class poptpyInstall(install):
    def run(self):
        super().run()
        p = Path(__file__).parent.resolve()
        p_install = p / "install" / "INSTALL.py"
        subprocess.run([sys.executable, str(p_install)], check=True)


with open("README.md", "r") as fp:
    long_description = fp.read()


setup(
    name="ts-poptpy",
    version="0.1.2",
    author="Jonathan Yong",
    author_email="yongrenjie@gmail.com",
    description="NMR parameter optimisation in TopSpin",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yongrenjie/poptpy",
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.4',
    install_requires=["numpy>=1.17.0"],
    cmdclass={"install": poptpyInstall},
)
