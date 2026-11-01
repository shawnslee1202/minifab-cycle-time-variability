"""Generate the two-page PDF, detailed findings, README and analysis notebook."""

from pathlib import Path

import json,math,textwrap

import pandas as pd

import numpy as np

from reportlab.pdfgen import canvas

from reportlab.lib.colors import HexColor,white

from reportlab.platypus import Paragraph,Table,TableStyle

from reportlab.lib.styles import ParagraphStyle

from reportlab.lib.enums import TA_LEFT

ROOT=Path(__file__).resolve().parent;D=ROOT/'results';F=ROOT/'figures'

INK=HexColor('#17324a');TEAL=HexColor('#087f8c');MUTED=HexColor('#586e80')

STYLE=ParagraphStyle('body',fontName='Helvetica',fontSize=9,leading=12,textColor=INK,spaceAfter=5)

def para(c,text,x,y,width,size=9,color=INK):

    st=ParagraphStyle('p',parent=STYLE,fontSize=size,leading=size*1.35,textColor=color)

    p=Paragraph(text,st);w,h=p.wrap(width,1000);p.drawOn(c,x,y-h);return y-h-7



def report():

    summary=pd.read_csv(D/'summary.csv');bud=pd.read_csv(D/'budget.csv');sp=pd.read_csv(D/'shapley.csv');ef=pd.read_csv(D/'effects.csv')

    val=json.loads((D/'validation.json').read_text());s=summary[(summary.view=='equal_starts')&(summary.load==.85)].set_index('scenario')

    base=s.loc['Baseline'];best=s.loc[s.mean_hours.idxmin()];smooth=s.loc['D'];allr=s.loc['ABCD']

    g=sp[(sp.view=='equal_starts')&(sp.load==.85)].sort_values('hours_saved',ascending=False)

    inter=ef[(ef.view=='equal_starts')&(ef.load==.85)&(ef.term.str.len()==2)]

    top=inter.loc[inter.effect_hours.abs().idxmax()]

    wide=int((~summary.precision_pass).sum())

    precision_file=D/'final_precision.csv'

    precision_note="The balanced factorial had 34 of 96 cells above the precision limit."

    if precision_file.exists():

        final=pd.read_csv(precision_file)

        precision_note=(f"{int(final.precision_pass.sum())}/96 cell means meet the 5% precision criterion "

                        f"for the measured horizon (maximum relative half-width {100*final.relative_halfwidth.max():.2f}%). "

                        "The balanced factorial uses 960 runs. Two fixed confirmation stages add 6,989 and 256 runs.")

    target=json.loads((ROOT/'costs.json').read_text())['target_hours']

    findings=f'''# Findings and interpretation



## Decision at 85% baseline load (equal starts)



Baseline mean cycle time is **{base.mean_hours:.2f} +/- {base.halfwidth:.2f} hours** (95% replication CI), throughput **{base.throughput:.3f} lots/day**, WIP **{base.wip:.2f} lots**. Release smoothing alone gives **{smooth.mean_hours:.2f} +/- {smooth.halfwidth:.2f} hours**. The lowest tested mean is **{best.mean_hours:.2f} hours ({best.name})**. All four changes give **{allr.mean_hours:.2f} hours**, so implementing every proposed change is not optimal.



No tested combination meets the illustrative **{target:g}-hour** mean-cycle-time target. There is therefore no defensible cheapest feasible package for that target. For a looser target, use the dashboard's editable cost and target inputs. Costs A/B/C/D = 1/3/5/2 are relative assumptions, not dollar estimates. The full table is in budget.csv; both mean-only and upper-95%-CI feasibility are shown.



{precision_note} See [final cell estimates](results/final_precision.csv) and [external benchmark investigation](BENCHMARK.md). All factorial contrasts below use the balanced experiment.



## Attribution of the baseline-to-all difference



The Shapley allocation distributes the baseline-to-ABCD gain across all permutations of the four improvements, using the full factorial. It is additive by construction and allows negative shares. It does not claim that a source occupies that percentage of all cycle time. The gain being allocated is {base.mean_hours-allr.mean_hours:.2f} hours. Direct station queue and service residence is separately available in the event tables.



{g[['factor','hours_saved','halfwidth']].to_markdown(index=False)}



The largest two-factor interaction at this load is **{top.term}**. Its improved-minus-baseline factorial interaction effect is {top.effect_hours:+.3f} hours; the difference-in-differences is twice that, **{top.difference_in_differences:+.3f} hours**. Signs are not reversed to make every improvement look beneficial.



## Load, capacity and policy interpretation



See operating_equal_starts.png and operating_equal_utilization.png. Equal-starts cells share a release interval within each load, and report their achieved output rate. The separate equal-utilization experiment calibrates interval using independent pilot runs, targeting occupied/available lithography time. Achieved values remain stochastic and differ from their targets; maximum discrepancy is {val['max_util_target_error_equal_util']*100:.2f} percentage points. These are approximately matched-utilization comparisons, not exactly equal utilization.



The published-source correction matters: B acts at lithography, C at implant. C can affect lithography through staff/technician scheduling and arrival patterns, but it does not directly halve lithography repair time. Lithography has PM and no random breakdown mechanism in this source variant. The report cannot support the brief's proposed claim that lithography random repairs dominate at high load.



Partial batches trade formation delay against furnace capacity. Their effect can be harmful even at lower load when small batches increase processing and operator work per lot. Short timeouts are not uniformly better. Setup reduction is modest compared with release smoothing in the 85% experiment. Repair reductions are not monotonic in this operational model: changed event timing, shared personnel and deferred maintenance can offset direct time savings. Treat small, uncertain gains as unresolved rather than causal reversals in a real fab.



## Statistical protocol and limits



Independent pilot replications selected a 90-day warm-up. The final design contains {val['runs']} factorial runs: 16 cells x two comparison views, with 5 replications at 70% and 85% for 365 measurement days, and 20 at 95% for 730 measurement days. All runs use an additional 90 warm-up days. Seeds are independent between replications and shared by source across cells. The paired contrast tests and Shapley CIs use replication as the independent unit, never individual lots.



The original balanced factorial precision audit found: {wide} of {len(summary)} cells have a mean-CT 95% CI half-width of at least 5%; the maximum is {val['max_relative_halfwidth']*100:.1f}%. High-load point estimates and rankings must be read with those wide intervals. These outputs complete a finite-horizon experimental study, not the brief's stronger certification of all steady-state means to 5%. Warm-up plots, sensitivity tables, half-window WIP comparisons and precision flags are supplied rather than suppressing failed checks. A positive drift flag is a warning, not a mathematical instability proof. A non-significant drift test is not proof of stationarity.



Maximum ordinary Little's-law boundary error is {val['max_little_error']*100:.2f}%; maximum step-to-total WIP identity error is {val['max_step_wip_identity_error']:.3g} lots. The identity is exact pathwise accounting; Little's law uses a departure-cohort estimate with boundary mismatch. The maximum input/output imbalance is {val['max_flow_imbalance']*100:.2f}%. See stability_summary.csv before treating a high-load cell as steady state.



ANOVA includes replication blocks, main effects and all two-factor interactions. Raw/log residual diagnostics are included. Classical ANOVA p-values are descriptive because common random numbers create within-replication dependence; paired factorial-contrast t-tests are primary. Multiple comparisons are unadjusted and exploratory. Higher-order interactions are available through the saturated factorial/Shapley allocation but are omitted from the two-factor ANOVA; residual lack of fit can therefore reflect them. The log model is a sensitivity check, not an automatic cure for correlated errors. Percentiles are average run-level p95 estimates; no precision guarantee is made for the tail.



## Theory check



See theory_baseline.csv for per-station SCVs, effective service time, utilization, simulated queue time, naive single-server VUT and the multiserver correction. Implant has two servers, so applying the one-server expression literally is structurally inappropriate. Diffusion combines a batch-level queue approximation with (b-1)/(2*lambda_recipe) formation delay for full batches. Partial-batch cells are extrapolations, not validated use of that corollary. Effective service is measured from machine seizure to release; vacations while idle are not fully captured. Re-entrant correlations, shared operators and scheduled maintenance also violate the approximation's assumptions.



## Published-output comparison: not validated



The cited thesis reports 1813 minutes CT and 15.66 lots WIP for exponential starts at a 120-minute interval (mixed products). This implementation with explicit qualified operators, breaks and technician coordination is overloaded at that rate. Its finite-horizon outputs in extras.csv are **not** a steady-state benchmark match. Removing personnel constraints in reference_check.py improves throughput but still does not reproduce the cited output; reference.csv contains that diagnostic. The source's inconsistent load/unload table and incompletely specified personnel/maintenance dispatch rules prevent claiming exact replication. Parameter correspondence and unit tests are not equivalent to empirical/published-output validation.



Use the results as a transparent research variant and a reproducible method demonstration. Before operational use or an academic claim of Intel Mini-Fab replication, resolve source conventions and reconcile the benchmark. Do not use the brief's resume template to claim a validated Intel model or attribute gains to lithography random repair.



## Scope



The product-mix/test-lot extension is implemented, using one pass through the common route and published batch compatibility. It does not model test recirculation or process qualification. One-factor timeout/setup/repair sweeps are completed. Optional outage recovery, wet-clean limits, alternate dispatching and CONWIP were not included in the requested core deliverables.



All structural numerical values, source conflicts and operational conventions are listed in MODEL.md. Source references: El-Khouly (2015), Chapter 4; Wang (2015), Table 4.1; McGinnis (2016); Factory Physics simulation paper (2004). Links are in MODEL.md.

'''

    (ROOT/'FINDINGS.md').write_text(findings,encoding='utf8')

    readme=f'''# Mini-Fab cycle-time variability study



![85% variability allocation](figures/pareto_85.png)



**85% equal starts:** baseline {base.mean_hours:.2f} h; smooth starts {smooth.mean_hours:.2f} h; best tested {best.name} {best.mean_hours:.2f} h. The illustrative 24-hour target is infeasible among the tested combinations.



**External benchmark failed.** Published throughput and cycle time do not jointly match the reference runs. See [the comparison and capacity calculation](BENCHMARK.md). Source parameters place setups at lithography and random repairs at implant.



{precision_note} The [final estimates](results/final_precision.csv) give the confidence interval and sampling stage for each case. At 85% equal starts the confirmed baseline is 39.10 hours, compared with 26.72 hours for smooth starts. The budget and effects below come from the balanced factorial.



[Two-page report](report.pdf) · [Tableau dashboard](tableau/Mini-Fab.twbx) · [Detailed findings](FINDINGS.md) · [Download the project with the offline dashboard and SQL sample](https://github.com/shawnslee1202/minifab-cycle-time-variability/releases/latest)



## Variability budget



{bud[['scenario','cost','mean_hours','saved_hours','conservative_meets_target']].round(2).to_markdown(index=False)}



## Open the deliverables



- `report.pdf`: two-page write-up.

- `dashboard/dist/index.html`: interactive dashboard, works locally; hosted URL in `dashboard-url.txt` when publication succeeds.

- `figures/`: operating curves for both comparison views, Pareto, effects, interactions, residuals, Welch plot, theory and sensitivity charts (PNG and SVG).

- `analysis.ipynb`: reproducible analysis notebook.

- `results/`: run-level responses, confidence intervals, contrasts, ANOVA, Shapley allocation, budget, theory and verification tables.

- `results/reporting.sqlite`: SQL dashboard audit sample for six scenarios at 85%, replication 0, plus all summary results.

- `results/events/`: **complete** per-run visit/lot/activity tables. `event_manifest.csv` inventories the final factorial exports. The SQL sample is deliberately smaller than the complete archive.



## Reproduce



Python 3.12 was used. Create a virtual environment and run:



```shell

python -m pip install -r requirements.txt

python test_model.py

python experiment.py --phase pilot

python parallel_run.py --workers 4

python experiment.py --phase extras

python reference_check.py

python analyze.py

python audit.py

python build_reporting.py

python make_report.py

```



Run from this directory. `parallel_run.py` resumes completed run IDs and caches pilot calibrations. To run a different design, use a new results directory or archive the existing one; do not mix changed models/parameters into the same checkpoint. Long-run experiments produce a substantial complete event archive. Two comparison views each contain 16 cells at three loads; replication counts differ by load as recorded in `results/design.json`. `model.py` exposes Config and simulate for custom experiments.



The environment-specific bundled dependency path used during authoring is not embedded in model code. Requirements record the versions actually installed; newer versions may alter numerical/serialization behavior. The complete archive is data, not a runtime dependency.



## Statistical definitions



Minutes internally; hours in charts. Cycle-time means use post-warm-up departures; WIP is an exact time integral including carry-in/carry-out. CI units are independent replications. Common random streams support paired contrasts. Shapley values allocate baseline-to-all gain, not the full raw cycle time. Equal-utilization charts target measured occupied/available lithography time; achieved utilization is always reported. Costs in costs.json are editable illustrative relative units (A=1,B=3,C=5,D=2); there is no empirical dollar-cost claim.



## Reporting and BI



`views.sql` defines lot CT, daily moves, exact step WIP changes, machine utilization, and daily setup/PM/repair intervals. Daily downtime is split at midnight; machine batch time is not multiplied by batch size. Use `build_reporting.py` to rebuild SQLite and dashboard data. `all_events.duckdb.sql` provides full archive access; table grain and run ID must be preserved. Power BI/Tableau can ingest the supplied CSV summaries or SQLite/Parquet through an appropriate connector. A native packaged Tableau dashboard is included in tableau/Mini-Fab.twbx alongside the HTML dashboard.



Nine model tests passed. The audit additionally checks complete factorial cells, unique run IDs, event-file presence and the Shapley identity. See validation.json for achieved thresholds; passing structural tests does not erase failed statistical or published-output validation.

'''

    (ROOT/'README.md').write_text(readme,encoding='utf8')

    c=canvas.Canvas(str(ROOT/'report.pdf'),pagesize=(612,792));c.setTitle('Mini-Fab: Cycle-Time Variability Study')

    def header(page,title):

        c.setFillColor(INK);c.rect(0,716,612,76,fill=1,stroke=0);c.setFillColor(white);c.setFont('Helvetica-Bold',20);c.drawString(40,751,title);c.setFont('Helvetica',9);c.drawString(40,731,'RE-ENTRANT FAB / REPLICATED SIMULATION / 27 OCTOBER 2026')

        c.setFillColor(MUTED);c.setFont('Helvetica',8);c.drawString(40,22,'Research variant; all values are simulated. See accompanying source and audit tables.');c.drawRightString(572,22,str(page))

    header(1,'Cycle time: smooth the starts first')

    y=para(c,f'At 85% baseline load and equal starts, smoothing releases reduces mean cycle time from <b>{base.mean_hours:.1f} to {smooth.mean_hours:.1f} hours</b>. The best tested package is <b>{best.name}: {best.mean_hours:.1f} hours</b>. None meets the illustrative 24-hour target.',40,699,532,11)

    y=para(c,'Model correction: published setups are on lithography (B); random repairs are on implant (C). The brief assigns these to the opposite stations.',40,y,532,9)

    c.drawImage(str(F/'operating_equal_starts.png'),40,374,width=532,height=249,preserveAspectRatio=True,anchor='c',mask='auto')

    c.drawImage(str(F/'pareto_85.png'),40,132,width=532,height=230,preserveAspectRatio=True,anchor='c',mask='auto')

    para(c,f'The Pareto allocates the {base.mean_hours-allr.mean_hours:.1f}-hour baseline-to-all gain using all 16 cells. Negative values denote harmful contributions. Largest two-factor interaction: {top.term}, difference-in-differences {top.difference_in_differences:+.2f} h. Partial batching can lose more furnace capacity than it saves in waiting.',40,120,532,9)

    c.showPage();header(2,'Decision budget and validation limits')

    y=699

    for title,text in [

      ('Decision and cost model',f'The 24-hour target is infeasible. D alone costs 2 illustrative units and reaches {smooth.mean_hours:.2f} h; {best.name} reaches {best.mean_hours:.2f} h. Costs A/B/C/D = 1/3/5/2 are assumptions, not prices. The dashboard recalculates the least-cost feasible package for user-supplied costs and targets, including an upper-95%-CI screen.'),

      ('Experimental design',f'{val["runs"]} factorial runs cover 16 combinations, three loads and two views (equal starts and calibrated equal utilization). Measurement horizons: 365 days with five replications at 70%/85%; 730 days with 20 replications at 95%. All discard 90 warm-up days. Independent pilots, common random streams, blocked ANOVA, paired contrasts, raw/log residual checks and Shapley attribution are included.'),

      ('Verification and precision',precision_note+" Nine model tests passed. The 95% equal-starts ACD case showed rising WIP in a ten-year check, so its interval describes the finite measurement window. The 85% baseline confirmation gives 39.10 hours."),

      ('Theory and diminishing returns','VUT uses measured arrival and effective-service variability. Implant requires a two-server correction; diffusion additionally needs batch formation delay. Re-entrant dependence, operator contention and idle-time vacations explain limitations. Timeout/setup/repair sweeps are supplied. Faster repairs and shorter batch waits are not uniformly beneficial under the implemented resource schedules; do not extrapolate a monotonic benefit.'),

      ('External benchmark failed','At 120-minute exponential starts, the simplified reference mode measured 13,554 minutes CT and 114.23 lots WIP versus 1,813 minutes and 15.66 lots published. The 30-run comparison uses the reported mix probabilities, simpler batching, no personnel constraints and a 22-week warm-up. BENCHMARK.md explains the capacity discrepancy and a second independent comparison.'),

      ('Scope and sources','The core uses one product; a mixed-product/test-lot extension is included without test recirculation. Exact break timing, PM arbitration and interruption rules are declared modeling conventions. Optional disruption recovery, wet-clean constraints and CONWIP are outside this study. Sources: El-Khouly (2015), Chapter 4; Wang (2015), Table 4.1; McGinnis (2016); Factory Physics and Simulation (2004). Full links and parameter provenance appear in MODEL.md.')]:

        y=para(c,'<b>'+title+'</b>',40,y,532,10,color=TEAL);y=para(c,text,40,y+3,532,9)

    if y<35:raise RuntimeError('Report page 2 overflow: '+str(y))

    c.save()

    cells=[{'cell_type':'markdown','metadata':{},'source':['# Mini-Fab reproducible analysis\n','Read README.md and MODEL.md first. This notebook reads the completed experiment; cells can be rerun from the project directory. Statistical and published-validation failures are retained.']}]

    def code(src):cells.append(dict(cell_type='code',metadata={},execution_count=None,outputs=[],source=src.splitlines(True)))

    code("from pathlib import Path\nimport pandas as pd\nfrom IPython.display import display, Image\nROOT=Path.cwd()\nD=ROOT/'results'\nsummary=pd.read_csv(D/'summary.csv')\ndisplay(summary)")

    code("display(pd.read_csv(D/'budget.csv'))\ndisplay(Image(filename=str(ROOT/'figures'/'pareto_85.png')))")

    code("display(Image(filename=str(ROOT/'figures'/'operating_equal_starts.png')))\ndisplay(Image(filename=str(ROOT/'figures'/'operating_equal_utilization.png')))")

    code("display(pd.read_csv(D/'effects.csv'))\ndisplay(pd.read_csv(D/'anova.csv'))\ndisplay(pd.read_csv(D/'residual_diagnostics.csv'))")

    code("display(pd.read_csv(D/'theory_baseline.csv'))\ndisplay(pd.read_csv(D/'warmup_sensitivity.csv'))\ndisplay(pd.read_csv(D/'stability_summary.csv'))")

    code("import sqlite3\nwith sqlite3.connect(D/'reporting.sqlite') as db:\n    display(pd.read_sql_query('SELECT * FROM moves_per_day LIMIT 20', db))\n    display(pd.read_sql_query('SELECT * FROM utilization_by_machine LIMIT 20', db))")

    code("# Regenerate statistical tables and charts from completed runs.\n# from analyze import analyze\n# analyze()\n# To rerun a scenario:\n# from model import Config, simulate\n# result, events, lots, activity, wip = simulate(Config(A=1,D=1,days=365))")

    (ROOT/'analysis.ipynb').write_text(json.dumps(dict(cells=cells,metadata=dict(kernelspec=dict(display_name='Python 3',language='python',name='python3')),nbformat=4,nbformat_minor=5),indent=2),encoding='utf8')

    print('Wrote report.pdf, README.md, FINDINGS.md, analysis.ipynb')

if __name__=='__main__':report()

