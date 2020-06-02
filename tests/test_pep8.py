from pathlib import Path

import pycodestyle

s = pycodestyle.StyleGuide()


def test_style_frontend():
    p = (Path(__file__).parents[1].resolve()) / "poptpy"
    res = s.check_files([f for f in p.iterdir() if f.suffix == ".py"])
    assert res.total_errors == 0


def test_style_backend():
    p = (Path(__file__).parents[1].resolve()) / "poptpy" / "poptpy_backend"
    res = s.check_files([f for f in p.iterdir() if f.suffix == ".py"])
    assert res.total_errors == 0


def test_style_costfunctions():
    p = ((Path(__file__).parents[1].resolve()) / "poptpy" / "poptpy_backend" /
         "cost_functions")
    res = s.check_files([f for f in p.iterdir() if f.suffix == ".py"])
    assert res.total_errors == 0


def test_style_tests():   # how meta
    p = Path(__file__).parent
    res = s.check_files([f for f in p.iterdir() if f.suffix == ".py"])
    assert res.total_errors == 0
