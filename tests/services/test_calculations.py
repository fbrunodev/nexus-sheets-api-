from types import SimpleNamespace
import pytest
from app.services.calculations import calc_line_result, calc_sheet_result


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


# --- calc_sheet_result -------------------------------------------------------

def sheet(lines=None, salary=0, cooperation_type="META"):
    return SimpleNamespace(lines=lines or [], salary=salary, cooperation_type=cooperation_type)


def test_sheet_no_lines():
    assert calc_sheet_result(sheet()) == 0.0


def test_sheet_lines_only():
    s = sheet(lines=[
        line(withdrawal=200, deposit=100),
        line(withdrawal=50, deposit=30, chest=10),
    ])
    # (200-100) + (50-30+10) = 100 + 30 = 130
    assert calc_sheet_result(s) == 130.0


def test_sheet_salary_included_for_meta():
    s = sheet(lines=[line(withdrawal=100, deposit=50)], salary=500, cooperation_type="META")
    assert calc_sheet_result(s) == 550.0


def test_sheet_salary_included_for_recarga():
    s = sheet(lines=[line(withdrawal=100, deposit=50)], salary=300, cooperation_type="RECARGA")
    assert calc_sheet_result(s) == 350.0


def test_sheet_salary_excluded_for_bau():
    s = sheet(lines=[line(withdrawal=100, deposit=50)], salary=500, cooperation_type="BAU")
    assert calc_sheet_result(s) == 50.0


def test_sheet_none_salary():
    s = sheet(lines=[line(withdrawal=100, deposit=50)], salary=None, cooperation_type="META")
    assert calc_sheet_result(s) == 50.0


def test_sheet_none_lines():
    s = sheet(lines=None, salary=200, cooperation_type="META")
    assert calc_sheet_result(s) == 200.0
