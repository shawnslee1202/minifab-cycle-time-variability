"""Second external benchmark: NIST framework, section VIII, Tables IV–VII.

FIFO. Fixed product-specific arrival clocks start one product interval after zero.
Interpret the single lithography setup as a change in product. Also evaluate recipe
change as a sensitivity. Both conventions are declared independently of the outputs.
"""
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import pandas as pd
import simpy
from minifab_cycle_time_variability.model.model import Fab,Config

class NistFab(Fab):
    process_minutes = [225,30,55,50,225,10]
    unload_minutes = [20,15,10,15,20,10]
    def __init__(self, rep, extra, trigger):
        self.trigger = trigger
        super().__init__(Config(rep=rep, personnel_constraints=True,
            maintenance=False, breaks=False, days=10000/24, warm_days=10000/24,
            mix=True, thesis_reference=True, view="NIST"))
        self.tech = simpy.PriorityResource(self.env,2)
        self.ops = simpy.FilterStore(self.env,2+extra)
        self.ops.items = ["PO1"]*(1+extra)+["PO2"]
        for m in self.machines:
            if m["station"]==1:
                self.env.process(self.failure(m))

    def release(self):
        for product, quantity in [("Pa",51),("Pb",30),("TW",3)]:
            self.env.process(self.product_stream(product,10080/quantity))
        yield self.env.timeout(0)

    def product_stream(self, product, interval):
        while True:
            yield self.env.timeout(interval)
            lot=dict(lot_id=len(self.lots),product=product,release=self.env.now,exit=None)
            self.lots.append(lot)
            self.active_wip+=1
            self.arrive(lot,0)

    def setup_minutes(self, previous, step, product):
        if previous is None:
            return 0
        if self.trigger=="product":
            return 10*(previous[1]!=product)
        return 10*(previous[0]!=step)

def measure(spec):
    rep,extra,trigger=spec
    fab=NistFab(rep,extra,trigger)
    _,_,lots,_,_=fab.run()
    rows=[]
    for product, group in lots.groupby("product"):
        done=group[group.exit>=fab.warm]
        exposure=(group.exit.fillna(fab.stop)-group.release.clip(lower=fab.warm)).clip(lower=0)
        rows.append(dict(rep=rep,extra_PO1=extra,setup_trigger=trigger,product=product,
                         ct_hours=(done.exit-done.release).mean()/60,wip=exposure.sum()/(fab.stop-fab.warm)))
    return rows

if __name__=="__main__":
    cases=[(rep,extra,trigger) for rep in range(5) for extra in (0,1) for trigger in ("product","step")]
    with ProcessPoolExecutor(3) as pool:
        data=pd.DataFrame([row for group in pool.map(measure,cases) for row in group])
    data.to_csv(Path(__file__).resolve().parents[2]/"results/nist_reference.csv",index=False)
    print(data.groupby(["extra_PO1","setup_trigger","product"])[["ct_hours","wip"]].mean())
