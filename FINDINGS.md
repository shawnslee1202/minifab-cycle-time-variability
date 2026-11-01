# Findings and interpretation



## Decision at 85% baseline load (equal starts)



Baseline mean cycle time is **40.56 +/- 9.90 hours** (95% replication CI), throughput **8.414 lots/day**, WIP **14.27 lots**. Release smoothing alone gives **26.72 +/- 0.39 hours**. The lowest tested mean is **25.23 hours (BCD)**. All four changes give **27.46 hours**, so implementing every proposed change is not optimal.



No tested combination meets the illustrative **24-hour** mean-cycle-time target. There is therefore no defensible cheapest feasible package for that target. For a looser target, use the dashboard's editable cost and target inputs. Costs A/B/C/D = 1/3/5/2 are relative assumptions, not dollar estimates. The full table is in budget.csv; both mean-only and upper-95%-CI feasibility are shown.



96/96 cell means meet the 5% precision criterion for the measured horizon (maximum relative half-width 4.87%). The balanced factorial uses 960 runs. Two fixed confirmation stages add 6,989 and 256 runs. See [final cell estimates](results/final_precision.csv) and [external benchmark investigation](BENCHMARK.md). All factorial contrasts below use the balanced experiment.



## Attribution of the baseline-to-all difference



The Shapley allocation distributes the baseline-to-ABCD gain across all permutations of the four improvements, using the full factorial. It is additive by construction and allows negative shares. It does not claim that a source occupies that percentage of all cycle time. The gain being allocated is 13.10 hours. Direct station queue and service residence is separately available in the event tables.



| factor   |   hours_saved |   halfwidth |
|:---------|--------------:|------------:|
| D        |     14.0127   |   10.2201   |
| B        |      1.90599  |    1.44082  |
| C        |     -0.194905 |    0.793628 |
| A        |     -2.62611  |    1.10196  |



The largest two-factor interaction at this load is **BD**. Its improved-minus-baseline factorial interaction effect is +1.647 hours; the difference-in-differences is twice that, **+3.294 hours**. Signs are not reversed to make every improvement look beneficial.



## Load, capacity and policy interpretation



See operating_equal_starts.png and operating_equal_utilization.png. Equal-starts cells share a release interval within each load, and report their achieved output rate. The separate equal-utilization experiment calibrates interval using independent pilot runs, targeting occupied/available lithography time. Achieved values remain stochastic and differ from their targets; maximum discrepancy is 2.82 percentage points. These are approximately matched-utilization comparisons, not exactly equal utilization.



The published-source correction matters: B acts at lithography, C at implant. C can affect lithography through staff/technician scheduling and arrival patterns, but it does not directly halve lithography repair time. Lithography has PM and no random breakdown mechanism in this source variant. The report cannot support the brief's proposed claim that lithography random repairs dominate at high load.



Partial batches trade formation delay against furnace capacity. Their effect can be harmful even at lower load when small batches increase processing and operator work per lot. Short timeouts are not uniformly better. Setup reduction is modest compared with release smoothing in the 85% experiment. Repair reductions are not monotonic in this operational model: changed event timing, shared personnel and deferred maintenance can offset direct time savings. Treat small, uncertain gains as unresolved rather than causal reversals in a real fab.



## Statistical protocol and limits



Independent pilot replications selected a 90-day warm-up. The final design contains 960 factorial runs: 16 cells x two comparison views, with 5 replications at 70% and 85% for 365 measurement days, and 20 at 95% for 730 measurement days. All runs use an additional 90 warm-up days. Seeds are independent between replications and shared by source across cells. The paired contrast tests and Shapley CIs use replication as the independent unit, never individual lots.



The original balanced factorial precision audit found: 34 of 96 cells have a mean-CT 95% CI half-width of at least 5%; the maximum is 30.6%. High-load point estimates and rankings must be read with those wide intervals. These outputs complete a finite-horizon experimental study, not the brief's stronger certification of all steady-state means to 5%. Warm-up plots, sensitivity tables, half-window WIP comparisons and precision flags are supplied rather than suppressing failed checks. A positive drift flag is a warning, not a mathematical instability proof. A non-significant drift test is not proof of stationarity.



Maximum ordinary Little's-law boundary error is 6.09%; maximum step-to-total WIP identity error is 2.84e-14 lots. The identity is exact pathwise accounting; Little's law uses a departure-cohort estimate with boundary mismatch. The maximum input/output imbalance is 5.64%. See stability_summary.csv before treating a high-load cell as steady state.



