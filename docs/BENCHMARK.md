# External benchmark result: failed

At the published 120-minute mean interval, the reference implementation processes roughly the published number of lots per week but has much longer queues. This is an external validation failure. All operating recommendations in this repository describe the simulated variant.

| Release pattern | Published CT, min | Measured CT, min (95% half-width) | Published WIP | Measured WIP (95% half-width) | Measured lots/week |
|---|---:|---:|---:|---:|---:|
| Exponential | 1,813 | 13,554 ± 4,159 | 15.66 | 114.23 ± 35.93 | 83.29 |
| Constant | 1,161 | 3,121 ± 237 | 9.61 | 26.01 ± 1.97 | 83.90 |

The comparison uses 15 replications for each pattern, 104 weeks total per replication and a 22-week warm-up. It removes personnel contention, permits full batches of any products at the same step, and uses probabilities 0.61, 0.36 and 0.03. Handling times follow the station descriptions in the parameter register. Setup times and maintenance remain active. See [reference simulation](../minifab_cycle_time_variability/validation/thesis_reference.py), [run results](../results/thesis_reference.csv) and [El-Khouly, Chapter 4, §§4.1.5–4.6.3](https://doras.dcu.ie/20816/1/Final_Thesis%2BAppendices.pdf).

## What the capacity calculation establishes

At lithography, steps 3 and 6 occupy one machine for at least 75 and 30 minutes per lot. Fourteen shifts each supply 690 available minutes after PM. Under those assumptions, sustainable throughput cannot exceed 14 × 690 / 105 = **92 lots/week** even with zero setups. Table 4-7 reports 93.52 lots/week at the 107-minute input setting. A finite observation window can draw down inventory, and implementations can handle deferred maintenance differently. The bound identifies an incompatibility with a steady-state reading of the high-throughput data.

At the 120-minute setting, 84 lots/week leaves only 10 minutes per lot for setups and other lost capacity. The estimated setup demands were 9.78 minutes per completed lot for exponential starts and 10.10 for constant starts. The machine therefore operates close to saturation in this implementation. The capacity bound alone does not rule out the thesis result at 120 minutes. Matching that point would require further information about how the reference engine seized and released the machine, scheduled PM and triggered setups.

## Independent published specification

A second check uses the workforce experiment in the [NIST modular simulation paper, section VIII, Tables IV–VII](https://www.govinfo.gov/content/pkg/GOVPUB-C13-1d7d08a33cb9fca929f3de4019a1ceb6/pdf/GOVPUB-C13-1d7d08a33cb9fca929f3de4019a1ceb6.pdf). It has separate deterministic product streams, full same-step batches, 225 minutes for both furnace processes, 20-minute furnace unloading, independent implant repairs, and no PM or personnel breaks. Five replications each use 10,000 measurement hours after 10,000 warm-up hours. The source specifies a 10-minute lithography setup without an explicit trigger in its table. Both product-change and step-change conventions were tested.

The paper gives product 1 a 24.48-hour mean and 7.43 lots WIP with two operators. Using step-change setups produced 255.73 hours and 77.63 lots. Product-change setups produced 1,233.28 hours and 374.37 lots. Adding a second PO1 with step-change setups produced 23.38 hours and 7.10 lots, compared with 18.07 hours and 5.49 lots in the paper's corresponding three-operator case. The comparison also fails under these conventions. All combinations, including both products, are retained in [the results](../results/nist_reference.csv). This diagnostic is separate from the project factorial.

## Lithography conventions tested separately

Moving loading and unloading off the machine came closest. For random starts, the published 1,813 minutes falls inside the measured interval of 1,779–1,919 minutes. For constant starts, the same change yields 1,459 minutes, well above the published 1,161 minutes. Handling explains much of the gap, but this comparison does not establish how the reference engine works.

| Single change | Random starts, minutes per lot | Constant starts, minutes per lot | Output, lots/week (random / constant) |
|---|---:|---:|---:|
| Load and unload off the machine | 1,849 ± 70 | 1,459 ± 3 | 84.53 / 84.00 |
| Start a setup only when the product changes | 5,486 ± 1,866 | 1,728 ± 8 | 84.39 / 84.00 |
| Overlap setup with the previous lot’s unload | 2,407 ± 162 | 1,581 ± 3 | 84.56 / 84.00 |
| Remove scheduled lithography downtime | 3,606 ± 785 | 1,658 ± 5 | 84.55 / 84.00 |

Each entry gives the mean and 95% Student-t interval half-width across 15 independent runs. All four comparisons use the same seeds, arrival intervals, mix and observation windows as the reference runs above. In the first case, handling still takes operator time before and after machine processing. In the second, the published setup duration applies when the product changes. In the third, the next lot must already be waiting to use the remaining unload time. The fourth removes only lithography maintenance.

Both source processing times, 55 and 10 minutes, were already used. The baseline adds 10 minutes each for loading and unloading on both visits, for 105 machine minutes per lot. External handling reduces that to 65 minutes before setups. There was no separate processing-time correction to test.

The match rule required both published cycle times to lie inside the corresponding simulation intervals and both output rates to fall within 2% of 84 lots per week. Every convention met the output rule. None met both cycle-time criteria, so no convention qualified for the conditional 85% factorial rerun. The intervals describe simulation uncertainty; the published means were treated as fixed targets.

[120 run responses](../results/litho_conventions.csv) · [Simulation code](../minifab_cycle_time_variability/validation/litho_conventions.py). Reproduce from the repository root with `python -m minifab_cycle_time_variability.validation.litho_conventions`.
