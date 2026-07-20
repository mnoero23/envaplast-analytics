from __future__ import annotations

import json

from src.quality import quality_report

report = quality_report()
print(json.dumps(report, indent=2, ensure_ascii=False))
raise SystemExit(0 if report["passed"] else 1)
