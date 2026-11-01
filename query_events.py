"""Query all final factorial tables through DuckDB without copying them into SQLite."""
from pathlib import Path
import argparse
import pandas as pd
import duckdb
ROOT=Path(__file__).resolve().parent
def connect():
    manifest=pd.read_csv(ROOT/'results'/'event_manifest.csv');db=duckdb.connect()
    for kind in ['events','lots','activity','wip']:
        paths=[str(ROOT/p) for p in manifest.loc[manifest.kind==kind,'path']]
        if paths:db.read_parquet(paths,union_by_name=True).create_view(kind)
    return db
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--sql',default='SELECT COUNT(*) AS lot_step_rows FROM events');a=p.parse_args()
    with connect() as db:print(db.sql(a.sql).df().to_string(index=False))
