# Pseudo Light Switch

A Home Assistant custom integration that exposes a single virtual **Light** entity backed by:

- an **on/off source** — a `switch`, `input_boolean`, `button`, `input_button`, or `event` entity
- a **Light** entity that owns brightness, color, and color temperature

The pseudo light's on/off is driven by the source; the rest of the light's state is read from (and written to) the underlying light.

## Use cases

1. **Shelly (or any relay) wired behind a smart bulb.** The relay is the `switch` source; the smart bulb is the `light`. Set `forward_on_off: true` if you also want the bulb to follow the relay, or leave it `false` for "detached" behavior where the relay's on/off doesn't break the bulb's state.
2. **Smart button / Zigbee remote mapped to a smart bulb.** A `button` or `event` entity toggles the pseudo light; `forward_on_off: true` (default for button/event) means the bulb follows the toggle.
3. **Any switch + light pair** that you want to expose as a single Light card in HA.

## Install (HACS)

1. HACS → ☰ → **Custom repositories** → **Add**.
2. Repository: `Aulos/light-pseudo-switch` (this repo).
3. Category: **Integration**.
4. HACS will download `custom_components/pseudo_light_switch/` into your HA `config/custom_components/` directory. Restart Home Assistant.
5. **Settings → Devices & Services → Add Integration → Pseudo Light Switch**.

## Configuration

Each config entry = one pseudo light. The flow has two steps:

### Step 1 — entities

| Field | Description |
|---|---|
| `name` | Friendly name (default: `Pseudo Light`) |
| `on_off_source` | Entity that drives on/off. Accepts `switch`, `button`, `input_button`, `event`. |
| `light_entity` | The real `light` that owns brightness / color / color-temp. |

### Step 2 — options (depend on source type)

| Source type | Option | Default | Meaning |
|---|---|---|---|
| `switch` | `invert_state` | `false` | Invert the on/off mapping (pseudo light "on" when switch is "off", and vice versa). Useful when the switch reports "on" while the actual load is "off" (e.g. a Shelly 1 in *detached* mode powering a dimmed bulb). |
| `switch` | `forward_on_off` | `false` | Also turn the underlying light on/off from the pseudo light. Default is `false` ("detached" — switch and light are independent on on/off). |
| `button` / `input_button` | `forward_on_off` | `true` | Also turn the underlying light on/off from the pseudo light. Default is `true` because a button press without forwarding would do nothing to the bulb. |
| `event` | `forward_on_off` | `true` | Same as above. |
| `event` | `event_actions` | empty (= any) | Restrict which event action values trigger a toggle (e.g. only `single_press`). Leave empty to toggle on any state change. |

## How it behaves

- **On/off** — for `switch`/`input_boolean` sources the pseudo light mirrors the source (optionally inverted). For `button`/`event` sources the pseudo light holds its own state and toggles on each press / matching event.
- **Brightness / color / color-temp / effect** — read from the underlying `light` when it is on, mirrored to the pseudo light.
- **Supported features** — mirrored from the underlying `light` at startup; updated whenever the light changes.
- **Availability** — pseudo light is available iff both the source and the underlying light are available.
- **State updates** — driven by `state_changed` listeners on both the source and the light.

## Development

```bash
# lint
ruff check custom_components/pseudo_light_switch

# syntax check
python3 -m py_compile custom_components/pseudo_light_switch/*.py
```

## License

MIT — see [LICENSE](LICENSE).
