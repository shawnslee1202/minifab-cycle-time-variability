"""Ten-year WIP follow-up for the high-load cells flagged in the original experiment.

This diagnostic records daily WIP only. The factorial experiment and confirmation
continue to export full event tables. Reuse the simulator's event dynamics.
"""
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import numpy as np
import pandas as pd
from minifab_cycle_time_variability.model.model import Config,Fab
from minifab_cycle_time_variability.experiment.experiment import DATA

class CountAppends:
    def __init__(self):
        self.count = 0
    def append(self, item):
        self.count += 1
    def __len__(self):
        return self.count

def measure(case):
    scenario, interval, rep = case
    factors={f:int(f in scenario) for f in "ABCD"}
    fab=Fab(Config(**factors,rep=rep,interval=interval,load=.95,warm_days=0,days=3650))
    fab.events=CountAppends()
    fab.lots=CountAppends()
    fab.activity=CountAppends()
    fab.env.run(until=fab.stop)
    data=pd.DataFrame(fab.samples,columns=["minutes","wip"])
    data["year"]=(data.minutes//(365*1440)).astype(int)+1
    return [dict(scenario=scenario,rep=rep,year=year,mean_daily_wip=wip)
            for year,wip in data.groupby("year").wip.mean().items()]

if __name__=="__main__":
    drift=pd.read_csv(DATA/"stability_summary.csv")
    flagged=drift[drift.positive_drift_flag]
    runs=pd.read_csv(DATA/"runs.csv")
    cases=[]
    for row in flagged.itertuples():
        match=runs[(runs.view==row.view)&(runs.load==row.load)&(runs.scenario==row.scenario)]
        cases.extend((row.scenario,match.interval_actual.iloc[0],rep) for rep in range(20000,20006))
    with ProcessPoolExecutor(2) as pool:
        data=pd.DataFrame([r for rows in pool.map(measure,cases) for r in rows])
    data.to_csv(DATA/"long_horizon_wip.csv",index=False)
    print(data.groupby(["scenario","year"]).mean_daily_wip.mean().unstack().round(1))
