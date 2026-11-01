"""Final audit: every exported run, stability signals, SQL and manifest checks."""
from pathlib import Path
import json,hashlib
import pandas as pd
import numpy as np
from scipy import stats
ROOT=Path(__file__).resolve().parent;D=ROOT/'results'
def audit():
    r=pd.read_csv(D/'runs.csv');records=[];manifest=[]
    for row in r.itertuples():
        rid=row.run_id;p=D/'events'/(rid+'_lots.parquet')
        l=pd.read_parquet(p) if p.exists() else pd.read_csv(D/'events'/(rid+'_lots.csv.gz'))
        start=row.warm_days*1440;stop=(row.warm_days+row.days)*1440;middle=(start+stop)/2
        def exposure(a,b):return np.maximum(0,np.minimum(l.exit.fillna(stop),b)-np.maximum(l.release,a)).sum()/(b-a)
        early=exposure(start,middle);late=exposure(middle,stop)
        drift=(late-early)/max(1e-9,(late+early)/2)
        records.append(dict(run_id=rid,view=row.view,load=row.load,scenario=row.scenario,rep=row.rep,
            first_half_wip=early,second_half_wip=late,relative_wip_change=drift,
            net_wip_change=row.released-row.completed,flow_imbalance=(row.released-row.completed)/row.completed))
        for suffix,kind in [('', 'events'),('_lots','lots'),('_activity','activity'),('_wip','wip')]:
            pp=D/'events'/(rid+suffix+'.parquet')
            if not pp.exists():pp=D/'events'/(rid+suffix+'.csv.gz')
            if pp.exists():manifest.append(dict(run_id=rid,kind=kind,path=str(pp.relative_to(ROOT)).replace('\\','/'),bytes=pp.stat().st_size))
            elif kind!='wip':raise RuntimeError('Missing audit file '+str(pp))
    pd.DataFrame(manifest).to_csv(D/'event_manifest.csv',index=False)
    drift=pd.DataFrame(records);drift.to_csv(D/'stability_runs.csv',index=False)
    rows=[]
    for (view,load,sc),g in drift.groupby(['view','load','scenario']):
        v=g.relative_wip_change.to_numpy();hw=stats.t.ppf(.975,len(v)-1)*v.std(ddof=1)/len(v)**.5
        rows.append(dict(view=view,load=load,scenario=sc,mean_wip_change=v.mean(),halfwidth=hw,
                        positive_drift_flag=bool(v.mean()-hw>0),max_flow_imbalance=g.flow_imbalance.abs().max()))
    pd.DataFrame(rows).to_csv(D/'stability_summary.csv',index=False)
    # Pairwise Shapley identity and complete-design checks.
    sh=pd.read_csv(D/'shapley.csv');summary=pd.read_csv(D/'summary.csv');errors=[]
    for (view,load),g in sh.groupby(['view','load']):
        z=summary[(summary.view==view)&(summary.load==load)].set_index('scenario')
        errors.append(abs(g.hours_saved.sum()-(z.loc['Baseline','mean_hours']-z.loc['ABCD','mean_hours'])))
    counts=r.groupby(['view','load','scenario']).size()
    assert len(counts)==96 and all(len(g)==16 for _,g in r.groupby(['view','load','rep'])), 'Incomplete factorial'
    assert r.run_id.nunique()==len(r),'Duplicate run IDs'
    assert max(errors)<1e-7,'Shapley identity failed'
    v=json.loads((D/'validation.json').read_text());v.update(complete_factorial=True,event_files=len(manifest),
      event_bytes=sum(x['bytes'] for x in manifest),max_shapley_identity_error=max(errors),
      positive_drift_cells=sum(x['positive_drift_flag'] for x in rows))
    (D/'validation.json').write_text(json.dumps(v,indent=2));print(json.dumps(v,indent=2))
if __name__=='__main__':audit()
