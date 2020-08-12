import platform
import subprocess
from pathlib import Path
from distutils.dir_util import copy_tree, remove_tree
from distutils.file_util import copy_file

import pytest

hostname = platform.node()
pkg_toplevel_dir = Path(__file__).parents[1].resolve()

# Have to hardcode these. I don't see a way around it.
hostname_to_tspath_dict = {
    "jymbp": Path("/opt/topspin4.0.9/exp/stan/nmr/py/user/"),
    "CARP-CRL": Path(r"C:\Bruker\TopSpin4.0.7\exp\stan\nmr\py\user"),
}


def delete_file_force(path):
    """Equivalent to path.unlink(missing_ok=True), but that parameter is
    only in Python 3.8."""
    try:
        path.unlink()
    except FileNotFoundError:
        pass


@pytest.mark.skipif(all(host not in platform.node()
                        for host in hostname_to_tspath_dict.keys()),
                    reason=f"Testing on {hostname} is not supported.")
def test_topspin_installation(tmpdir):
    # Path to TopSpin py/user.
    for host in hostname_to_tspath_dict.keys():
        if host in platform.node():
            ts_path = hostname_to_tspath_dict[host]
    # Make sure it's right
    assert ts_path.is_dir()

    # Clear out the existing installation of poise
    delete_file_force(ts_path / "poise.py")
    remove_tree(str(ts_path / "poise_backend"))
    assert not (ts_path / "poise.py").exists()
    assert not (ts_path / "poise_backend").exists()

    # Copy package to a temporary directory
    tmpdir = Path(tmpdir)
    tmpdir_poise = tmpdir / "nmrpoise"
    ts_install_script = pkg_toplevel_dir / "topspin_install.py"
    poise_folder = pkg_toplevel_dir / "nmrpoise"
    copy_file(str(ts_install_script), str(tmpdir))
    copy_tree(str(poise_folder), str(tmpdir_poise))

    # Run the installation script in the temporary directory
    new_ts_install_script = tmpdir / "topspin_install.py"
    subprocess.run(["python3", str(new_ts_install_script)])

    # Check whether the files were installed to TopSpin correctly
    assert (ts_path / "poise.py").exists()
    assert (ts_path / "poise_backend").exists()
    assert (ts_path / "poise_backend" / "backend.py").exists()
    assert (ts_path / "poise_backend" / "optpoise.py").exists()
    assert (ts_path / "poise_backend" / "cost_functions").exists()
    assert (ts_path / "poise_backend" / "routines").exists()
