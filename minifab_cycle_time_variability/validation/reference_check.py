from pathlib import Path
import pandas as pd
from minifab_cycle_time_variability.model.model import Config,simulate
D=Path(__file__).resolve().parents[2]/'results';rows=[]
for constant in [0,1]:
 for rep in range(5):
    r,e,l,a,s=simulate(Config(interval=120,mix=True,D=constant,days=365,warm_days=90,rep=rep,personnel_constraints=False,view='reference'))
    r['case']='reduced_constant' if constant else 'reduced_exp';rows.append(r)
    print(r['case'],rep,r['mean_ct']/60,r['wip'],flush=True)
pd.DataFrame(rows).to_csv(D/'reference.csv',index=False)
