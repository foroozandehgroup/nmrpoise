"""
SPDX-License-Identifier: GPL-3.0-or-later
"""

import sys
import subprocess
from pathlib import Path
from setuptools import setup, find_packages
from setuptools.command.install import install


class TopSpinInstall(install):
    def run(self):
        p = Path(__file__).parent.resolve()
        p_install = p / "nmrpoise" / "topspin_install.py"
        subprocess.run([sys.executable, str(p_install)], check=True)
        super().run()


class noTopSpinInstall(install):
    """Doesn't install to TopSpin. Useful for testing."""
    pass


with open("README.md", "r") as fp:
    long_description = fp.read()

# Read the version number in as __version__
exec(open('nmrpoise/_version.py').read())

setup(
    name="nmrpoise",
    version=__version__,
    author="Jonathan Yong",
    author_email="jonathan.yong@chem.ox.ac.uk",
    description=("Parameter Optimisation by Iterative Spectral Evaluation, "
                 "a TopSpin-compatible NMR package"),
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/foroozandehgroup/nmrpoise",
    packages=[
        "nmrpoise",
        "nmrpoise.poise_backend",
        "nmrpoise.py",
        "nmrpoise.au",
    ],
    include_package_data=True,
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
    },
    entry_points={
        "console_scripts": [
            "poise_ts = nmrpoise.topspin_install:main",
            "poise_addons = nmrpoise.topspin_install:install_addons",
        ]
    },
)
