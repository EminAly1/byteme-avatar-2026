"""Label every primary key in an explicitly isolated synthetic demo schema.

Read-only sidecar: preserves original seed payloads and idempotency hashes.
This is an operator declaration of data origin, not synthetic-data detection.
"""
import argparse
import json
import os
from pathlib import Path

from app.demo_safety import require_local_demo
from app.database import get_engine
from app.models import Base
from sqlalchemy import select


def main():
    require_local_demo()
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    tables = {}
    with get_engine().connect() as connection:
        for table in Base.metadata.sorted_tables:
            columns = list(table.primary_key.columns)
            records = [
                {'identity_values': list(row),
                 'data_origin': 'KURGUSAL / SYNTHETIC'}
                for row in connection.execute(select(*columns).order_by(*columns))
            ]
            tables[table.name] = {'identity_columns': [column.name for column in columns],
                                  'record_count': len(records), 'records': records}
    report = {
        'database': os.environ['MYSQL_DATABASE'],
        'declaration': 'All records in this dedicated demo schema are fictional.',
        'business_data': False,
        'seed_payloads_and_ledger_changed': False,
        'tables': tables,
    }
    Path(args.output).write_text(json.dumps(report, indent=2) + '\n')
    print('İzole demo kayıtlarının KURGUSAL/SYNTHETIC manifesti salt-okunur üretildi.')


if __name__ == '__main__':
    main()
