from types import SimpleNamespace
import pytest
from app.services.calculations import calc_line_result


def line(**kwargs):
    defaults = {"deposit": 0, "withdrawal": 0, "chest": 0, "bonus": 0}
    return SimpleNamespace(**{**defaults, **kwargs})


def test_empty_line():
    assert calc_line_result(line()) == 0.0


def test_deposit_only():
    assert calc_line_result(line(deposit=100)) == -100.0


def test_withdrawal_only():
    assert calc_line_result(line(withdrawal=200)) == 200.0


def test_with_chest():
    assert calc_line_result(line(withdrawal=100, deposit=50, chest=30)) == 80.0


def test_with_bonus():
    assert calc_line_result(line(withdrawal=100, deposit=50, bonus=20)) == 70.0


def test_all_fields():
    assert calc_line_result(line(withdrawal=200, deposit=100, chest=30, bonus=10)) == 140.0


def test_none_deposit():
    assert calc_line_result(line(deposit=None, withdrawal=50)) == 50.0


def test_none_withdrawal():
    assert calc_line_result(line(withdrawal=None, deposit=30)) == -30.0


def test_none_chest():
    assert calc_line_result(line(chest=None, withdrawal=100, deposit=50)) == 50.0


def test_none_bonus():
    assert calc_line_result(line(bonus=None, withdrawal=100, deposit=50)) == 50.0


def test_all_none():
    assert calc_line_result(line(deposit=None, withdrawal=None, chest=None, bonus=None)) == 0.0
