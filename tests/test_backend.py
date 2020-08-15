from pathlib import Path

import numpy as np
import pytest

import nmrpoise.poise_backend.backend as be
from nmrpoise.poise_backend.backend import Routine


def makep(expno, procno):
    return (Path(__file__).parent / "test_data" /
            str(expno) / "pdata" / str(procno))


def test_ppm_to_point():
    p_spec = makep(1, 1)
    assert be._ppm_to_point(9, p_spec=p_spec) is None  # out of range
    assert be._ppm_to_point(6, p_spec=p_spec) == 19658
    assert be._ppm_to_point(3, p_spec=p_spec) == 39324
    # This one is mildly off. 58990 is the "index" in TopSpin, but ppm_to_point
    # calculates an index of 58989. See docstring of ppm_to_point.
    assert be._ppm_to_point(0, p_spec=p_spec) == 58990 - 1
    assert be._ppm_to_point(-3, p_spec=p_spec) is None
    p_spec = makep(101, 1)
    assert be._ppm_to_point(170, axis=0, p_spec=p_spec) is None  # out of range
    assert be._ppm_to_point(123.1, axis=0, p_spec=p_spec) == 545  # 13C
    assert be._ppm_to_point(7.083, axis=1, p_spec=p_spec) == 402  # 1H
    with pytest.raises(ValueError):   # Nonexistent axis
        be._ppm_to_point(100, axis=2, p_spec=p_spec)
    with pytest.raises(ValueError):
        be._ppm_to_point(100, axis="goose", p_spec=p_spec)


def test_getpar():
    # 1D tests
    p_spec = makep(5, 1)
    assert be.getpar("p0", p_spec=p_spec) == 15
    assert be.getpar("p1", p_spec=p_spec) == 15
    assert be.getpar("p2", p_spec=p_spec) == 30
    assert be.getpar("P2", p_spec=p_spec) == 30
    assert be.getpar("p 2", p_spec=p_spec) == 30
    assert be.getpar("P 2", p_spec=p_spec) == 30
    assert round(be.getpar("cnst20", p_spec=p_spec), 4) == 25.6466
    assert round(be.getpar("spw 20", p_spec=p_spec), 8) == 0.00076827
    assert round(be.getpar("PLW 1", p_spec=p_spec), 3) == 31.537
    assert be.getpar("pulprog", p_spec=p_spec) is None

    assert be.getpar("si", p_spec=p_spec) == 65536
    assert be.getpar("lb", p_spec=p_spec) == 0.30
    assert round(be.getpar("phc0", p_spec=p_spec), 3) == 283.742
    assert round(be.getpar("PHC0", p_spec=p_spec), 3) == 283.742
    assert round(be.getpar("phc 0", p_spec=p_spec), 3) == 283.742
    assert round(be.getpar("PHC 0", p_spec=p_spec), 3) == 283.742
    assert round(be.getpar("PHC1", p_spec=p_spec), 3) == -10.292
    assert be.getpar("wdw", p_spec=p_spec) == 1
    assert be.getpar("ft_mod", p_spec=p_spec) == 6

    assert be.getpar("penguin", p_spec=p_spec) is None

    # 2D tests
    p_spec = makep(101, 1)
    assert np.array_equal(be.getpar("SI", p_spec=p_spec), (1024, 1024))
    assert be.getpar("NS", p_spec=p_spec) == 1
    assert round(be.getpar("SW", p_spec=p_spec)[0], 4) == 60.0127
    assert round(be.getpar("SW", p_spec=p_spec)[1], 4) == 10.0130


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
    p_cf_dir = (Path(__file__).parents[1] / "nmrpoise" /
                "poise_backend" / "cost_functions")

    routine, cf = be.get_routine_cf(routine_id, p_routine_dir, p_cf_dir)
    assert routine.name == "p1cal"
    assert routine.pars == ["p1"]
    assert routine.lb == [40]
    assert routine.ub == [56]
    assert routine.init == [48]
    assert routine.tol == [0.2]
    assert routine.cf == "minabsint"
    assert routine.au == "poise_1d"


