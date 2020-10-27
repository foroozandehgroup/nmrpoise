from pathlib import Path

import numpy as np
import pytest

import nmrpoise.poise_backend.cfhelpers as cfh
from nmrpoise.poise_backend.backend import (Routine, scale, unscale)


def test_make_p_spec():
    ps = cfh.make_p_spec(path=(Path(__file__).parent / "test_data"),
                         expno=1, procno=1)
    assert ps == (Path(__file__).parent / "test_data" / "1"
                  / "pdata" / "1")


def makep(expno, procno):
    return cfh.make_p_spec(path=(Path(__file__).parent / "test_data"),
                           expno=expno,
                           procno=procno)


def test_ppm_to_point():
    p_spec = makep(1, 1)
    assert cfh._ppm_to_point(9, p_spec=p_spec) is None  # out of range
    assert cfh._ppm_to_point(6, p_spec=p_spec) == 19658
    assert cfh._ppm_to_point(3, p_spec=p_spec) == 39324
    # This one is mildly off. 58990 is the "index" in TopSpin, but ppm_to_point
    # calculates an index of 58989. See docstring of ppm_to_point.
    assert cfh._ppm_to_point(0, p_spec=p_spec) == 58990 - 1
    assert cfh._ppm_to_point(-3, p_spec=p_spec) is None
    p_spec = makep(101, 1)
    assert cfh._ppm_to_point(170, axis=0, p_spec=p_spec) is None
    assert cfh._ppm_to_point(123.1, axis=0, p_spec=p_spec) == 545  # 13C
    assert cfh._ppm_to_point(7.083, axis=1, p_spec=p_spec) == 402  # 1H
    with pytest.raises(ValueError):   # Nonexistent axis
        cfh._ppm_to_point(100, axis=2, p_spec=p_spec)
    with pytest.raises(ValueError):
        cfh._ppm_to_point(100, axis="goose", p_spec=p_spec)


def test_getpar():
    # 1D tests
    p_spec = makep(5, 1)
    assert cfh.getpar("p0", p_spec=p_spec) == 15
    assert cfh.getpar("p1", p_spec=p_spec) == 15
    assert cfh.getpar("p2", p_spec=p_spec) == 30
    assert cfh.getpar("P2", p_spec=p_spec) == 30
    assert cfh.getpar("p 2", p_spec=p_spec) == 30
    assert cfh.getpar("P 2", p_spec=p_spec) == 30
    assert round(cfh.getpar("cnst20", p_spec=p_spec), 4) == 25.6466
    assert round(cfh.getpar("spw 20", p_spec=p_spec), 8) == 0.00076827
    assert round(cfh.getpar("PLW 1", p_spec=p_spec), 3) == 31.537
    assert cfh.getpar("pulprog", p_spec=p_spec) is None

    assert cfh.getpar("si", p_spec=p_spec) == 65536
    assert cfh.getpar("lb", p_spec=p_spec) == 0.30
    assert round(cfh.getpar("phc0", p_spec=p_spec), 3) == 283.742
    assert round(cfh.getpar("PHC0", p_spec=p_spec), 3) == 283.742
    assert round(cfh.getpar("phc 0", p_spec=p_spec), 3) == 283.742
    assert round(cfh.getpar("PHC 0", p_spec=p_spec), 3) == 283.742
    assert round(cfh.getpar("PHC1", p_spec=p_spec), 3) == -10.292
    assert cfh.getpar("wdw", p_spec=p_spec) == 1
    assert cfh.getpar("ft_mod", p_spec=p_spec) == 6

    assert cfh.getpar("penguin", p_spec=p_spec) is None

    # 2D tests
    p_spec = makep(101, 1)
    assert np.array_equal(cfh.getpar("SI", p_spec=p_spec), (1024, 1024))
    assert cfh.getpar("NS", p_spec=p_spec) == 1
    assert round(cfh.getpar("SW", p_spec=p_spec)[0], 4) == 60.0127
    assert round(cfh.getpar("SW", p_spec=p_spec)[1], 4) == 10.0130


def test_getndim():
    # 1D
    p_spec = makep(5, 1)
    assert cfh.getndim(p_spec=p_spec) == 1
    # 2D
    p_spec = makep(101, 1)
    assert cfh.getndim(p_spec=p_spec) == 2


