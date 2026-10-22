#!/usr/bin/env python3
"""Validate the map and its reviewed, hashed evidence without touching hardware."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'host'))
from evidence import EvidenceError, report
try:
    result = report()
    print('PASS hardware evidence validation: %d assigned pins, %d reviewed records; board emulated: false'
          % (result['assignedPins'], result['reviewedRecords']))
except (EvidenceError, OSError, ValueError, KeyError, TypeError) as exc:
    print('FAIL hardware evidence validation: ' + str(exc), file=sys.stderr)
    sys.exit(1)
