# Pseudo Light Switch

Expose a single virtual **Light** entity backed by an on/off source plus a real light that owns brightness, color, and color temperature.

- On/off follows the source; brightness / color / color-temp / effect follow the real light.
- Sources supported: `switch.*`, `input_boolean.*` (stateful — follows, optional invert), `button.*` / `input_button.*` (each press toggles), `event.*` (each state change toggles, optional action filter).
- `forward_on_off` — also propagate the pseudo light's on/off to the real light (useful for keeping a smart bulb in sync with a smart button or a detached relay).

Install from HACS as a **Custom Repository**, then add one config entry per (source, light) pair.
