from pathlib import Path
import json,zipfile,hashlib,sys
import pandas as pd
R=Path(__file__).resolve().parent
D=R/"results"
f=pd.read_csv(D/"final_precision.csv")
precision=f"{int(f.precision_pass.sum())}/96 finite-window cell means have relative 95% interval half-width below 5%. The largest half-width is {100*f.relative_halfwidth.max():.2f}%."
note=f"""
## Precision confirmation and long-run behavior

For the complete runnable folder, download and extract the project ZIP from the GitHub release. It includes the large result tables, SQLite audit sample, all figures, and the offline HTML dashboard. The public source tree provides the model, analysis scripts, key result tables and Tableau workbook.

{precision} The original balanced experiment supports paired factorial contrasts across all 16 combinations. The follow-up estimates use 6,989 independent confirmation runs and 256 fresh replications for the one case above 5% in that first confirmation. Every run retains its four Parquet tables locally. The downloadable package contains all 7,245 follow-up responses in compressed CSV. Reproduce with confirm_precision.py, confirm_last_cell.py, final_precision.py and long_horizon.py after installing the project dependencies. The archive of raw events supplied with the original study covers the original design and its sensitivity runs. The confirmation event files can be generated with the follow-up scripts.

At 85% equal starts, baseline cycle time was 39.10 hours in the 102-run confirmation (95% interval ±0.79 hours). Constant starts had already met the criterion at 26.72 ±0.39 hours. The difference between those estimates is 12.38 hours. The original paired factorial gave 40.56 and 26.72 hours. Use the balanced design for interaction and attribution estimates, which depend on shared replication seeds. Precision applies to each mean separately. Selecting cells for confirmation based on pilot uncertainty does not give simultaneous 95% coverage across all cells.

The ten-year check used six fresh replications per flagged cell. With 95% nominal load, equal starts, and ACD, mean daily WIP rose from 19.65 lots in year one to 134.71 in year ten. Estimates for this cell depend on the chosen horizon. See results/long_horizon_wip.csv. For the benchmark conditions, see [the failed external comparison](BENCHMARK.md).
"""
for target in ["README.md","FINDINGS.md","VERIFICATION.md"]:
    p=R/target
    s=p.read_text(encoding="utf-8-sig").split("## Precision confirmation and long-run behavior")[0].rstrip()
    p.write_text(s+"\n"+note,encoding="utf-8")
p=R/"BI_HANDOFF.md"
s=p.read_text(encoding="utf-8-sig").replace("The delivered interactive dashboard is HTML/Sites, with an offline copy. No native PBIX or TWB is claimed.","The packaged Tableau workbook and the offline HTML dashboard both accompany the project.")
p.write_text(s,encoding="utf8")
p=R/"dashboard/dist/index.html"
s=p.read_text(encoding="utf-8-sig")
s=s.replace("the published output benchmark is not reproduced, and some cells miss the requested 5% precision.","The external benchmark failed. "+precision+" Factorial charts retain their original paired estimates.")
if "confirmed-estimate" not in s:
    s=s.replace('<div class="controls">','<p id="confirmed-estimate" aria-live="polite"></p><div class="controls">',1)
    j=json.dumps(f.to_dict("records"))
    js="const finalEstimates="+j+";function showFinal(){const r=finalEstimates.find(x=>x.view===$(\x27view\x27).value && x.load===Number($(\x27load\x27).value) && x.scenario===$(\x27scenario\x27).value);if(r)$(\x27confirmed-estimate\x27).textContent=\x27Final cell mean: \x27+r.mean_hours.toFixed(2)+\x27 ± \x27+r.halfwidth.toFixed(2)+\x27 hours (95% CI, n=\x27+r.n+\x27, \x27+r.source+\x27).\x27;}[\x27view\x27,\x27load\x27,\x27scenario\x27].forEach(k=>$(k).addEventListener(\x27change\x27,showFinal));showFinal();"
    s=s.replace("</script></body>",js+"</script></body>")
p.write_text(s,encoding="utf8")
p=R/"analysis.ipynb"
nb=json.loads(p.read_text(encoding="utf8"))
if not any("final_precision.csv" in "".join(c.get("source",[])) for c in nb["cells"]): nb["cells"].append(dict(cell_type="code",metadata={},execution_count=None,outputs=[],source=["display(pd.read_csv(D/'final_precision.csv'))\n","display(pd.read_csv(D/'thesis_reference.csv').groupby('D')[['mean_ct','wip']].mean())\n","display(pd.read_csv(D/'long_horizon_wip.csv').groupby(['scenario','year']).mean_daily_wip.mean().unstack())"]))
p.write_text(json.dumps(nb,indent=2),encoding="utf8")
