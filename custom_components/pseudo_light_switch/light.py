"""Light platform for Pseudo Light Switch."""

from __future__ import annotations

import contextlib
from typing import Any

from homeassistant.components.light import (
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import Event, HomeAssistant, State, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import (
    EventStateChangedData,
    async_track_state_change_event,
)

from .config_flow import default_forward_on_off, source_type_for
from .const import (
    CONF_EVENT_ACTIONS,
    CONF_FORWARD_ON_OFF,
    CONF_INVERT_STATE,
    CONF_LIGHT_ENTITY,
    CONF_NAME,
    CONF_ON_OFF_SOURCE,
    DEFAULT_INVERT_STATE,
    SOURCE_TYPE_BUTTON,
    SOURCE_TYPE_EVENT,
    SOURCE_TYPE_SWITCH,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Pseudo Light Switch light from a config entry."""
    source_entity_id: str = entry.data[CONF_ON_OFF_SOURCE]
    light_entity_id: str = entry.data[CONF_LIGHT_ENTITY]
    name: str = entry.data.get(CONF_NAME, "Pseudo Light")
    invert_state: bool = entry.options.get(CONF_INVERT_STATE, DEFAULT_INVERT_STATE)
    forward_on_off: bool = entry.options.get(
        CONF_FORWARD_ON_OFF, default_forward_on_off(source_type_for(source_entity_id))
    )
    event_actions: list[str] = list(entry.options.get(CONF_EVENT_ACTIONS, []))

    entity = PseudoLightSwitch(
        hass=hass,
        name=name,
        source_entity_id=source_entity_id,
        light_entity_id=light_entity_id,
        source_type=source_type_for(source_entity_id),
        invert_state=invert_state,
        forward_on_off=forward_on_off,
        event_actions=event_actions,
        entry_id=entry.entry_id,
    )
    async_add_entities([entity])


class PseudoLightSwitch(LightEntity):
    """Virtual light backed by an on/off source and a real light."""

    _attr_should_poll = False
    _attr_icon = "mdi:light-switch"

    def __init__(
        self,
        hass: HomeAssistant,
        name: str,
        source_entity_id: str,
        light_entity_id: str,
        source_type: str,
        invert_state: bool,
        forward_on_off: bool,
        event_actions: list[str],
        entry_id: str,
    ) -> None:
        self.hass = hass
        self._source_entity_id = source_entity_id
        self._light_entity_id = light_entity_id
        self._source_type = source_type
        self._invert_state = invert_state
        self._forward_on_off = forward_on_off
        self._event_actions = event_actions
        self._attr_name = name
        self._attr_unique_id = f"{entry_id}_pseudo_light"

        # internal state for button/event sources (no source-side state to mirror)
        self._internal_state: bool = False

        # mirrored from the underlying light
        self._attr_brightness: int | None = None
        self._attr_color_mode: ColorMode | None = None
        self._attr_color_temp_kelvin: int | None = None
        self._attr_hs_color: tuple[float, float] | None = None
        self._attr_rgb_color: tuple[int, int, int] | None = None
        self._attr_rgbw_color: tuple[int, int, int, int] | None = None
        self._attr_rgbww_color: tuple[int, int, int, int, int] | None = None
        self._attr_white: int | None = None
        self._attr_effect: str | None = None
        self._attr_effect_list: list[str] | None = None
        self._attr_supported_color_modes: set[ColorMode] | None = None
        self._attr_supported_features: LightEntityFeature = LightEntityFeature(0)

    # ----- live state properties ------------------------------------------------

    @property
    def is_on(self) -> bool | None:
        if self._source_type == SOURCE_TYPE_SWITCH:
            state = self.hass.states.get(self._source_entity_id)
            if state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
                return None
            on = state.state == STATE_ON
            return (not on) if self._invert_state else on
        return self._internal_state

    @property
    def available(self) -> bool:
        source = self.hass.states.get(self._source_entity_id)
        light = self.hass.states.get(self._light_entity_id)
        if source is None or source.state == STATE_UNAVAILABLE:
            return False
        return not (light is None or light.state == STATE_UNAVAILABLE)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "source_entity_id": self._source_entity_id,
            "light_entity_id": self._light_entity_id,
            "source_type": self._source_type,
            "invert_state": self._invert_state,
            "forward_on_off": self._forward_on_off,
            "event_actions": list(self._event_actions),
        }

    # ----- lifecycle -----------------------------------------------------------

    async def async_added_to_hass(self) -> None:
        """Register state listener and seed initial values from the light."""
        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                [self._source_entity_id, self._light_entity_id],
                self._handle_state_change,
            )
        )
        self._refresh_light_attrs(self.hass.states.get(self._light_entity_id))
        self.async_write_ha_state()

    # ----- listener ------------------------------------------------------------

    @callback
    def _handle_state_change(self, event: Event[EventStateChangedData]) -> None:
        entity_id = event.data["entity_id"]
        new_state: State | None = event.data["new_state"]
        old_state: State | None = event.data["old_state"]
        if entity_id == self._source_entity_id:
            self._handle_source_change(new_state, old_state)
        elif entity_id == self._light_entity_id:
            self._refresh_light_attrs(new_state)
        self.async_write_ha_state()

    @callback
    def _handle_source_change(self, new_state: State | None, old_state: State | None) -> None:
        if (self._source_type == SOURCE_TYPE_BUTTON and self._is_press_event(new_state, old_state)) or (
            self._source_type == SOURCE_TYPE_EVENT and self._is_event_trigger(new_state, old_state)
        ):
            self._internal_state = not self._internal_state
        # SOURCE_TYPE_SWITCH: state is computed live by the is_on property;
        # the listener still triggers a write so HA pushes updates promptly.

    @staticmethod
    @callback
    def _is_press_event(new_state: State | None, old_state: State | None) -> bool:
        if new_state is None or new_state.state == STATE_UNAVAILABLE:
            return False
        if old_state is None:
            return False
        if new_state.state != old_state.state:
            return True
        # input_button doesn't change `state` on press, but updates
        # the `last_pressed` attribute.
        new_lp = new_state.attributes.get("last_pressed")
        old_lp = old_state.attributes.get("last_pressed")
        return bool(new_lp) and new_lp != old_lp

    @callback
    def _is_event_trigger(self, new_state: State | None, old_state: State | None) -> bool:
        if new_state is None or old_state is None:
            return False
        if new_state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN, ""):
            return False
        if new_state.state == old_state.state:
            return False
        return not (self._event_actions and new_state.state not in self._event_actions)

    def _refresh_light_attrs(self, light_state: State | None) -> None:
        if light_state is None or light_state.state == STATE_UNAVAILABLE:
            return
        attrs = light_state.attributes

        supported = attrs.get("supported_color_modes")
        if isinstance(supported, list):
            parsed: set[ColorMode] = set()
            for raw in supported:
                try:
                    parsed.add(ColorMode(str(raw)))
                except ValueError:
                    continue
            if parsed:
                self._attr_supported_color_modes = parsed

        cm_raw = attrs.get("color_mode")
        if cm_raw is not None:
            with contextlib.suppress(ValueError):
                self._attr_color_mode = ColorMode(str(cm_raw))

        if light_state.state == STATE_ON:
            self._attr_brightness = attrs.get("brightness")
            self._attr_hs_color = _as_tuple(attrs.get("hs_color"), 2)
            self._attr_rgb_color = _as_tuple(attrs.get("rgb_color"), 3)
            self._attr_rgbw_color = _as_tuple(attrs.get("rgbw_color"), 4)
            self._attr_rgbww_color = _as_tuple(attrs.get("rgbww_color"), 5)
            self._attr_white = attrs.get("white")
            self._attr_effect = attrs.get("effect")

            kelvin = attrs.get("color_temp_kelvin")
            if isinstance(kelvin, (int, float)):
                self._attr_color_temp_kelvin = int(kelvin)
            else:
                mireds = attrs.get("color_temp")
                if isinstance(mireds, (int, float)) and mireds:
                    self._attr_color_temp_kelvin = round(1_000_000 / mireds)
        else:
            self._attr_brightness = None
            self._attr_hs_color = None
            self._attr_rgb_color = None
            self._attr_rgbw_color = None
            self._attr_rgbww_color = None
            self._attr_white = None
            self._attr_color_temp_kelvin = None
            self._attr_effect = None

        self._attr_effect_list = attrs.get("effect_list")
        feats = attrs.get("supported_features", 0)
        with contextlib.suppress(TypeError, ValueError):
            self._attr_supported_features = LightEntityFeature(int(feats))

    # ----- service handlers ----------------------------------------------------

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the pseudo light on."""
        if self._source_type == SOURCE_TYPE_SWITCH:
            if not self.is_on:
                await self.hass.services.async_call(
                    "switch",
                    "turn_on",
                    {"entity_id": self._source_entity_id},
                    blocking=True,
                )
        else:
            self._internal_state = True

        if kwargs:
            await self.hass.services.async_call(
                "light",
                "turn_on",
                {"entity_id": self._light_entity_id, **kwargs},
                blocking=True,
            )
        elif self._forward_on_off:
            light_state = self.hass.states.get(self._light_entity_id)
            if light_state is not None and light_state.state != STATE_ON:
                await self.hass.services.async_call(
                    "light",
                    "turn_on",
                    {"entity_id": self._light_entity_id},
                    blocking=True,
                )

        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the pseudo light off."""
        if self._forward_on_off:
            light_state = self.hass.states.get(self._light_entity_id)
            if light_state is not None and light_state.state != STATE_OFF:
                await self.hass.services.async_call(
                    "light",
                    "turn_off",
                    {"entity_id": self._light_entity_id},
                    blocking=True,
                )

        if self._source_type == SOURCE_TYPE_SWITCH:
            if self.is_on:
                await self.hass.services.async_call(
                    "switch",
                    "turn_off",
                    {"entity_id": self._source_entity_id},
                    blocking=True,
                )
        else:
            self._internal_state = False

        self.async_write_ha_state()


def _as_tuple(value: Any, length: int) -> tuple | None:
    """Coerce a list/tuple of the given length into a tuple, else None."""
    if isinstance(value, (list, tuple)) and len(value) == length:
        return tuple(value)
    return None
