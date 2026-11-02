"""Independent confirmation of the finite-window mean CT in underprecise design cells.

Use the initial experiment only for sample sizing. Preserve its balanced factorial
contrasts. Each new replication has its own event export and atomic checkpoint.
"""
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import argparse
import json
import math
import os
import pandas as pd
from scipy.stats import t
from minifab_cycle_time_variability.experiment.parallel_run import task
from minifab_cycle_time_variability.experiment.experiment import DATA

CHECKPOINT = DATA / "confirmation"
def execute(spec):
    path = CHECKPOINT / (spec[2] + ".json")
    if not path.exists():
        row, theory = task(spec)
        pending = path.with_suffix(".tmp")
        pending.write_text(json.dumps(dict(response=row, theory=theory)))
        pending.replace(path)
    return spec[2]

def schedule():
    runs = pd.read_csv(DATA / "runs.csv")
    specs = []
    for (view,load,scenario), group in runs.groupby(["view","load","scenario"]):
        n = len(group)
        cv = group.mean_ct.std() / group.mean_ct.mean()
        if t.ppf(.975,n-1)*cv/math.sqrt(n) < .05:
            continue
        # A fixed confirmation design, allowing for uncertain pilot variance.
        target = max(30, math.ceil((2.05*cv/.04)**2))
        first = group.iloc[0]
        for rep in range(1000,1000+target):
            bits = tuple(int(first[factor]) for factor in "ABCD")
            rid = f"confirm_{view}_{int(100*load)}_{scenario}_{rep}"
            config = dict(view=view,load=load,rep=rep,days=float(first.days),
                          warm_days=float(first.warm_days), interval=float(first.interval_actual))
            specs.append((bits,config,rid))
    return specs

if __name__ == "__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--workers", type=int, default=4)
    args=p.parse_args()
    CHECKPOINT.mkdir(exist_ok=True)
    specs=schedule()
    print(f"Fixed design: {len(specs)} independent confirmation runs",flush=True)
    with ProcessPoolExecutor(args.workers) as pool:
        for i, rid in enumerate(pool.map(execute,specs),1):
            if i%25==0: print(i,rid,flush=True)
    rows=pd.DataFrame([json.loads((CHECKPOINT/(s[2]+".json")).read_text())["response"] for s in specs])
    summary=rows.groupby(["view","load","scenario"]).mean_ct.agg(["count","mean","std"])
    summary["relative_halfwidth"]=t.ppf(.975,summary["count"]-1)*summary["std"]/summary["mean"]/summary["count"]**.5
    summary.to_csv(DATA/"confirmation_summary.csv")
    print(summary.to_string())
