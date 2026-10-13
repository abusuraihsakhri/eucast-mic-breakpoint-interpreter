import csv
import pytest
from eucast_interpreter import interpret_mic, process_batch, calculate_metrics


BASE = dict(organism="Example organism", antimicrobial="Example antibiotic", breakpoint_version="user-verified 16.1", s_le="1", r_gt="8")


def cat(mic, **extra):
    return interpret_mic(**(BASE | extra), mic=mic)["classification"]


def test_boundaries_and_increased_exposure():
    assert [cat(x) for x in ("0.5", "1", "2", "8", "16")] == ["S", "S", "I", "I", "R"]
    assert cat("2", s_le="2", r_gt="2") == "S"
    assert cat("4", s_le="2", r_gt="2") == "R"


def test_qualified_intervals():
    assert cat("<=1") == "S"
    assert cat("<2") == "UNDETERMINED"
    assert cat(">8") == "R"
    assert cat(">=8") == "UNDETERMINED"
    assert cat("<=16") == "UNDETERMINED"
    assert cat("<1") == "S"
    assert cat(">1") == "UNDETERMINED"


def test_atu_overrides_category():
    assert cat("4", atu_low="2", atu_high="4") == "ATU"
    assert cat("<=4", atu_low="2", atu_high="4") == "ATU"
    assert cat(">4", atu_low="2", atu_high="4") == "UNDETERMINED"
    assert cat("8", atu_low="2", atu_high="4") == "I"


@pytest.mark.parametrize("override", [
    {"mic": "NaN"}, {"mic": "0"}, {"mic": "-1"}, {"mic": "Inf"},
    {"mic": "abc"}, {"s_le": "NaN"}, {"s_le": "4", "r_gt": "2"},
    {"antimicrobial": ""}, {"breakpoint_version": ""},
    {"atu_low": "2"}, {"atu_low": "5", "atu_high": "4"},
])
def test_invalid_inputs_fail_closed(override):
    with pytest.raises(ValueError):
        interpret_mic(**(BASE | {"mic": "2"} | override))


def test_calculate_metrics_no_fabricated_scores():
    assert calculate_metrics(**BASE, mic="2")["classification"] == "I"
    with pytest.raises(TypeError):
        calculate_metrics(v1=28, v2=4)


def test_batch_per_row_and_formula_escape(tmp_path):
    source, target = tmp_path / "sample.csv", tmp_path / "out.csv"
    source.write_text("organism,antimicrobial,mic,s_le,r_gt,breakpoint_version\n"
                      "Test species,Drug A,1,1,8,16.1\n"
                      "Test species,Drug A,9,1,8,16.1\n"
                      "=2+2,Drug A,banana,1,8,16.1\n", encoding="utf-8")
    assert process_batch(str(source), str(target)) == 3
    with target.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert [r["classification"] for r in rows] == ["S", "R", "INVALID"]
    assert rows[2]["organism"] == "'=2+2"
    with pytest.raises(ValueError):
        process_batch(str(source), str(source))
