import os
from pathlib import Path

import numpy as np

from nmrpoise.poise_backend import backend as be


def test_get_routine_cf():
    routine_id = "p1cal"   # serialised on AV600
    p_routine_dir = Path(__file__).parent / "test_data"

    routine, cf = be.get_routine_cf(routine_id, p_routine_dir)
    assert routine.name == "p1cal"
    assert routine.pars == ["p1"]
    assert routine.lb == [40]
    assert routine.ub == [56]
    assert routine.init == [48]
    assert routine.tol == [0.2]
    assert routine.cf == "minabsint"
    assert routine.au == "poise_1d"


def test_pidfile():
    pid = os.getpid()
    # We need to be careful with this. pidfile() creates itself in the
    # same directory as backend.py, wherever it is. Since tox testing uses
    # the local copy, we need to check the poise_backend directory.
    pid_fname = (Path(__file__).parents[1] / "nmrpoise" / "poise_backend"
                 / (".pid" + str(pid)))
    # Check that the file exists inside the context manager block.
    with be.pidfile() as _:
        assert pid_fname.exists()
    # Check that it is deleted.
    assert not pid_fname.exists()
