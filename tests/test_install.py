import sys
import time
import platform
import subprocess
from pathlib import Path
from distutils.dir_util import copy_tree, remove_tree
from distutils.file_util import copy_file

import pytest

identifier = f"{platform.node()}_{sys.platform}"
pkg_toplevel_dir = Path(__file__).parents[1].resolve()

identifier_to_tspath = {
    "Empoleon_darwin": Path("/opt/topspin4.1.3/exp/stan/nmr"),
    "Empoleon.local_darwin": Path("/opt/topspin4.1.3/exp/stan/nmr"),
    # "CARP-CRL_linux": Path("/mnt/c/Bruker/TopSpin4.0.7/exp/stan/nmr"),
    "CARP-CRL_win32": Path(r"C:\Bruker\TopSpin4.0.7\exp\stan\nmr"),
}


def delete_file_force(path):
    """Equivalent to path.unlink(missing_ok=True), but that parameter is
    only in Python 3.8."""
    try:
        path.unlink()
    except FileNotFoundError:
        pass


@pytest.mark.skipif(identifier not in identifier_to_tspath,
                    reason=f"Testing on {identifier} is not supported.")
def test_topspin_installation(tmpdir):
    # Path to TopSpin py/user, and /au/src/user.
    py_user_path = identifier_to_tspath[identifier] / "py" / "user"
    au_src_user_path = identifier_to_tspath[identifier] / "au" / "src" / "user"
    # Make sure it's right
    assert py_user_path.is_dir()

    # Clear out the existing installation of poise
    delete_file_force(py_user_path / "poise.py")
    remove_tree(str(py_user_path / "poise_backend"))
    delete_file_force(au_src_user_path / "poise_1d")
    delete_file_force(au_src_user_path / "poise_2d")
    delete_file_force(au_src_user_path / "poise_1d_noapk")
    delete_file_force(au_src_user_path / "poisecal")
    assert not (py_user_path / "poise.py").exists()
    assert not (py_user_path / "poise_backend").exists()
    assert not (au_src_user_path / "poise_1d").exists()
    assert not (au_src_user_path / "poise_2d").exists()
    assert not (au_src_user_path / "poise_1d_noapk").exists()
    assert not (au_src_user_path / "poisecal").exists()

    # Copy package to a temporary directory
    tmpdir = Path(tmpdir)
    tmpdir_poise = tmpdir / "nmrpoise"
    poise_folder = pkg_toplevel_dir / "nmrpoise"
    ts_install_script = poise_folder / "topspin_install.py"
    copy_file(str(ts_install_script), str(tmpdir))
    copy_tree(str(poise_folder), str(tmpdir_poise))

    # Run the installation script in the temporary directory
    new_ts_install_script = tmpdir_poise / "topspin_install.py"
    subprocess.run([sys.executable, str(new_ts_install_script)])

    # Check whether the files were installed to TopSpin correctly
    assert (py_user_path / "poise.py").exists()
    assert (py_user_path / "poise_backend").exists()
    assert (py_user_path / "poise_backend" / "backend.py").exists()
    assert (py_user_path / "poise_backend" / "optpoise.py").exists()
    assert (py_user_path / "poise_backend" / "costfunctions.py").exists()
    assert (py_user_path / "poise_backend" / "cfhelpers.py").exists()
    assert (py_user_path / "poise_backend" / "example_routines").exists()
    assert (au_src_user_path / "poise_1d").exists()
    assert (au_src_user_path / "poise_2d").exists()
    assert (au_src_user_path / "poise_1d_noapk").exists()
    assert (au_src_user_path / "poisecal").exists()
