"""Compare the published push cases under the chapter 4 simplified batching rules."""
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import pandas as pd
from model import Config, simulate

def measure(case):
    pattern, rep = case
    cfg = Config(mix=True, thesis_reference=True, personnel_constraints=False,
                 days=574, warm_days=154, interval=120, D=pattern, rep=rep,
                 view="thesis_reference")
    result, *_ = simulate(cfg)
    return result

if __name__ == "__main__":
    with ProcessPoolExecutor(4) as pool:
        rows = list(pool.map(measure, [(pattern, rep) for pattern in (0, 1) for rep in range(15)]))
    data = pd.DataFrame(rows)
    data.to_csv(Path(__file__).parent / "results/thesis_reference.csv", index=False)
    print(data.groupby("D")[["mean_ct","wip","throughput_day","Me_setup"]].mean())
