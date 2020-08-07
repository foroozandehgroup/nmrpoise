import sys
import subprocess
from pathlib import Path
from setuptools import setup, find_packages
from setuptools.command.install import install


class TopSpinInstall(install):
    def run(self):
        p = Path(__file__).parent.resolve()
        p_install = p / "topspin_install.py"
        subprocess.run([sys.executable, str(p_install)], check=True)
        super().run()


class noTopSpinInstall(install):
    """Doesn't install to TopSpin. Useful for testing."""
    pass


with open("README.md", "r") as fp:
    long_description = fp.read()


setup(
    name="poptpy",
    version="0.1.8",
    author="Jonathan Yong",
    author_email="yongrenjie@gmail.com",
    description="NMR parameter optimisation in TopSpin",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yongrenjie/poptpy",
    include_package_data=True,
    packages=find_packages(exclude=["tests"]),
    classifiers=[
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    install_requires=["numpy>=1.17.0",
                      "Py-BOBYQA",
                      "pandas"
                      ],
    cmdclass={"install": TopSpinInstall,
              "notopspin": noTopSpinInstall,
    }
)