ANOVA includes replication blocks, main effects and all two-factor interactions. Raw/log residual diagnostics are included. Classical ANOVA p-values are descriptive because common random numbers create within-replication dependence; paired factorial-contrast t-tests are primary. Multiple comparisons are unadjusted and exploratory. Higher-order interactions are available through the saturated factorial/Shapley allocation but are omitted from the two-factor ANOVA; residual lack of fit can therefore reflect them. The log model is a sensitivity check, not an automatic cure for correlated errors. Percentiles are average run-level p95 estimates; no precision guarantee is made for the tail.



## Theory check



See theory_baseline.csv for per-station SCVs, effective service time, utilization, simulated queue time, naive single-server VUT and the multiserver correction. Implant has two servers, so applying the one-server expression literally is structurally inappropriate. Diffusion combines a batch-level queue approximation with (b-1)/(2*lambda_recipe) formation delay for full batches. Partial-batch cells are extrapolations, not validated use of that corollary. Effective service is measured from machine seizure to release; vacations while idle are not fully captured. Re-entrant correlations, shared operators and scheduled maintenance also violate the approximation's assumptions.



## Published-output comparison: not validated



The cited thesis reports 1813 minutes CT and 15.66 lots WIP for exponential starts at a 120-minute interval (mixed products). This implementation with explicit qualified operators, breaks and technician coordination is overloaded at that rate. Its finite-horizon outputs in extras.csv are **not** a steady-state benchmark match. Removing personnel constraints in reference_check.py improves throughput but still does not reproduce the cited output; reference.csv contains that diagnostic. The source's inconsistent load/unload table and incompletely specified personnel/maintenance dispatch rules prevent claiming exact replication. Parameter correspondence and unit tests are not equivalent to empirical/published-output validation.



Use the results as a transparent research variant and a reproducible method demonstration. Before operational use or an academic claim of Intel Mini-Fab replication, resolve source conventions and reconcile the benchmark. Do not use the brief's resume template to claim a validated Intel model or attribute gains to lithography random repair.



## Scope



The product-mix/test-lot extension is implemented, using one pass through the common route and published batch compatibility. It does not model test recirculation or process qualification. One-factor timeout/setup/repair sweeps are completed. Optional outage recovery, wet-clean limits, alternate dispatching and CONWIP were not included in the requested core deliverables.



All structural numerical values, source conflicts and operational conventions are listed in MODEL.md. Source references: El-Khouly (2015), Chapter 4; Wang (2015), Table 4.1; McGinnis (2016); Factory Physics simulation paper (2004). Links are in MODEL.md.

## Precision confirmation and long-run behavior

For the complete runnable folder, download and extract the project ZIP from the GitHub release. It includes the large result tables, SQLite audit sample, all figures, and the offline HTML dashboard. The public source tree provides the model, analysis scripts, key result tables and Tableau workbook.

96/96 finite-window cell means have relative 95% interval half-width below 5%. The largest half-width is 4.87%. The original balanced experiment supports paired factorial contrasts across all 16 combinations. The follow-up estimates use 6,989 independent confirmation runs and 256 fresh replications for the one case above 5% in that first confirmation. Every run retains its four Parquet tables locally. The downloadable package contains all 7,245 follow-up responses in compressed CSV. Reproduce with confirm_precision.py, confirm_last_cell.py, final_precision.py and long_horizon.py after installing the project dependencies. The archive of raw events supplied with the original study covers the original design and its sensitivity runs. The confirmation event files can be generated with the follow-up scripts.

At 85% equal starts, baseline cycle time was 39.10 hours in the 102-run confirmation (95% interval ±0.79 hours). Constant starts had already met the criterion at 26.72 ±0.39 hours. The difference between those estimates is 12.38 hours. The original paired factorial gave 40.56 and 26.72 hours. Use the balanced design for interaction and attribution estimates, which depend on shared replication seeds. Precision applies to each mean separately. Selecting cells for confirmation based on pilot uncertainty does not give simultaneous 95% coverage across all cells.

The ten-year check used six fresh replications per flagged cell. With 95% nominal load, equal starts, and ACD, mean daily WIP rose from 19.65 lots in year one to 134.71 in year ten. Estimates for this cell depend on the chosen horizon. See results/long_horizon_wip.csv. For the benchmark conditions, see [the failed external comparison](BENCHMARK.md).
