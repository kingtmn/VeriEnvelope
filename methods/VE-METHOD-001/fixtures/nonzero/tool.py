"""Exit nonzero. The method records that the expected exit was not met."""

import sys


def main() -> int:
    sys.stderr.write("nonzero fixture\n")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
