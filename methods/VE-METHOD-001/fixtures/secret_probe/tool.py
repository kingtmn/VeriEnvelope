"""Report whether VE_TEST_SECRET reached this process."""

import os
import sys


def main() -> int:
    if "VE_TEST_SECRET" in os.environ:
        sys.stdout.write("SECRET_PRESENT")
        return 0
    sys.stdout.write("clean\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
