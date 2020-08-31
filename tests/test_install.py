import platform
import subprocess
from pathlib import Path
from distutils.dir_util import copy_tree, remove_tree
from distutils.file_util import copy_file

import pytest

hostname = platform.node()
pkg_toplevel_dir = Path(__file__).parents[1].resolve()

# Have to hardcode these. I don't see a way around it.
hostname_to_tspath = {
    "Empoleon": Path("/opt/topspin4.0.9/exp/stan/nmr"),
    "CARP-CRL": Path(r"C:\Bruker\TopSpin4.0.7\exp\stan\nmr"),
}


def delete_file_force(path):
    """Equivalent to path.unlink(missing_ok=True), but that parameter is
    only in Python 3.8."""
    try:
        path.unlink()
    except FileNotFoundError:
        pass


@pytest.mark.skipif(all(host not in platform.node()
                        for host in hostname_to_tspath.keys()),
                    reason=f"Testing on {hostname} is not supported.")
def test_topspin_installation(tmpdir):
    # Path to TopSpin py/user, and /au/src/user.
    for host in hostname_to_tspath.keys():
        if host in platform.node():
            py_user_path = hostname_to_tspath[host] / "py" / "user"
            au_src_user_path = hostname_to_tspath[host] / "au" / "src" / "user"
    # Make sure it's right
    assert py_user_path.is_dir()

    # Clear out the existing installation of poise
    delete_file_force(py_user_path / "poise.py")
    remove_tree(str(py_user_path / "poise_backend"))
    delete_file_force(au_src_user_path / "poise_1d")
    delete_file_force(au_src_user_path / "poise_2d")
    assert not (py_user_path / "poise.py").exists()
    assert not (py_user_path / "poise_backend").exists()
    assert not (au_src_user_path / "poise_1d").exists()
    assert not (au_src_user_path / "poise_2d").exists()

    # Copy package to a temporary directory
    tmpdir = Path(tmpdir)
    tmpdir_poise = tmpdir / "nmrpoise"
    poise_folder = pkg_toplevel_dir / "nmrpoise"
    ts_install_script = poise_folder / "topspin_install.py"
    copy_file(str(ts_install_script), str(tmpdir))
    copy_tree(str(poise_folder), str(tmpdir_poise))

    # Run the installation script in the temporary directory
    new_ts_install_script = tmpdir_poise / "topspin_install.py"
    subprocess.run(["python3", str(new_ts_install_script)])

    # Check whether the files were installed to TopSpin correctly
    assert (py_user_path / "poise.py").exists()
    assert (py_user_path / "poise_backend").exists()
    assert (py_user_path / "poise_backend" / "backend.py").exists()
    assert (py_user_path / "poise_backend" / "optpoise.py").exists()
    assert (py_user_path / "poise_backend" / "costfunctions.py").exists()
    assert (py_user_path / "poise_backend" / "cfhelpers.py").exists()
    assert (py_user_path / "poise_backend" / "routines").exists()
    assert (au_src_user_path / "poise_1d").exists()
    assert (au_src_user_path / "poise_2d").exists()
