"""Print the input file to stdout and exit 0."""

import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        sys.stderr.write("usage: tool.py INPUT\n")
        return 2
    sys.stdout.buffer.write(Path(sys.argv[1]).read_bytes())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
