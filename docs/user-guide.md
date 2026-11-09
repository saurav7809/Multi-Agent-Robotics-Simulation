# Operator guide

## Launch a mission

1. Start FastAPI and Vite using the [Windows quick start](../README.md#quick-start-on-windows).
2. Choose a mission in **Mission setup**. Loading a preset creates a new run and selects its default policy.
3. Set the fleet size and radio range, then choose **Apply configuration**. Expand **Advanced settings** to adjust arena dimensions, obstacle and target counts, drone speed, mission duration, packet loss, delay, stream rate, and seed.
4. Click **Start**. Use **Pause** and **Resume** to inspect a run. **Playback speed** changes the target pace immediately.
5. Click **Reset** to replay the same setup. **Randomize arena** changes the seed and starts a fresh run with the applied settings.

## Inspect the fleet

Select a drone in the arena or in the fleet selector. The inspector shows its position, velocity, state, battery, neighbors, radio status, and current task. **Grid**, **Links**, and **Trails** control overlays. Zoom in before dragging to pan. **Fit arena** restores the original view.

## Inject failures

- Select **Leader failure** and start the run. At eight simulated seconds, the current primary leader fails. Watch the amber leader ring and the event log as surviving drones elect a replacement.
- Select **Communication failure** to isolate part of the fleet from eight to sixteen simulated seconds. The consensus chart tracks estimate spread as messages resume.
- Select a drone and use **Fail agent**, **Drain battery**, or **Disable radio**. Restore a failed drone with **Restore agent**. Restore a radio with **Restore radio**. **Random failure** picks one operational drone using the run seed.

## Compare and export

Use the analytics tabs to inspect mission progress, fleet health, radio behavior, task distribution, and consensus when available. **Save reference** pins a snapshot for comparison across run resets in the current browser session. For a reproducible comparison, reuse the same scenario and seed, change one parameter, and compare at the same simulated time.

Use **Export** to download metrics as CSV or the complete retained run data as JSON. Use the event log filter to find mission, fault, radio, task, and coordination events.
