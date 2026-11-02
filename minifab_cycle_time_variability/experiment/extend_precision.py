"""Optional precision extension. Run only after inspecting stability flags.
Adds a balanced block of new replications for a view/load; never treats lots as replicates.
"""
import argparse,json
from concurrent.futures import ProcessPoolExecutor,as_completed
import pandas as pd
from minifab_cycle_time_variability.experiment.parallel_run import task
from minifab_cycle_time_variability.experiment.experiment import DATA,FACTORS,config

def extend(view,load,additional,workers):
    r=pd.read_csv(DATA/'runs.csv');th=pd.read_csv(DATA/'theory.csv')
    group=r[(r.view==view)&(r.load==load)]
    if len(group.groupby('rep'))==0:raise ValueError('Run base design first')
    first=int(group.rep.max())+1;specs=[]
    for bits in FACTORS:
        sc=config(bits).scenario;template=group[group.scenario==sc].iloc[0]
        for rep in range(first,first+additional):
            rid=f'{view}_{int(load*100)}_{sc}_{rep}'
            specs.append((bits,dict(view=view,load=load,rep=rep,days=float(template.days),warm_days=float(template.warm_days),interval=float(template.interval_actual)),rid))
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for future in as_completed([pool.submit(task,s) for s in specs]):
            row,tt=future.result();r=pd.concat([r,pd.DataFrame([row])],ignore_index=True);th=pd.concat([th,pd.DataFrame(tt)],ignore_index=True)
            r.to_csv(DATA/'runs.next.csv',index=False);(DATA/'runs.next.csv').replace(DATA/'runs.csv')
            th.to_csv(DATA/'theory.next.csv',index=False);(DATA/'theory.next.csv').replace(DATA/'theory.csv')
            print(row['run_id'],flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--view',choices=['equal_starts','equal_utilization'],required=True);p.add_argument('--load',type=float,required=True);p.add_argument('--additional',type=int,default=5);p.add_argument('--workers',type=int,default=4)
    a=p.parse_args();extend(a.view,a.load,a.additional,a.workers)
