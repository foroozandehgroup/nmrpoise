import json
import pytest

from nmrpoise.poise_backend import get_cfs


def test_get_cfs(capsys):
    get_cfs.main()
    cfs = capsys.readouterr().out
    fdict = json.loads(cfs)
    assert set(fdict.keys()) == {"noe_1d",
                                 "minabsint",
                                 "maxabsint",
                                 "minrealint",
                                 "maxrealint",
                                 "zeronetrealint",
                                 "zerorealint",
                                 "zerorealint_squared",
                                 "epsi_gradient_drift"
                                 }
