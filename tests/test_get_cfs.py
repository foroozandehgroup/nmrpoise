import pytest

from nmrpoise.poise_backend import get_cfs


def test_get_cfs(capsys):
    get_cfs.main()
    cfs = capsys.readouterr().out
    assert set(cfs.split()) == {"noe_1d",
                                "minabsint",
                                "maxabsint",
                                "minrealint",
                                "maxrealint",
                                "zerorealint"}
