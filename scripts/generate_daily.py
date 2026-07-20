from __future__ import annotations

import argparse
import json
from datetime import date

from sqlalchemy.orm import Session

from src.config import settings
from src.database import engine
from src.generator import create_schema, generate_day, generate_missing, seed_master_data

parser = argparse.ArgumentParser(description="Generación diaria idempotente")
parser.add_argument("--date", type=date.fromisoformat)
parser.add_argument("--fill-missing", action="store_true")
args = parser.parse_args()
create_schema(engine)
if args.fill_missing:
    result = generate_missing(engine, args.date or date.today())
else:
    target = args.date or date.today()
    with Session(engine) as session, session.begin():
        seed_master_data(session, settings.seed)
        result = generate_day(session, target, settings.seed, target)
print(json.dumps(result, indent=2, ensure_ascii=False))
