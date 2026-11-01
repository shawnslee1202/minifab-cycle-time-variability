from pathlib import Path
import json
import pandas as pd
from scipy.stats import t
from confirm_precision import schedule
from experiment import DATA

def finish():
    specs=schedule()
    rows=[json.loads((DATA/"confirmation"/(rid+".json")).read_text())["response"] for _,_,rid in specs]
    final=pd.read_csv(DATA/"confirmation2_runs.csv")
    assert len(final)==256 and final.rep.nunique()==256
    first=pd.DataFrame(rows)
    full=pd.concat([first,final],ignore_index=True)
    assert full.run_id.is_unique
    import os
    with os.scandir(DATA/"events") as files:
        exported={f.name for f in files if f.name.startswith("confirm") and f.stat().st_size>0}
    expected={rid+suffix+".parquet" for rid in full.run_id for suffix in ["","_lots","_activity","_wip"]}
    assert expected == exported, "Confirmation event exports differ from the expected manifest"
    full.to_csv(DATA/"confirmation_runs.csv.gz",index=False)
    base=pd.read_csv(DATA/"summary.csv")
    for idx,row in base.iterrows():
        g=full[(full.view==row["view"])&(full.load==row["load"])&(full.scenario==row["scenario"])]
        stage="Balanced factorial"
        if not g.empty:
            if g.run_id.str.startswith("confirm2_").any():
                g=g[g.run_id.str.startswith("confirm2_")]
                stage="Second confirmation"
            else:
                stage="First confirmation"
            ct=g.mean_ct/60
            hw=t.ppf(.975,len(ct)-1)*ct.sem()
            for k,v in dict(n=len(ct),mean_hours=ct.mean(),halfwidth=hw,relative_halfwidth=hw/ct.mean(),precision_pass=hw/ct.mean()<.05).items():
                base.loc[idx,k]=v
        base.loc[idx,"source"]=stage
    cols=["view","load","scenario","source","n","mean_hours","halfwidth","relative_halfwidth","precision_pass"]
    base[cols].to_csv(DATA/"final_precision.csv",index=False)
    assert len(base)==96
    print(base.groupby("source").precision_pass.agg(["sum","count"]))
    print("Maximum relative halfwidth",base.relative_halfwidth.max())
if __name__=="__main__":finish()
