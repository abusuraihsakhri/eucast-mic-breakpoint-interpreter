#!/usr/bin/env python3
"""Conservative MIC categorisation using explicitly supplied EUCAST breakpoints.

No clinical breakpoint table is bundled. The caller must confirm the species,
agent, dosing context, notes, and exact breakpoint table edition.
"""

import argparse
import csv
from decimal import Decimal, InvalidOperation
import json
import os
import re
import sys
import tempfile

MIC_PATTERN = re.compile(r"^\s*(<=|>=|<|>)?\s*(\d+(?:\.\d+)?|\.\d+)\s*$")
FIELDS = ("organism", "antimicrobial", "mic", "s_le", "r_gt", "breakpoint_version")
OPTIONAL = ("atu_low", "atu_high")


def _validate_safe_path(path, must_exist=False):
    if "\x00" in path:
        raise ValueError("Invalid path: contains null bytes")
    if ".." in path.replace("\\", "/").split("/"):
        raise ValueError("Path traversal detected")
    resolved = os.path.abspath(path)
    if must_exist and not os.path.isfile(resolved):
        raise FileNotFoundError(f"Input file not found: {path}")
    return resolved


def _number(value, name):
    try:
        number = Decimal(str(value).strip())
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError(f"{name} must be a finite nonnegative number") from None
    if not number.is_finite() or number < 0:
        raise ValueError(f"{name} must be a finite nonnegative number")
    return number


def _mic_interval(value):
    match = MIC_PATTERN.fullmatch(str(value))
    if match is None:
        raise ValueError("MIC must be a number or a qualified value such as <=0.25 or >8")
    op, raw = match.groups()
    amount = _number(raw, "MIC")
    if amount <= 0:
        raise ValueError("MIC must be greater than zero")
    if op == "<":
        return (None, False, amount, False)
    if op == "<=":
        return (None, False, amount, True)
    if op == ">":
        return (amount, False, None, False)
    if op == ">=":
        return (amount, True, None, False)
    return (amount, True, amount, True)


def interpret_mic(*, organism, antimicrobial, mic, s_le, r_gt,
                  breakpoint_version, atu_low=None, atu_high=None):
    """Return S, I, R, ATU, or UNDETERMINED without inventing breakpoints.

    S: MIC <= s_le; I: s_le < MIC <= r_gt; R: MIC > r_gt.
    Qualified MICs receive a category only if all possible values agree.
    An interval overlapping a supplied ATU is flagged instead of categorised.
    """
    for label, value in (("organism", organism), ("antimicrobial", antimicrobial),
                         ("breakpoint_version", breakpoint_version)):
        if not isinstance(value, str) or not value.strip() or len(value) > 160:
            raise ValueError(f"{label} is required (max 160 characters)")
    s, r = _number(s_le, "s_le"), _number(r_gt, "r_gt")
    if s > r:
        raise ValueError("s_le must not exceed r_gt")
    low, low_inc, high, high_inc = _mic_interval(mic)
    if (atu_low is None or str(atu_low).strip() == "") != (atu_high is None or str(atu_high).strip() == ""):
        raise ValueError("Specify both atu_low and atu_high, or neither")

    category = "UNDETERMINED"
    reason = "The MIC reporting interval crosses a category boundary"
    if atu_low is not None and str(atu_low).strip() != "":
        a, b = _number(atu_low, "atu_low"), _number(atu_high, "atu_high")
        if a > b:
            raise ValueError("atu_low must not exceed atu_high")
        below = high is not None and (high < a or (high == a and not high_inc))
        above = low is not None and (low > b or (low == b and not low_inc))
        if not (below or above):
            category = "ATU"
            reason = "MIC interval overlaps the specified Area of Technical Uncertainty; manual review required"
    if category != "ATU":
        if high is not None and high <= s:
            category, reason = "S", "MIC is within the supplied S threshold (standard dosing regimen)"
        elif low is not None and (low > r or (low == r and not low_inc)):
            category, reason = "R", "MIC exceeds the supplied R threshold"
        elif (low is not None and (low > s or (low == s and not low_inc))
              and high is not None and high <= r):
            category, reason = "I", "MIC is between S and R thresholds (increased exposure)"

    return {
        "organism": organism.strip(), "antimicrobial": antimicrobial.strip(),
        "mic": str(mic).strip(), "s_le": str(s), "r_gt": str(r),
        "breakpoint_version": breakpoint_version.strip(),
        "classification": category, "reason": reason,
        "atu_low": str(_number(atu_low, "atu_low")) if atu_low is not None and str(atu_low).strip() else "",
        "atu_high": str(_number(atu_high, "atu_high")) if atu_high is not None and str(atu_high).strip() else "",
    }


def calculate_metrics(**kwargs):
    """Compatibility entry point: unlike the previous weighted-score placeholder, requires MIC fields."""
    return interpret_mic(**kwargs)


def _csv_safe(value):
    text = str(value)
    return "'" + text if text.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")) else text


def process_batch(input_csv, output_csv):
    source = _validate_safe_path(input_csv, must_exist=True)
    destination = _validate_safe_path(output_csv)
    if os.path.samefile(source, destination) if os.path.exists(destination) else source == destination:
        raise ValueError("Input and output files must differ")
    if os.path.getsize(source) > 10 * 1024 * 1024:
        raise ValueError("CSV input exceeds 10 MiB limit")
    results = []
    with open(source, newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or any(field not in reader.fieldnames for field in FIELDS):
            raise ValueError("CSV requires headers: " + ", ".join(FIELDS))
        for index, row in enumerate(reader, start=1):
            if index > 50000:
                raise ValueError("CSV exceeds 50000-row limit")
            try:
                if None in row:
                    raise ValueError("Unexpected extra CSV columns")
                result = interpret_mic(**{field: row.get(field) for field in FIELDS + OPTIONAL})
            except (ValueError, TypeError) as exc:
                result = {field: row.get(field, "") for field in FIELDS + OPTIONAL}
                result.update(classification="INVALID", reason=str(exc))
            results.append({"row": index, **{key: _csv_safe(result.get(key, "")) for key in FIELDS + OPTIONAL + ("classification", "reason")}})
    headers = ("row",) + FIELDS + OPTIONAL + ("classification", "reason")
    fd, temporary = tempfile.mkstemp(prefix=".mic-", suffix=".csv", dir=os.path.dirname(destination) or ".")
    try:
        with os.fdopen(fd, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=headers)
            writer.writeheader()
            writer.writerows(results)
        os.replace(temporary, destination)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return len(results)


def main(argv=None):
    parser = argparse.ArgumentParser(description="EUCAST MIC breakpoint interpreter (user-supplied thresholds)")
    commands = parser.add_subparsers(dest="command", required=True)
    single = commands.add_parser("single", help="Interpret one MIC")
    for field in FIELDS:
        single.add_argument("--" + field.replace("_", "-"), required=True)
    for field in OPTIONAL:
        single.add_argument("--" + field.replace("_", "-"))
    batch = commands.add_parser("batch", help="Interpret CSV using explicit per-row breakpoints")
    batch.add_argument("-i", "--input", required=True)
    batch.add_argument("-o", "--output", default="results.csv")
    args = parser.parse_args(argv)
    try:
        if args.command == "single":
            print(json.dumps(interpret_mic(**{name: getattr(args, name) for name in FIELDS + OPTIONAL}), indent=2))
        else:
            print(f"Processed {process_batch(args.input, args.output)} rows -> {args.output}")
    except (ValueError, FileNotFoundError, OSError) as exc:
        parser.exit(2, f"Error: {exc}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
