"""Change one lithography convention at a time in the published push comparison."""
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pandas as pd
from minifab_cycle_time_variability.model.model import Config, Fab, LOAD, UNLOAD, STATION


class ExternalHandling(Fab):
    load_minutes = [0 if station == 2 else v for station, v in zip(STATION, LOAD)]
    unload_minutes = [0 if station == 2 else v for station, v in zip(STATION, UNLOAD)]

    def arrive(self, lot, step):
        if STATION[step] == 2:
            self.env.process(self.prepare(lot, step))
        else:
            super().arrive(lot, step)

    def prepare(self, lot, step):
        entered = self.env.now
        op = yield self.ops.get(lambda x: x == "PO2")
        yield self.env.timeout(LOAD[step])
        yield self.ops.put(op)
        super().arrive(lot, step)
        self.events[-1]["queue_in"] = entered

    def finish_visit(self, lot, step, record):
        if STATION[step] == 2:
            record["end"] = None
            self.env.process(self.unload(lot, step, record))
        else:
            super().finish_visit(lot, step, record)

    def unload(self, lot, step, record):
        op = yield self.ops.get(lambda x: x == "PO2")
        yield self.env.timeout(UNLOAD[step])
        yield self.ops.put(op)
        record["end"] = self.env.now
        super().finish_visit(lot, step, record)


class ProductSetup(Fab):
    def setup_minutes(self, previous, step, product):
        return super().setup_minutes(previous, step, product) if previous and previous[1] != product else 0.


class OverlapSetup(Fab):
    def changeover(self, machine, step, lot, queued_at):
        duration = super().changeover(machine, step, lot, queued_at)
        if not duration:
            return 0.
        overlap = max(0., machine["unload_end"] - max(queued_at, machine["unload_start"]))
        return max(0., duration - overlap)


class NoLithoPM(Fab):
    def pm(self, machine, index):
        if machine["station"] != 2:
            yield from super().pm(machine, index)


MODELS = {"external_handling": ExternalHandling, "product_setup": ProductSetup,
          "overlap_setup": OverlapSetup, "no_litho_pm": NoLithoPM}


def measure(case):
    name, pattern, rep = case
    cfg = Config(mix=True, thesis_reference=True, personnel_constraints=False,
                 days=574, warm_days=154, interval=120, D=pattern, rep=rep)
    result, *_ = MODELS[name](cfg).run()
    return dict(convention=name, pattern=pattern, rep=rep, ct_minutes=result["mean_ct"],
                wip_lots=result["wip"], lots_week=7*result["throughput_day"])


if __name__ == "__main__":
    cases = [(name, pattern, rep) for name in MODELS for pattern in (0, 1) for rep in range(15)]
    with ProcessPoolExecutor(6) as pool:
        rows = list(pool.map(measure, cases))
    pd.DataFrame(rows).to_csv(Path(__file__).resolve().parents[2]/"results/litho_conventions.csv", index=False)
