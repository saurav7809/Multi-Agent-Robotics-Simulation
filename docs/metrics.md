# Simulation metrics

Distances use world units and times use simulated seconds. The engine samples once per simulated second and records a final sample at completion or timeout. The JSON export includes the current snapshot and recent events alongside the history.

| Metric | Calculation |
| --- | --- |
| Mission progress | Scenario score scaled to 0–100 as described below |
| Area coverage | 100 × visited valid cells ÷ valid cells. A cell is valid when its center clears static obstacle bodies by the drone radius |
| Average battery | Sum of current battery percentages ÷ total fleet size, including failed drones |
| Failure rate | 100 × failed drones ÷ total fleet size |
| Collision count | Number of newly detected overlapping drone–drone or drone–obstacle pairs. A continuing overlap counts once until the pair separates |
| Connectivity | 100 × size of the largest eligible radio component ÷ operational drones, or zero when no drones are operational |
| Average task time | Mean of completion time minus discovery time for completed targets. Known targets start at time zero. This value is unset until a target completes |
| Average distance | Total integrated movement distance ÷ total fleet size. Movement before an agent fails remains part of its total |
| Coordination efficiency | 100 × productive agent-ticks ÷ operational agent-ticks. Exploring, moving, executing, and communicating contribute productive ticks |
| Consensus spread | Largest estimate minus smallest estimate among operational drones, expressed as a percentage on the chart |
| Consensus convergence time | First simulated timestamp when at least two operational drones share one radio component and their spread has stayed at or below 0.025 for two seconds after packet delivery |

Connectivity measures radio reachability at the latest discovery round. Packet delivery divides cumulative delivered packets by cumulative offered deliveries, including loss and packets still in flight. At 100% configured loss, eligible inter-drone links disappear. The dashboard uses a subset of edges for readability while connectivity uses the full eligible graph.

## Mission scoring

- **Exploration** uses coverage ÷ 80% × 100, capped at 100.
- **Formation** multiplies the fraction of the base-to-gate trip completed by $0.75+0.25\times\mathrm{alignedFraction}$. Progress reaches 100 when the lead position is within 44 units of the gate, at least two drones are available, and at least 75% of available drones are within 48 units of their stations. The leader-failure preset also requires a replacement leader. When no leader policy is selected, the scoring observer uses the available fleet's center and spread.
- **Navigation** divides the available drones that have crossed into the 116-unit gate radius by the required count, which is 80% of available drones rounded up.
- **Search and rescue** weights discovered targets at 35% and completed targets at 65%. Multi-target allocation uses completed targets ÷ total targets.
- **Communication recovery** progresses through the scheduled blackout. After radios return, progress rises as spread shrinks and reaches 100 once connectivity and agreement hold for two simulated seconds. With another policy selected, the recovery check uses connectivity.