def test_get1d_real():
    p_spec = makep(1, 1)
    real = cfh.get1d_real(p_spec=p_spec)
    npff = np.fromfile(p_spec / "1r", dtype=np.int32)
    assert cfh.getpar("NC_proc", p_spec=p_spec) == -8
    assert np.array_equal(real, npff * (2 ** -8))

    # Check whether bounds work
    left, right = 6, 4
    lpoint = cfh._ppm_to_point(left, p_spec=p_spec)
    rpoint = cfh._ppm_to_point(right, p_spec=p_spec)
    lpoint, rpoint = sorted([lpoint, rpoint])  # if left < right
    subarray = cfh.get1d_real(bounds="4..6", p_spec=p_spec)
    assert np.array_equal(subarray, npff[lpoint:rpoint + 1] * (2 ** -8))
    subarray = cfh.get1d_real(bounds=(4, 6), p_spec=p_spec)
    assert np.array_equal(subarray, npff[lpoint:rpoint + 1] * (2 ** -8))

    left, right = 6, None
    lpoint = cfh._ppm_to_point(left, p_spec=p_spec)
    si = int(cfh.getpar("si", p_spec=p_spec))
    subarray = cfh.get1d_real(bounds="..6", p_spec=p_spec)
    assert np.array_equal(subarray, npff[lpoint:si] * (2 ** -8))
    subarray = cfh.get1d_real(bounds=(None, 6), p_spec=p_spec)
    assert np.array_equal(subarray, npff[lpoint:si] * (2 ** -8))

    left, right = None, 6
    rpoint = cfh._ppm_to_point(right, p_spec=p_spec)
    subarray = cfh.get1d_real(bounds="6..", p_spec=p_spec)
    assert np.array_equal(subarray, npff[0:rpoint + 1] * (2 ** -8))
    subarray = cfh.get1d_real(bounds=(6, None), p_spec=p_spec)
    assert np.array_equal(subarray, npff[0:rpoint + 1] * (2 ** -8))


def test_get1d_imag():
    p_spec = makep(1, 1)
    imag = cfh.get1d_imag(p_spec=p_spec)
    npff = np.fromfile(p_spec / "1i", dtype=np.int32)
    assert cfh.getpar("NC_proc", p_spec=p_spec) == -8
    assert np.array_equal(imag, npff * (2 ** -8))

    # Check whether bounds work
    left, right = 6, 4
    lpoint = cfh._ppm_to_point(left, p_spec=p_spec)
    rpoint = cfh._ppm_to_point(right, p_spec=p_spec)
    lpoint, rpoint = sorted([lpoint, rpoint])  # if left < right
    subarray = cfh.get1d_imag(bounds="4..6", p_spec=p_spec)
    assert np.array_equal(subarray, npff[lpoint:rpoint + 1] * (2 ** -8))

    left, right = 6, None
    lpoint = cfh._ppm_to_point(left, p_spec=p_spec)
    si = int(cfh.getpar("si", p_spec=p_spec))
    subarray = cfh.get1d_imag(bounds="..6", p_spec=p_spec)
    assert np.array_equal(subarray, npff[lpoint:si] * (2 ** -8))

    left, right = None, 6
    rpoint = cfh._ppm_to_point(right, p_spec=p_spec)
    subarray = cfh.get1d_imag(bounds="6..", p_spec=p_spec)
    assert np.array_equal(subarray, npff[0:rpoint + 1] * (2 ** -8))


def test_get1d_fid():
    p_spec = makep(1, 1)
    fid = cfh.get1d_fid(p_spec)

    npff = np.fromfile(p_spec.parents[1] / "fid", dtype=np.int32)

    assert np.array_equal(np.real(fid), npff[0::2])
    assert np.array_equal(np.imag(fid), npff[1::2])


def test_get2d_rr():
    p_spec = makep(101, 1)
    spec = cfh.get2d_rr(p_spec=p_spec)
    assert spec.shape == (1024, 1024)

    spec = cfh.get2d_rr(f1_bounds="", f2_bounds="6..8", p_spec=p_spec)
    assert spec.shape == (1024, 205)

    spec = cfh.get2d_rr(f1_bounds="", f2_bounds=(6, 8), p_spec=p_spec)
    assert spec.shape == (1024, 205)
