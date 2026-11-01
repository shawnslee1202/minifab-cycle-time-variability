# Verification record

Nine deterministic/resource/accounting tests passed on the final default model:

1. Route order and lot conservation.
2. Nonnegative event times and exact step-to-total residency accounting.
3. Full-batch size, recipe compatibility and diffusion operator identity.
4. No overlapping occupied runs on a machine.
5. Deterministic cycle-time decomposition including unavoidable batch/serial/operator waits.
6. Identical outputs for repeated seeds.
7. Partial-batch and mixed-product compatibility.
8. Exact accumulated processing work despite interruption/resumption.
9. PM duration excludes technician queueing and PM occurs on lithography.

Run `python test_model.py` to reproduce. `audit.py` checks all final factorial cells, event-file presence, unique IDs, Shapley additivity and half-window WIP trends. Final achieved statistical thresholds are in results/validation.json.

## Issues found and corrected before final runs

The first implementation acquired the tool while waiting for a maintenance technician. This inflated downtime. PM now acquires tool and technician together after the current run; the tool can keep producing while the technician is unavailable. A scheduling yield gives due maintenance a chance between production runs. All affected results were discarded from the final output set and rerun. Operators also release/reacquire their token if a tool fails while they await acquisition, rather than holding labor idle during repair.

## Checks that do not pass

The published output benchmark is not reproduced by this explicit-personnel variant, nor by the reduced-personnel diagnostic. Some 95% CIs exceed the requested 5% precision, and some finite-window Little's-law/drift diagnostics exceed desired tolerances. These are visible failed validation gates, not waived successes. See FINDINGS.md for interpretation and limitations. Passing code tests is not a claim of original-model replication or steady-state convergence.

## Final artifact checks — October 28, 2026

SQLite integrity_check returned `ok`; all six reporting views exist and the sample contains 140,447 lot-step rows. Full factorial Parquet querying counted 34,935,655 lot-step rows. The two-page PDF was rendered and visually reviewed; a chart footer overlap was corrected before delivery. Local dashboard checks covered comparison/load/scenario selection, the editable 30-hour target, the infeasible default 24-hour target, and CSV export; no JavaScript errors were observed. Owner-private Sites deployment succeeded. These artifact checks do not resolve the failed statistical gates above.

## Precision confirmation and long-run behavior

For the complete runnable folder, download and extract the project ZIP from the GitHub release. It includes the large result tables, SQLite audit sample, all figures, and the offline HTML dashboard. The public source tree provides the model, analysis scripts, key result tables and Tableau workbook.

96/96 finite-window cell means have relative 95% interval half-width below 5%. The largest half-width is 4.87%. The original balanced experiment supports paired factorial contrasts across all 16 combinations. The follow-up estimates use 6,989 independent confirmation runs and 256 fresh replications for the one case above 5% in that first confirmation. Every run retains its four Parquet tables locally. The downloadable package contains all 7,245 follow-up responses in compressed CSV. Reproduce with confirm_precision.py, confirm_last_cell.py, final_precision.py and long_horizon.py after installing the project dependencies. The archive of raw events supplied with the original study covers the original design and its sensitivity runs. The confirmation event files can be generated with the follow-up scripts.

At 85% equal starts, baseline cycle time was 39.10 hours in the 102-run confirmation (95% interval ±0.79 hours). Constant starts had already met the criterion at 26.72 ±0.39 hours. The difference between those estimates is 12.38 hours. The original paired factorial gave 40.56 and 26.72 hours. Use the balanced design for interaction and attribution estimates, which depend on shared replication seeds. Precision applies to each mean separately. Selecting cells for confirmation based on pilot uncertainty does not give simultaneous 95% coverage across all cells.

The ten-year check used six fresh replications per flagged cell. With 95% nominal load, equal starts, and ACD, mean daily WIP rose from 19.65 lots in year one to 134.71 in year ten. Estimates for this cell depend on the chosen horizon. See results/long_horizon_wip.csv. For the benchmark conditions, see [the failed external comparison](BENCHMARK.md).
