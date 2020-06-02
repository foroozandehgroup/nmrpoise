from pathlib import Path

import numpy as np

import poptpy.poptpy_backend.backend as be


def makep(expno, procno):
    return (Path(__file__).parent / "test_data" /
            str(expno) / "pdata" / str(procno))


def test_ppm_to_point():
    p_spec = makep(1, 1)
    assert be.ppm_to_point(9, p_spec) is None  # out of range
    assert be.ppm_to_point(6, p_spec) == 19658
    assert be.ppm_to_point(3, p_spec) == 39324
    # This one is mildly off. 58990 is the "index" in TopSpin, but ppm_to_point
    # calculates an index of 58989. See docstring of ppm_to_point.
    assert be.ppm_to_point(0, p_spec) == 58990 - 1
    assert be.ppm_to_point(-3, p_spec) is None


def test_get_acqu_par():
    p_spec = makep(5, 1)
    assert be.get_acqu_par("p0", p_spec) == 15
    assert be.get_acqu_par("p1", p_spec) == 15
    assert be.get_acqu_par("p2", p_spec) == 30
    # Check some misspellings
    assert be.get_acqu_par("P2", p_spec) == 30
    assert be.get_acqu_par("p 2", p_spec) == 30
    assert be.get_acqu_par("P 2", p_spec) == 30
    # When you type 'cnst20' in TopSpin, you are told that it's 25.6466.
    # But the *actual* value as stored in acqus is 25.64659, hence the round()
    assert round(be.get_acqu_par("cnst20", p_spec), 4) == 25.6466
    # Same with these.
    assert round(be.get_acqu_par("spw 20", p_spec), 8) == 0.00076827
    assert round(be.get_acqu_par("PLW 1", p_spec), 3) == 31.537
    # get_acqu_par refuses to read strings.
    assert be.get_acqu_par("pulprog", p_spec) is None
    # A nonexistent parameter
    assert be.get_acqu_par("penguin", p_spec) is None


def test_get_proc_par():
    p_spec = makep(5, 1)
    assert be.get_proc_par("si", p_spec) == 65536
    assert be.get_proc_par("lb", p_spec) == 0.30
    assert round(be.get_proc_par("phc0", p_spec), 3) == 283.742
    assert round(be.get_proc_par("PHC0", p_spec), 3) == 283.742
    assert round(be.get_proc_par("phc 0", p_spec), 3) == 283.742
    assert round(be.get_proc_par("PHC 0", p_spec), 3) == 283.742
    assert round(be.get_proc_par("PHC1", p_spec), 3) == -10.292
    # This is the second option from a dropdown list.
    # TopSpin stores the selection as a number starting from 0.
    assert be.get_proc_par("wdw", p_spec) == 1
    # And the seventh option.
    assert be.get_proc_par("ft_mod", p_spec) == 6
    # A nonexistent parameter
    assert be.get_proc_par("penguin", p_spec) is None


def test_getpar():
    # The same tests as get_acqu_par and get_proc_par.
    p_spec = makep(5, 1)
    assert be.getpar("p0", p_spec) == 15
    assert be.getpar("p1", p_spec) == 15
    assert be.getpar("p2", p_spec) == 30
    assert be.getpar("P2", p_spec) == 30
    assert be.getpar("p 2", p_spec) == 30
    assert be.getpar("P 2", p_spec) == 30
    assert round(be.getpar("cnst20", p_spec), 4) == 25.6466
    assert round(be.getpar("spw 20", p_spec), 8) == 0.00076827
    assert round(be.getpar("PLW 1", p_spec), 3) == 31.537
    assert be.getpar("pulprog", p_spec) is None

    assert be.getpar("si", p_spec) == 65536
    assert be.getpar("lb", p_spec) == 0.30
    assert round(be.getpar("phc0", p_spec), 3) == 283.742
    assert round(be.getpar("PHC0", p_spec), 3) == 283.742
    assert round(be.getpar("phc 0", p_spec), 3) == 283.742
    assert round(be.getpar("PHC 0", p_spec), 3) == 283.742
    assert round(be.getpar("PHC1", p_spec), 3) == -10.292
    assert be.getpar("wdw", p_spec) == 1
    assert be.getpar("ft_mod", p_spec) == 6

    assert be.getpar("penguin", p_spec) is None


def test_scale_unscale():
    rng = np.random.default_rng()
    # Generate and sort a random 3x20 matrix.
    mat = rng.uniform(low=-500, high=500, size=(3, 20))
    mat.sort(axis=0)
    lb, val, ub = mat[0], mat[1], mat[2]
    # Make sure that scaling and unscaling val gives val back again.
    assert np.allclose(be.unscale(be.scale(val, lb, ub), lb, ub), val)
