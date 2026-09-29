"""Exit 0 and write bytes that do not match the shared input."""

import sys


def main() -> int:
    sys.stdout.buffer.write(b"wrong\n")
    sys.stderr.write("mismatch fixture\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
