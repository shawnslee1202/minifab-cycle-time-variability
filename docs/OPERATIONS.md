# Reproducing the study

Run the commands from the repository root with the dependencies in requirements.txt. The short report rebuild uses the tracked summary tables and figures. For the original run tables, interim outputs and SQLite sample, extract the [v1.0.0 project ZIP](https://github.com/shawnslee1202/minifab-cycle-time-variability/releases/download/v1.0.0/minifab-project.zip) outside the checkout and copy the contents of its minifab/results directory into results. Use the current package commands with those files. The ZIP uses the original directory layout.

## Full simulation

Use a fresh checkout without restored run files for a full simulation. The runner resumes saved run IDs and pilot calibrations. Keep separate working directories for different model configurations. Allow several hours and at least 25 GB of disk space. Timing depends on worker count and hardware. The event-level files can be regenerated locally.

~~~sh
python -m minifab_cycle_time_variability.experiment.experiment --phase pilot
python -m minifab_cycle_time_variability.experiment.parallel_run --workers 4
python -m minifab_cycle_time_variability.experiment.experiment --phase extras
python -m minifab_cycle_time_variability.validation.reference_check
python -m minifab_cycle_time_variability.validation.thesis_reference
python -m minifab_cycle_time_variability.validation.nist_reference
python -m minifab_cycle_time_variability.analysis.analyze
python -m minifab_cycle_time_variability.validation.audit
python -m minifab_cycle_time_variability.experiment.confirm_precision --workers 4
python -m minifab_cycle_time_variability.experiment.confirm_last_cell
python -m minifab_cycle_time_variability.analysis.final_precision
python -m minifab_cycle_time_variability.experiment.long_horizon
python -m minifab_cycle_time_variability.reporting.build_reporting
python -m minifab_cycle_time_variability.reporting.build_tableau
python -m minifab_cycle_time_variability.reporting.make_report
python -m minifab_cycle_time_variability.reporting.update_release_views
~~~

The audit checks run IDs, coverage of the experiment, event exports and the allocation of cycle-time savings. See [verification](VERIFICATION.md). To query the original event archive, run python -m minifab_cycle_time_variability.reporting.query_events from the repository root after generating the event files and their manifest.

## Measures

The simulation clock runs in minutes. Charts report hours. Mean cycle time includes lots that leave after warm-up. Average work in process measures the time each lot spends in the factory during the observation window, including lots already present or still unfinished at its boundaries. Each independent run contributes one observation to the confidence interval.

Matched random streams support paired comparisons. Factor contributions allocate the difference between the baseline and the combined intervention. The equal-utilization comparison targets the fraction of available lithography time for which the machine is occupied. Actual utilization is recorded for each run. The cost file assigns relative costs of 1, 3, 5 and 2 units to factors A through D.

[Model and sources](MODEL.md) · [Study findings](FINDINGS.md) · [Reporting and SQL](BI_HANDOFF.md)
