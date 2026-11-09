# Swarm algorithms

Each policy reads an agent and a local view and returns a preferred velocity and activity state. Navigation then applies collision avoidance to the chosen velocity.

## Boids

For agent $i$, let $p_i$ and $v_i$ be position and velocity. Neighbor separation adds unit vectors away from active peers closer than 52 units. Each peer's weight is $(52-d)/52$, where $d$ is its distance from $i$. Alignment uses $\operatorname{mean}(v_j)-v_i$ and cohesion uses $0.9(\operatorname{mean}(p_j)-p_i)$, capped at the drone's speed. The policy adds the weighted terms to a destination or patrol bias and caps the result at maximum speed.

A peer 26 units directly east contributes a westward separation vector with weight 0.5. A peer traveling north contributes a northward alignment correction if the receiving drone is stationary.

## Leader–follower

A fresh beacon carries the leader ID, origin time, pose, and velocity. Agents relay their locally preferred beacon. Each agent prefers the smallest eligible ID and uses beacon age to choose the freshest report for that ID. A beacon expires after $2.4+2D$ simulated seconds, where $D$ is configured packet delay in seconds. A drone promotes itself when it has no fresh beacon from a lower ID. Components can elect different leaders during a partition and reconcile when they reconnect.

Each follower aims for a deterministic station offset rotated by the beacon heading. Its desired velocity combines $1.15$ times the position error with the leader's advertised velocity. If the leader turns 90 degrees, the offsets turn with it.

## Distributed consensus

Each drone starts with a seeded estimate $x_i$ in the interval $[0,1]$. On a decision round with a new peer sample, it applies

$$
x_i \leftarrow x_i + 0.48\left(\operatorname{mean}(x_j)-x_i\right).
$$

Only fresh, received neighbor samples enter the mean. Isolated agents retain their estimates and continue steering toward the rendezvous they currently infer. For example, two drones starting at 0.2 and 0.8 and hearing each other update to 0.488 and 0.512 in one round. Agreement is based on estimate spread, so an irregular network can agree on a value that differs from the initial arithmetic mean.

## Distributed task auction

Each agent scores known unfinished targets using

$$
\mathrm{cost}(i,t)=\frac{\mathrm{distance}(i,t)}{\mathrm{maxSpeed}(i)}
+0.075(100-\mathrm{battery}(i))+\mathrm{switchCost}(i,t).
$$

Switching away from a different claimed task costs 2.5. Claims are compared by cost, then agent ID. An agent chooses its cheapest target it can win against recent neighboring bids. Reports expire after $1.6+D$ seconds. For example, two otherwise equal drones with travel estimates of three and five seconds favor the closer drone. Lower battery can reverse the ranking.

A drone must stay within 25 units for the target's required dwell. Explore requires 0.55 seconds, inspect 1.25 seconds, coverage 0.85 seconds, and rescue 1.4 seconds. The engine records a target's completion once, even if separate radio components send two drones to the same target.

## Predictive obstacle avoidance

Navigation estimates closest approach between a candidate velocity and a moving disk. For relative position $r$, relative velocity $v$, and look-ahead $H$, the closest point is at

$$
t=\operatorname{clamp}\left(-\frac{r\cdot v}{v\cdot v},0,H\right).
$$

A stationary relative velocity uses $t=0$. If a candidate approaches a disk or boundary too closely, the policy samples alternative headings and scores clearance and alignment with the preferred direction. It briefly favors the selected passing side to reduce oscillation. Nearby drones add separation and a lateral correction for predicted head-on encounters. The contact solver handles residual overlaps after integration.

## Grid coverage

Agents mark cells whose centers are within 49 units of their position. They exchange visited and blocked masks and the cell they intend to visit. The policy prefers nearby unseen cells, applies a small forward bias, and avoids recent peer claims. Lower agent IDs break conflicts on an existing claim. An intent expires after five seconds, allowing a drone to choose a different frontier when progress stalls.

For example, if a drone hears that its nearest unvisited cell is claimed by a peer, it picks another unseen cell. If it runs out of known frontier cells, it patrols and can update its plan after receiving fresh information.
