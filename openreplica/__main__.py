"""
OpenReplica - Main entry point for running the application.

This module allows running OpenReplica as a Python module:
    python -m openreplica
"""

import sys
from openreplica.cli import main

if __name__ == "__main__":
    sys.exit(main())
