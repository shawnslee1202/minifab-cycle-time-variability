"""Independent fixed-size follow-up for the sole cell exceeding 5% in confirmation."""
from concurrent.futures import ProcessPoolExecutor
import json
import pandas as pd
from scipy.stats import t
from confirm_precision import execute, DATA, CHECKPOINT

if __name__ == "__main__":
    template = pd.read_csv(DATA / "runs.csv").query(
        "view == 'equal_starts' and load == .95 and scenario == 'ACD'").iloc[0]
    specs = []
    for rep in range(3000, 3256):
        rid = f"confirm2_equal_starts_95_ACD_{rep}"
        kw = dict(view="equal_starts",load=.95,rep=rep,days=float(template.days),
                  warm_days=float(template.warm_days),interval=template.interval_actual)
        specs.append(((1,0,1,1),kw,rid))
    CHECKPOINT.mkdir(exist_ok=True)
    with ProcessPoolExecutor(6) as pool:
        list(pool.map(execute,specs))
    data = pd.DataFrame([json.loads((CHECKPOINT/(rid+".json")).read_text())["response"]
                         for _,_,rid in specs])
    data.to_csv(DATA/"confirmation2_runs.csv",index=False)
    print(len(data),data.mean_ct.mean()/60,t.ppf(.975,255)*data.mean_ct.sem()/data.mean_ct.mean())

