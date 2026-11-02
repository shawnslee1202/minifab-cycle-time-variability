"""Build a portable SQL audit database and dashboard payload from final outputs."""
from pathlib import Path
import sqlite3,json,shutil
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[2];D=ROOT/'results';DIST=ROOT/'dashboard'/'dist'
def read_log(rid,suffix=''):
    p=D/'events'/(rid+suffix+'.parquet')
    return pd.read_parquet(p) if p.exists() else pd.read_csv(D/'events'/(rid+suffix+'.csv.gz'))
def build():
    db=sqlite3.connect(D/'reporting.sqlite');runs=pd.read_csv(D/'runs.csv');runs.to_sql('runs',db,if_exists='replace',index=False)
    for table in ['events','lots','activity','wip_samples']:db.execute('DROP TABLE IF EXISTS '+table)
    for sc in ['Baseline','A','B','C','D','ABCD']:
        rid=f'equal_starts_85_{sc}_0'
        for suffix,table in [('', 'events'),('_lots','lots'),('_activity','activity')]:
            read_log(rid,suffix).to_sql(table,db,if_exists='append',index=False,chunksize=10000)
    for table in ['summary','effects','budget','theory']:
        pd.read_csv(D/(table+'.csv')).to_sql(table,db,if_exists='replace',index=False)
    db.executescript((Path(__file__).with_name('views.sql')).read_text(encoding='utf-8-sig'))
    db.execute('CREATE INDEX IF NOT EXISTS ix_events ON events(run_id,lot_id,step)');db.execute('CREATE INDEX IF NOT EXISTS ix_lots ON lots(run_id,lot_id)');db.commit()
    details={}
    for sc in ['Baseline','A','B','C','D','ABCD']:
        rid=f'equal_starts_85_{sc}_0';rr=runs[runs.run_id==rid].iloc[0]
        ct=pd.read_sql_query('SELECT cycle_time_hours FROM cycle_time_per_lot WHERE run_id=? AND measurement_departure=1',db,params=[rid]).cycle_time_hours
        counts,edges=np.histogram(ct,bins=8)
        moves=pd.read_sql_query('SELECT * FROM moves_per_day WHERE run_id=? AND day>=? ORDER BY day,step',db,params=[rid,int(rr.warm_days+rr.days-14)])
        pivot=moves.pivot(index='day',columns='step',values='moves').fillna(0).rename(columns=lambda x:'s'+str(x)).reset_index()
        details[sc]=dict(hist=dict(labels=[f'{a:.0f}-{b:.0f}h' for a,b in zip(edges[:-1],edges[1:])],counts=counts.tolist()),moves=pivot.to_dict('records'),target=1440/rr.interval_actual)
    payload={name:pd.read_csv(D/(name+'.csv')).replace({np.nan:None}).to_dict('records') for name in ['summary','effects','shapley','budget','runs','theory']}
    payload['details']=details;payload['validation']=json.loads((D/'validation.json').read_text())
    (DIST/'data.js').write_text('const DATA='+json.dumps(payload,allow_nan=False)+';',encoding='utf8')
    for view in ['equal_starts','equal_utilization']:shutil.copy2(ROOT/'figures'/f'operating_{view}.png',DIST)
    print('SQL audit rows',db.execute('SELECT COUNT(*) FROM events').fetchone()[0]);db.close()
    # All-run SQL over Parquet without duplicating the full audit archive.
    (Path(__file__).with_name('all_events.duckdb.sql')).write_text("""-- Start duckdb from the project root after converting any legacy gzip files.
CREATE OR REPLACE VIEW events_all AS SELECT * FROM read_parquet('results/events/*.parquet',union_by_name=true) WHERE step IS NOT NULL;
-- Prefer the file manifest in results/event_manifest.csv to distinguish visit, lot, activity and WIP tables.
""")
if __name__=='__main__':build()