def test_get1d_real():
    p_spec = makep(1, 1)
    real = be.get1d_real(p_spec=p_spec)
    npff = np.fromfile(p_spec / "1r", dtype=np.int32)
    assert be.getpar("NC_proc", p_spec=p_spec) == -8
    assert np.array_equal(real, npff * (2 ** -8))

    # Check whether bounds work
    left, right = 6, 4
    lpoint = be._ppm_to_point(left, p_spec=p_spec)
    rpoint = be._ppm_to_point(right, p_spec=p_spec)
    lpoint, rpoint = sorted([lpoint, rpoint])  # if left < right
    subarray = be.get1d_real(bounds="4..6", p_spec=p_spec)
    assert np.array_equal(subarray, npff[lpoint:rpoint + 1] * (2 ** -8))
    subarray = be.get1d_real(bounds=(4, 6), p_spec=p_spec)
    assert np.array_equal(subarray, npff[lpoint:rpoint + 1] * (2 ** -8))

    left, right = 6, None
    lpoint = be._ppm_to_point(left, p_spec=p_spec)
    si = int(be.getpar("si", p_spec=p_spec))
    subarray = be.get1d_real(bounds="..6", p_spec=p_spec)
    assert np.array_equal(subarray, npff[lpoint:si] * (2 ** -8))
    subarray = be.get1d_real(bounds=(None, 6), p_spec=p_spec)
    assert np.array_equal(subarray, npff[lpoint:si] * (2 ** -8))

    left, right = None, 6
    rpoint = be._ppm_to_point(right, p_spec=p_spec)
    subarray = be.get1d_real(bounds="6..", p_spec=p_spec)
    assert np.array_equal(subarray, npff[0:rpoint + 1] * (2 ** -8))
    subarray = be.get1d_real(bounds=(6, None), p_spec=p_spec)
    assert np.array_equal(subarray, npff[0:rpoint + 1] * (2 ** -8))


def test_get1d_imag():
    p_spec = makep(1, 1)
    imag = be.get1d_imag(p_spec=p_spec)
    npff = np.fromfile(p_spec / "1i", dtype=np.int32)
    assert be.getpar("NC_proc", p_spec=p_spec) == -8
    assert np.array_equal(imag, npff * (2 ** -8))

    # Check whether bounds work
    left, right = 6, 4
    lpoint = be._ppm_to_point(left, p_spec=p_spec)
    rpoint = be._ppm_to_point(right, p_spec=p_spec)
    lpoint, rpoint = sorted([lpoint, rpoint])  # if left < right
    subarray = be.get1d_imag(bounds="4..6", p_spec=p_spec)
    assert np.array_equal(subarray, npff[lpoint:rpoint + 1] * (2 ** -8))

    left, right = 6, None
    lpoint = be._ppm_to_point(left, p_spec=p_spec)
    si = int(be.getpar("si", p_spec=p_spec))
    subarray = be.get1d_imag(bounds="..6", p_spec=p_spec)
    assert np.array_equal(subarray, npff[lpoint:si] * (2 ** -8))

    left, right = None, 6
    rpoint = be._ppm_to_point(right, p_spec=p_spec)
    subarray = be.get1d_imag(bounds="6..", p_spec=p_spec)
    assert np.array_equal(subarray, npff[0:rpoint + 1] * (2 ** -8))


def test_get1d_fid():
    p_spec = makep(1, 1)
    fid = be.get1d_fid(p_spec)

    npff = np.fromfile(p_spec.parents[1] / "fid", dtype=np.int32)

    assert np.array_equal(np.real(fid), npff[0::2])
    assert np.array_equal(np.imag(fid), npff[1::2])


def test_get2d_rr():
    p_spec = makep(101, 1)
    spec = be.get2d_rr(p_spec=p_spec)
    assert spec.shape == (1024, 1024)

    spec = be.get2d_rr(f1_bounds="", f2_bounds="6..8", p_spec=p_spec)
    assert spec.shape == (1024, 205)

    spec = be.get2d_rr(f1_bounds="", f2_bounds=(6, 8), p_spec=p_spec)
    assert spec.shape == (1024, 205)


def test_deco_count():
    @be.deco_count
    def peep():
        print("PEEP")

    n = 10
    for i in range(n):
        peep()
    assert peep.calls == n


def test_send_values(capsys):
    be.send_values([0.1, 0.2, 0.3, 0.4, 0.5])
    assert capsys.readouterr().out == "values: 0.1 0.2 0.3 0.4 0.5\n"
