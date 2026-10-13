import csv
from eucast_interpreter import calculate_metrics, process_batch


def test_interpret_single():
    result = calculate_metrics(
        organism="Demo organism", antimicrobial="Demo agent",
        mic="2", s_le="1", r_gt="8", breakpoint_version="illustrative")
    assert result["classification"] == "I"


def test_interpret_batch(tmp_path):
    incoming = tmp_path / "in.csv"
    outgoing = tmp_path / "out.csv"
    incoming.write_text(
        "organism,antimicrobial,mic,s_le,r_gt,breakpoint_version\n"
        "Demo organism,Demo agent,1,1,8,illustrative\n",
        encoding="utf-8",
    )
    assert process_batch(str(incoming), str(outgoing)) == 1
    with outgoing.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert rows[0]["classification"] == "S"
