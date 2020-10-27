from pathlib import Path

from nmrpoise.poise_backend.shared import _g
from nmrpoise.poise_backend import costfunctions as cf
from nmrpoise.poise_backend import cfhelpers as cfh


def makep(expno, procno):
    return cfh.make_p_spec(path=(Path(__file__).parent / "test_data"),
                           expno=expno,
                           procno=procno)


def test_noe_1d():
    _g.p_spectrum = makep(7, 1)
    assert cf.noe_1d() < -1e6  # actual value is -1.462e6
    _g.p_spectrum = None


def test_minabsint():
    # check that it has some basic properties.
    def get_minabsint(expno):
        _g.p_spectrum = makep(expno, 1)
        return cf.minabsint()
    for i in range(1, 8):
        assert get_minabsint(i) > 0
    biggest = get_minabsint(1)
    smallest = get_minabsint(2)
    middle1, middle2 = get_minabsint(3), get_minabsint(4)
    assert biggest > middle1
    assert biggest > middle2
    assert middle1 > smallest
    assert middle2 > smallest
    _g.p_spectrum = None  # reset for next test


def test_maxabsint():
    # just check that it is the negative of minabsint.
    def get_minmaxabsint(expno):
        _g.p_spectrum = makep(expno, 1)
        return cf.minabsint(), cf.maxabsint()
    for i in range(1, 8):
        minai, maxai = get_minmaxabsint(i)
        assert maxai == -minai


def test_minrealint():
    # check that it has some basic properties.
    def get_minrealint(expno):
        _g.p_spectrum = makep(expno, 1)
        return cf.minrealint()
    for i in range(1, 8):
        if i != 1:
            assert get_minrealint(1) > get_minrealint(i)
        assert get_minrealint(i) > 0


def test_maxrealint():
    # just check that this is the negative of minrealint.
    def get_minmaxrealint(expno):
        _g.p_spectrum = makep(expno, 1)
        return cf.minrealint(), cf.maxrealint()
    for i in range(1, 8):
        minri, maxri = get_minmaxrealint(i)
        assert maxri == -minri


def test_zerorealint():
    # check that it has some basic properties.
    def get_zerorealint(expno):
        _g.p_spectrum = makep(expno, 1)
        return cf.zerorealint()
    for i in range(1, 8):
        if i != 7:
            assert get_zerorealint(i) > get_zerorealint(7)
        assert get_zerorealint(i) > 0
