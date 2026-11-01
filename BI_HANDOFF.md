# Power BI / Tableau handoff

The packaged Tableau workbook and the offline HTML dashboard both accompany the project.

Import these CSV tables without needing a database driver:

| File | Grain | Recommended visuals |
|---|---|---|
| results/summary.csv | view x load x scenario | CT vs throughput, precision flags, achieved utilization |
| results/runs.csv | one independent replication | CT, p95, WIP, machine time fractions |
| results/budget.csv | scenario at 85% equal starts | cost frontier, target feasibility |
| results/effects.csv | view x load x factorial contrast | signed effect Pareto with CI |
| results/shapley.csv | view x load x factor | baseline-to-all gain allocation |
| results/theory.csv | run x station | observed vs predicted queue time |
| results/stability_summary.csv | view x load x scenario | drift and flow-balance warnings |

Use view/load/scenario as filters. Do not average over view or load indiscriminately. Never add replication means as if they were lot counts. The run-level p95 field is not a pooled percentile. Tool occupied and process/load/unload/setup fractions overlap: do not stack them together. PM and repair can overlap; their sum is not unique downtime.

For detailed event reporting, connect to results/reporting.sqlite using a compatible SQLite connector/ODBC driver, or query the full Parquet archive with DuckDB and export a selected result to CSV. views.sql defines the reporting logic. events grain is a lot-step visit; activity grain is a machine interval. Furnace machine utilization must use activity, not summed lot-step duration, which would count the same batch three times.

Join runs to detailed tables using run_id (one-to-many). lot_id is only unique within run_id. A batch_id is only unique within run_id. Filter exit times to [warm_days*1440, (warm_days+days)*1440). Include carry-in/carry-out for WIP. NULL end means unfinished, not zero cycle time.

Costs are illustrative relative units. A confidence interval for mean CT is not a delivery-percentile guarantee. Include the failed validation gates prominently on any dashboard republished from this data.
# Native dashboard

Open tableau/Mini-Fab.twbx in Tableau Public or Desktop. The package contains four source tables, four worksheets and one dashboard. Operating curves use equal starts and the original balanced design. Step WIP is averaged across baseline replications at 85% load. Moves, targets and the cycle-time distribution use the SQL audit sample at replication 0. Moves cover the final 28 days; cycle time includes all measurement departures in that run. Rebuild with python build_tableau.py. The packaged structure and source paths have been checked.
