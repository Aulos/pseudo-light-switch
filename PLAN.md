# PLAN — `pseudo_light_switch` (HA custom integration)

## Goal
A Home Assistant custom integration that exposes a single virtual **Light** entity backed by:
- an **on/off source** entity (switch, button, input_button, or event) → owns on/off
- a **Light** entity → owns everything else (brightness, color, color temp, effect, …)

The repo is laid out for one-click install from **HACS**.

## HACS repo layout
```
light-pseudo-switch/
├── custom_components/
│   └── pseudo_light_switch/
│       ├── __init__.py        # entry setup, listener registration
│       ├── manifest.json      # HACS / HA manifest
│       ├── const.py           # constants + config keys
│       ├── config_flow.py     # UI config (switch + light + options)
│       ├── light.py           # PseudoLightSwitch(LightEntity)
│       └── services.yaml      # (empty for v1; placeholder)
├── README.md                  # install + config + use cases
├── info.md                    # HACS side-panel info
├── hacs.json                  # HACS metadata
├── LICENSE                    # MIT (suggested)
└── .gitignore
```

`hacs.json`:
```json
{ "name": "Pseudo Light Switch", "render_readme": true, "homeassistant": "2024.1.0" }
```

## Configuration model
Config-flow options per entry (one entry = one pseudo light):
- `name` (default: `Pseudo Light`)
- `on_off_source` — entity picker, domains `switch` / `button` / `input_button` / `event`
- `light_entity` — entity picker, `light` domain
- `invert_state` (bool, default `false`) — only meaningful when `on_off_source` is a `switch`/`input_boolean`-like entity; inverts "on" ↔ "off" mapping
- `forward_on_off` (bool, default `false` for switch, **`true` for button/event**) — see *Detached mode* below
- `event_actions` (list, default `[]` = "any") — only for `event` sources; if non-empty, only listed event action values (e.g. `single_press`) trigger a toggle

Multiple entries supported → multiple pseudo lights.

## Detached mode — interpretation
The phrase *"the event should optionally also be send to the light entity, when the switch/button is detached"* is the one ambiguous bit. My reading:

- The **switch is always the on/off source of truth**. The pseudo light is "on" iff the switch is on.
- **`forward_on_off = false`** (default → "detached" in your wording): the pseudo light **does not** send on/off to the underlying light. Toggling the pseudo light toggles the switch only. The underlying light keeps whatever on/off state you set on it directly (e.g. via its own entity). Brightness/color/temp are still read/written through the light entity.
  - Use case: a smart button (`input_boolean` / momentary) that doesn't physically touch the bulb, or a Shelly 1 in *detached* relay mode that powers a smart bulb's mains but shouldn't cut its state.
- **`forward_on_off = true`** (attached): pseudo light forwards the on/off to the light entity too. Switch and light stay in sync.
  - Use case: a relay where you do want the bulb's on/off to follow the switch, just routed through the pseudo light UI so you can keep brightness/color/presets.

If your intended meaning is different (e.g. "detached" = the switch's state is ignored entirely and we mirror the light), call it out — I'll adjust.

## Runtime behavior

### State source semantics
- **`switch` source** — pseudo light **follows** the source's on/off state (optionally inverted). Pseudo light is "on" iff the (possibly inverted) source is "on". Reading the source is the only path to a state value.
- **`button` / `input_button` source** — pseudo light holds its **own** state (in-memory, defaults to `off` on reload). Each press of the source toggles the pseudo light.
- **`event` source** — pseudo light holds its **own** state. Each state change on the source (matching `event_actions` filter if set) toggles the pseudo light.

### Other behavior
- **Brightness / color / color temp / effect** → read from the light entity when the pseudo light is on; `None` (HA convention) when off.
- **Supported features** → mirrored from the underlying light at startup, intersected with what the pseudo light can actually do.
- **Availability** → available only if both source + light entities are available.
- **Updates** → listen to `state_changed` for the source AND the light; push updates to the pseudo light.
- **Commands**:
  - `turn_on`:
    1. if source is a `switch` → turn on switch (skip if already on)
    2. if source is `button`/`event` → just flip internal state to `on`
    3. if `forward_on_off` and light is off → turn on light
    4. apply brightness/color/color_temp via `light.turn_on` on the light entity
  - `turn_off`:
    1. if source is `button`/`event` → flip internal state to `off`
    2. if `forward_on_off` and light is on → turn off light
    3. if source is a `switch` → turn off switch

## Implementation phases
1. Repo skeleton: `hacs.json`, `info.md`, `manifest.json`, `LICENSE`, `README.md`, `.gitignore`, `const.py`.
2. `config_flow.py` (user + options flow).
3. `light.py` — `PseudoLightSwitch(LightEntity)` with:
   - state mirroring
   - feature inheritance
   - turn on / off + brightness/color/temp passthrough
4. `__init__.py` — entry setup, listener wiring.
5. `services.yaml` (empty stub).
6. `README.md` — install via HACS, config, examples.

## Verification
- `python -m script.hassfest` if HA dev env available; otherwise validate `manifest.json` / `hacs.json` JSON manually.
- Manual test in HA dev container or symlinked install:
  - Pseudo light entity appears with features matching the underlying light.
  - Flipping the switch externally updates the pseudo light.
  - Turning the pseudo light on/off moves the switch.
  - Brightness/color/temp edits on the pseudo light land on the light entity.
  - Underlying light unavailable → pseudo light unavailable.

## Open questions for you
1. ~Confirm the `forward_on_off` / "detached" interpretation above~ ✅ confirmed
2. OK with one config entry = one pseudo light (multi-instance via adding more entries)?
3. Any icon preference? Default: `mdi:light-switch`.
4. License: MIT OK, or do you want a different one?
5. **Event-source action filter** — for `event` sources, do you want a per-config list of action values that trigger a toggle (e.g. only `single_press`), or any state-change on the source toggles (simpler)? Current plan: list, default empty (= all).
