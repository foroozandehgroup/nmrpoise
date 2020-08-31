from pathlib import Path

import numpy as np

from nmrpoise.poise_backend import backend as be


def test_scaleby_bounds():
    rng = np.random.default_rng()
    # Generate and sort a random 3x20 matrix.
    mat = rng.uniform(low=-500, high=500, size=(3, 20))
    mat.sort(axis=0)
    lb, val, ub = mat[0], mat[1], mat[2]
    # Generate random percentage tolerances.
    tol = rng.uniform(low=0.01, high=0.5, size=(1, 20))
    # Convert to actual tolerances.
    tol = tol * (ub - lb)
    # Scale.
    sval, slb, sub, stol = be.scale(val, lb, ub, tol)
    # Make sure that lb's and ub's are zeros and ones.
    assert np.allclose(slb, np.zeros(np.shape(val)))
    assert np.allclose(sub, np.ones(np.shape(val)))
    # Make sure that unscaling gives the right things.
    usval = be.unscale(sval, lb, ub, tol)
    assert np.allclose(usval, val)


def test_scaleby_tols():
    rng = np.random.default_rng()
    # Generate and sort a random 3x20 matrix.
    mat = rng.uniform(low=-500, high=500, size=(3, 20))
    mat.sort(axis=0)
    lb, val, ub = mat[0], mat[1], mat[2]
    # Generate random percentage tolerances.
    tol = rng.uniform(low=0.01, high=0.5, size=(1, 20))
    # Convert to actual tolerances.
    tol = tol * (ub - lb)
    # Scale by tolerances.
    sval, slb, sub, stol = be.scale(val, lb, ub, tol, scaleby="tols")
    # Make sure that lb's and tol's are 0's and 0.03's.
    assert np.allclose(slb, np.zeros(np.shape(val)))
    assert np.allclose(stol, 0.03 * np.ones(np.shape(val)))
    # Check that unscaling gives back the same values.
    usval = be.unscale(sval, lb, ub, tol, scaleby="tols")
    assert np.allclose(usval, val)


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
