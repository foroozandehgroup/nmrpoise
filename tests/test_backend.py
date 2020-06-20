from pathlib import Path

import numpy as np

import poptpy.poptpy_backend.backend as be
from poptpy.poptpy_backend.backend import Routine


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


def test_get_routine_cf():
    routine_id = "test_routine"   # serialised by TS 4.0.8, macOS 10.15.5
    p_routine_dir = Path(__file__).parent / "test_data"
    p_cf_dir = (Path(__file__).parents[1] / "poptpy" /
                "poptpy_backend" / "cost_functions")

    routine, cf = be.get_routine_cf(routine_id, p_routine_dir, p_cf_dir)
    assert routine.name == "test_routine"
    assert routine.pars == ["p1", "cnst20"]
    assert routine.lb == [10, 0.2]
    assert routine.ub == [20, 0.4]
    assert routine.init == [15, 0.3]
    assert routine.tol == [0.2, 0.00015]
    assert routine.cf == "specdiff"
    assert cf.__doc__.strip() == ("Obtains the distance between the current "
                                  "spectrum and a target spectrum.")


def test_get_real_spectrum():
    p_spec = makep(1, 1)
    real = be.get_real_spectrum(p_spec=p_spec)
    npff = np.fromfile(p_spec / "1r", dtype=np.int32)
    assert be.getpar("NC_proc", p_spec) == -8
    assert np.array_equal(real, npff * (2 ** -8))

    # Check whether bounds work
    left, right = 4, 6
    lpoint = be.ppm_to_point(left, p_spec)
    rpoint = be.ppm_to_point(right, p_spec)
    lpoint, rpoint = sorted([lpoint, rpoint])  # if left < right
    subarray = be.get_real_spectrum(left=left, right=right, p_spec=p_spec)
    assert np.array_equal(subarray, npff[lpoint:rpoint + 1] * (2 ** -8))

    left, right = 6, 4
    lpoint = be.ppm_to_point(left, p_spec)
    rpoint = be.ppm_to_point(right, p_spec)
    lpoint, rpoint = sorted([lpoint, rpoint])  # if left < right
    subarray = be.get_real_spectrum(left=left, right=right, p_spec=p_spec)
    assert np.array_equal(subarray, npff[lpoint:rpoint + 1] * (2 ** -8))

    left, right = 6, None
    lpoint = be.ppm_to_point(left, p_spec)
    si = int(be.getpar("si", p_spec))
    subarray = be.get_real_spectrum(left=left, right=right, p_spec=p_spec)
    assert np.array_equal(subarray, npff[lpoint:si] * (2 ** -8))

    left, right = None, 6
    rpoint = be.ppm_to_point(right, p_spec)
    subarray = be.get_real_spectrum(left=left, right=right, p_spec=p_spec)
    assert np.array_equal(subarray, npff[0:rpoint + 1] * (2 ** -8))


def test_get_imag_spectrum():
    p_spec = makep(1, 1)
    imag = be.get_imag_spectrum(p_spec=p_spec)
    npff = np.fromfile(p_spec / "1i", dtype=np.int32)
    assert be.getpar("NC_proc", p_spec) == -8
    assert np.array_equal(imag, npff * (2 ** -8))

    # Check whether bounds work
    left, right = 4, 6
    lpoint = be.ppm_to_point(left, p_spec)
    rpoint = be.ppm_to_point(right, p_spec)
    lpoint, rpoint = sorted([lpoint, rpoint])  # if left < right
    subarray = be.get_imag_spectrum(left=left, right=right, p_spec=p_spec)
    assert np.array_equal(subarray, npff[lpoint:rpoint + 1] * (2 ** -8))

    left, right = 6, 4
    lpoint = be.ppm_to_point(left, p_spec)
    rpoint = be.ppm_to_point(right, p_spec)
    lpoint, rpoint = sorted([lpoint, rpoint])  # if left < right
    subarray = be.get_imag_spectrum(left=left, right=right, p_spec=p_spec)
    assert np.array_equal(subarray, npff[lpoint:rpoint + 1] * (2 ** -8))

    left, right = 6, None
    lpoint = be.ppm_to_point(left, p_spec)
    si = int(be.getpar("si", p_spec))
    subarray = be.get_imag_spectrum(left=left, right=right, p_spec=p_spec)
    assert np.array_equal(subarray, npff[lpoint:si] * (2 ** -8))

    left, right = None, 6
    rpoint = be.ppm_to_point(right, p_spec)
    subarray = be.get_imag_spectrum(left=left, right=right, p_spec=p_spec)
    assert np.array_equal(subarray, npff[0:rpoint + 1] * (2 ** -8))


def test_get_fid():
    p_spec = makep(1, 1)
    fid = be.get_fid(p_spec)

    npff = np.fromfile(p_spec.parents[1] / "fid", dtype=np.int32)

    assert np.array_equal(np.real(fid), npff[0::2])
    assert np.array_equal(np.imag(fid), npff[1::2])


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
