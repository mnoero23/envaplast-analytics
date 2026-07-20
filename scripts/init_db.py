from __future__ import annotations

import argparse
import json
from datetime import date

from src.database import engine
from src.generator import create_schema, initialize_history

parser = argparse.ArgumentParser(description="Inicializa el histórico sintético de Envaplast")
parser.add_argument("--end-date", type=date.fromisoformat, default=date.today())
parser.add_argument("--months", type=int, default=18)
args = parser.parse_args()
create_schema(engine)
print(
    json.dumps(initialize_history(engine, args.end_date, args.months), indent=2, ensure_ascii=False)
)
