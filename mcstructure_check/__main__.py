"""Command line entry point."""
import argparse
import json
from pathlib import Path
import sys

from . import __version__
from .inspect import inspect_bytes
from .nbt import MAX_BYTES


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Read-only checker for Bedrock .mcstructure command blocks."
    )
    parser.add_argument("file", type=Path)
    parser.add_argument("--json", action="store_true", help="print JSON")
    parser.add_argument("--version", action="version", version=__version__)
    args = parser.parse_args(argv)
    try:
        with args.file.open("rb") as fp:
            data = fp.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise ValueError("input exceeds 64 MiB")
        report = inspect_bytes(data)
    except (ValueError, OSError) as exc:
        # Errors deliberately exclude paths and file-derived values from reports.
        message = str(exc) if isinstance(exc, ValueError) else "cannot read input file"
        if args.json:
            print(json.dumps({"schema_version": 1, "error": message}, ensure_ascii=True))
        else:
            print(f"Input error: {message}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report, ensure_ascii=True, indent=2))
    else:
        print("Size:", " x ".join(map(str, report["size"])),
              "| Command blocks:", report["command_block_count"],
              "| Findings:", report["issue_count"])
        for item in report["issues"]:
            # The ASCII CLI also works on terminals with non-UTF-8 encodings.
            print(item["severity"], item["code"], tuple(item["position"]))
        if report["issues_truncated"]:
            print(f"Showing {len(report['issues'])} of {report['issue_count']} findings.")
    return 1 if report["issue_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
