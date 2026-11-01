# Model and parameter register

This is a reproducible research implementation, not a certified reproduction of an Intel operating fab.
The supplied brief reverses two mechanisms. **B reduces lithography setups; C halves implant repair duration.**
There is no published implant setup or lithography random repair distribution in the sources located. Those were not invented.

## Source register

1. Ingy A. El-Khouly (2015), *Investigation of WIP Management for Control of Semiconductor Manufacturing Segments*, Chapter 4, printed pp. 48-62 (PDF pp. 65-79).
   https://doras.dcu.ie/20816/1/Final_Thesis%2BAppendices.pdf
   Numerical register: steps 1..6 process 225/30/55/50/255/10 minutes; diffusion batch 3, load/unload 20/40; implant 15/15; lithography 10/10. PM: 75/1440, 120/720, 30/720 minutes. Implant uptime U(1440,4560), repair U(360,480). Lithography changeover: recipe 10, product 5, both 12 minutes. Mix 51:30:3. Production staff: 3 x 60 minutes off per 720; technician: 45+45+30. Benchmark at exponential interval 120: CT 1813 minutes, WIP 15.66; constant starts: 1161 minutes, WIP 9.61.
2. H. Wang (2015), *Optimal Control of Non-Conventional Queueing*, Table 4.1, p. 77, corroborates station load/unload assignments.
   https://etd.ohiolink.edu/acprod/odb_etd/ws/send_file/send?accession=ucin1427799942&disposition=attachment
3. Leon McGinnis (2016), Intel Mini-Fab discussion and operator qualification diagram.
   https://leonmcginnis.com/wp-content/uploads/2023/04/196.pdf
4. Factory Physics VUT formulation and its single-server scope:
   https://www.informs-sim.org/wsc04papers/141.pdf
5. SimPy resource semantics:
   https://simpy.readthedocs.io/en/stable/topical_guides/resources.html

The original Kempf ASU URL was inaccessible. El-Khouly Table 4-3 conflicts with its station descriptions and Table 4-1 on steps 4/5 load/unload. We use the station descriptions, corroborated by Wang. The implementation is explicitly a resolved published-source variant.

## Implemented operational conventions (not claimed to be published parameters)

- One lot is the entity; minutes are the internal unit. One product Pa is used in the factorial. Two products plus test wafers are included in the extension and benchmark cases.
- FIFO at implant/lithography. Diffusion selects the oldest eligible compatible group: identical step; at most one test lot; step 5 cannot mix Pa and Pb. An ineligible older group can be bypassed by an eligible group. This is necessary batch eligibility, not a priority optimization.
- A: partial batch after 120 minutes without another compatible queued arrival; timer resets on such an arrival. Full batches launch immediately when a machine is available. Sensitivity examines other wait limits. This is an experimental policy, not a published constant.
- B: multiply all lithography setup matrix entries by 0.5. C: multiply implant repair duration by 0.5, retaining the same uptime stream. D: constant starts instead of exponential. The seed convention preserves common random numbers by source and replication; changes in event sequences can reduce the resulting correlation.
- PO1 serves diffusion/implant; PO2 serves implant/lithography. Diffusion retains operator identity for unload but releases that operator during processing. Implant load/unload can use different qualified operators. Setups occupy the lithography machine but do not request an operator: the available source does not specify setup labor.
- Operators take three 60-minute breaks at shift minutes 180/360/540; PO2 is offset 60 minutes. Technician breaks at 150/345/570 last 45/45/30 minutes. Tasks are nonpreemptive and can defer breaks. These exact placements are analyst choices; durations and qualification constraints are sourced.
- Fixed PM due dates, staggered like tools, are deferred until the current full run ends. Tools continue production while a PM request waits for a technician; PM starts only when both technician and tool are free. Actual PM duration excludes technician queueing. A single technician prioritizes repair, then PM, then breaks; active work is nonpreemptive. Uptime is elapsed calendar time after repair, including idle/PM time. Emergency failure suspends processing, which resumes after repair; operator handling completes nonpreemptively and subsequent work waits for repair. PM and repair may overlap in calendar time if failure occurs during PM; do not add their fractions without taking an interval union.
- Transport time, yield loss, test recirculation, process qualification and rework are absent. Test lots traverse the same six steps once. Product mix extension is therefore not a complete original test-wafer lifecycle.

## Estimands and observation windows

Cycle time uses departures within the measurement window, including carry-in lots. Unfinished lots remain in exports (NULL end); they are not treated as completed. WIP is integrated over every lot's clipped residency, including carry-in/carry-out, not a sampled average. Step WIP uses the same exposure calculation. The standard finite-window Little's-law estimate can differ at the boundaries; step exposures sum exactly to total WIP. A departure-cohort estimator is suitable only after warm-up and under stability; output gates report drift and throughput balance.

X-factor denominator is 625 minutes of raw processing; load/unload sum to 220 minutes, so isolated handling-inclusive service is 845 minutes before setups, operator wait and batching. A deterministic network can still queue: absence of randomness does not eliminate synchronized batch arrivals or operator contention.

Nominal initial load uses a 115-minute reference lithography workload (105 handling+process, 10 reference setup minutes per lot) and 690/720 PM availability. Pilot simulation calibrates interval against observed occupied/available lithography time, including operator blocking. Report both productive utilization (process+handling+setup divided by availability) and occupied utilization. The three primary loads are calibrated baseline occupied utilization targets, not exact scenario utilization guarantees. Main cells share baseline starts; a separate equal-utilization experiment calibrates starts for every scenario. Report achieved utilization and throughput, not just target labels.

Completed occupied/activity intervals crossing the warm boundary are clipped. An activity unfinished at the final horizon is absent from the activity-duration summary, producing at most one run per machine of truncation; event/WIP residence is retained. This is small at long horizons and explicitly checked through the accounting diagnostics.

## Interpretation

A factorial effect is average improved-minus-baseline response over the other factors. It is not an additive physical share of raw cycle time. Shapley allocation distributes the baseline-to-all-improvements gain across factors using all 16 cells and sums exactly to that gain; negative allocations are possible. Queue residence by step is a separate descriptive decomposition. Neither establishes real-factory causality.

VUT uses measured station interarrival SCV and elapsed seized-machine service SCV, including in-service downtime/operator waits. The single-server formula is shown as requested, but implant has two servers: the multiserver approximation is the fairer comparator. Idle-time failures and PM are vacations that elapsed service does not fully capture. Re-entrant arrival autocorrelation, synchronized batches, shared labor and technician dependence violate independence assumptions. Diffusion adds the renewal full-batch formation estimate (b-1)/(2 lambda_recipe) to a batch-level two-server estimate; the formation formula is not valid for arbitrary partial-batch policies and is labeled accordingly.
