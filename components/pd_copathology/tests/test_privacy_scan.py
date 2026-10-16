"""The report scanner is type- and schema-aware: declared aggregate numbers are never compared with identifiers,
everything else is checked strictly. Synthetic identifiers only."""

from __future__ import annotations

import json

import pytest

from copath.data import privacy
from copath.data.privacy import scan_reports_for_ids

IDS = ["3101", "7101", "4015", "5019", "S-77-ABC"]


def _scan(tmp_path, text, name="report.csv", declared=None):
    folder = tmp_path / f"case{len(list(tmp_path.iterdir()))}"  # a fresh folder per call
    folder.mkdir()
    (folder / name).write_text(text, encoding="utf-8")
    return scan_reports_for_ids(folder, IDS, declared=declared)


def test_an_identifier_in_an_undeclared_column_is_detected(tmp_path):
    assert _scan(tmp_path, "label,site_code\nx,3101\n") == [{"file": "report.csv", "location": "column site_code", "n_matches": 1}]
    assert _scan(tmp_path, "label,site_code\nx,3101.0\n")  # the same identifier written as a float
    assert _scan(tmp_path, "label,site_code\nx,3102\n") == []  # a different number is fine


@pytest.mark.parametrize("header", ["PATNO", "patno", "participant_id", "Subject_ID", "id"])
def test_identifier_named_columns_always_fail(tmp_path, header):
    found = _scan(tmp_path, f"{header},auroc\nanything,0.9\n")
    assert found and "identifier-named column" in found[0]["location"]


def test_an_identifier_as_a_whole_word_in_a_text_field_is_detected(tmp_path):
    assert _scan(tmp_path, "label,note\nx,subject 3101 excluded\n")
    assert _scan(tmp_path, "label,note\nx,(3101)\n")
    assert _scan(tmp_path, "label,note\nx,S-77-ABC was dropped\n")  # an identifier with punctuation
    assert _scan(tmp_path, "label,note\nx,reached 0.7101 AUROC\n") == []  # the digits of a decimal are not the word 7101
    assert _scan(tmp_path, "label,note\nx,order 131012 shipped\n") == []  # a digit substring of a longer number


def test_a_declared_float_metric_whose_digits_contain_an_id_is_not_flagged(tmp_path):
    table = "label,heldout,heldout_ci_low\nx,0.731012,0.7101\ny,0.4015,-0.5019\n"
    assert _scan(tmp_path, table, "dev_vs_test.csv", declared={"dev_vs_test.csv": ["heldout", "heldout_ci_low"]}) == []
    assert _scan(tmp_path, table, "other.csv") == []  # undeclared decimals are not equal to an identifier either


def test_a_declared_count_equal_to_an_id_is_not_flagged_but_the_same_value_undeclared_is(tmp_path):
    table = "label,cases\nx,4015\ny,5019\n"
    assert _scan(tmp_path, table, "counts.csv", declared={"counts.csv": ["cases"]}) == []
    assert _scan(tmp_path, table, "counts.csv") == [{"file": "counts.csv", "location": "column cases", "n_matches": 2}]
    assert _scan(tmp_path, "label,n_cases\nx,4015\n", "counts2.csv") == []  # generic n_* counts are declared by name


def test_declaring_a_column_does_not_hide_text_in_it(tmp_path):
    assert _scan(tmp_path, "label,heldout\nx,subject 3101\n", "dev_vs_test.csv", declared={"dev_vs_test.csv": ["heldout"]})
    assert _scan(tmp_path, "label,heldout\nx,<5\n", "dev_vs_test.csv", declared={"dev_vs_test.csv": ["heldout"]}) == []


def test_the_other_report_kinds_still_catch_planted_identifiers(tmp_path):
    (tmp_path / "a.md").write_text("The table `subject 3101` is listed\n", encoding="utf-8")
    (tmp_path / "b.json").write_text(json.dumps({"note": "dropped 7101 early"}), encoding="utf-8")
    (tmp_path / "c.csv").write_text("3101,x\n1,2\n", encoding="utf-8")  # an identifier as a column header
    (tmp_path / "d.csv").write_text("test_name,units\n4015,pg/mL\n", encoding="utf-8")  # vocabulary column
    (tmp_path / "e.txt").write_text("free text with S-77-ABC inside\n", encoding="utf-8")
    assert {f["file"] for f in scan_reports_for_ids(tmp_path, IDS)} == {"a.md", "b.json", "c.csv", "d.csv", "e.txt"}


def test_findings_never_contain_the_identifier_or_the_cell_value(tmp_path):
    found = _scan(tmp_path, "label,note\nx,subject 3101 excluded\n")
    assert "3101" not in json.dumps(found) and "excluded" not in json.dumps(found)
    assert set(found[0]) == {"file", "location", "n_matches"}


def test_the_scanner_is_the_one_every_call_site_uses():
    import inspect

    from copath import phase2
    from copath.data import audit
    from copath.phase3 import core

    for module in (phase2, audit, core):
        assert "scan_reports_for_ids(" in inspect.getsource(module)
    assert privacy.scan_reports_for_ids is scan_reports_for_ids
