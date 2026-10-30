"""Entry point used by an optional external AI Python environment."""
import sys
from apt.worker import execute

if __name__ == '__main__':
    raise SystemExit(execute(sys.argv[1]))
