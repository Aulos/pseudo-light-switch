"""Config flow for Pseudo Light Switch."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_EVENT_ACTIONS,
    CONF_FORWARD_ON_OFF,
    CONF_INVERT_STATE,
    CONF_LIGHT_ENTITY,
    CONF_NAME,
    CONF_ON_OFF_SOURCE,
    DEFAULT_EVENT_ACTIONS,
    DEFAULT_FORWARD_ON_OFF,
    DEFAULT_INVERT_STATE,
    DEFAULT_NAME,
    DOMAIN,
    SOURCE_DOMAINS,
    SOURCE_TYPE_BUTTON,
    SOURCE_TYPE_EVENT,
    SOURCE_TYPE_SWITCH,
)


def source_type_for(entity_id: str) -> str:
    """Derive the source type from the source entity_id's domain."""
    domain = entity_id.split(".", 1)[0]
    if domain in ("switch", "input_boolean"):
        return SOURCE_TYPE_SWITCH
    if domain in ("button", "input_button"):
        return SOURCE_TYPE_BUTTON
    if domain == "event":
        return SOURCE_TYPE_EVENT
    return SOURCE_TYPE_SWITCH


def default_forward_on_off(source_type: str) -> bool:
    """Return the default ``forward_on_off`` for a given source type."""
    return (source_type in (SOURCE_TYPE_BUTTON, SOURCE_TYPE_EVENT)) or DEFAULT_FORWARD_ON_OFF


def _user_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Optional(CONF_NAME, default=defaults.get(CONF_NAME, DEFAULT_NAME)): str,
            vol.Required(
                CONF_ON_OFF_SOURCE,
                default=defaults.get(CONF_ON_OFF_SOURCE),
            ): selector.EntitySelector(selector.EntitySelectorConfig(domain=SOURCE_DOMAINS)),
            vol.Required(
                CONF_LIGHT_ENTITY,
                default=defaults.get(CONF_LIGHT_ENTITY),
            ): selector.EntitySelector(selector.EntitySelectorConfig(domain="light", multiple=False)),
        }
    )


def _options_schema(
    source_type: str,
    event_options: list[str] | None = None,
    defaults: Mapping[str, Any] | None = None,
) -> vol.Schema:
    defaults = defaults or {}
    event_options = event_options or []
    schema: dict[Any, Any] = {}

    if source_type == SOURCE_TYPE_SWITCH:
        schema[
            vol.Optional(
                CONF_INVERT_STATE,
                default=defaults.get(CONF_INVERT_STATE, DEFAULT_INVERT_STATE),
            )
        ] = bool

    schema[
        vol.Optional(
            CONF_FORWARD_ON_OFF,
            default=defaults.get(CONF_FORWARD_ON_OFF, default_forward_on_off(source_type)),
        )
    ] = bool

    if source_type == SOURCE_TYPE_EVENT:
        schema[
            vol.Optional(
                CONF_EVENT_ACTIONS,
                default=defaults.get(CONF_EVENT_ACTIONS, list(DEFAULT_EVENT_ACTIONS)),
            )
        ] = selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[{"value": o, "label": o} for o in event_options],
                multiple=True,
                custom_value=True,
                mode=selector.SelectSelectorMode.DROPDOWN,
            )
        )

    return vol.Schema(schema)


def _event_options_for(hass, source_entity_id: str) -> list[str]:
    state = hass.states.get(source_entity_id)
    if state is None:
        return []
    raw = state.attributes.get("options", [])
    if not isinstance(raw, list):
        return []
    return [str(o) for o in raw]


class PseudoLightSwitchConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Pseudo Light Switch."""

    VERSION = 1

    def __init__(self) -> None:
        self._source: str | None = None
        self._light: str | None = None
        self._name: str = DEFAULT_NAME

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            self._source = user_input[CONF_ON_OFF_SOURCE]
            self._light = user_input[CONF_LIGHT_ENTITY]
            self._name = user_input.get(CONF_NAME, DEFAULT_NAME)
            await self.async_set_unique_id(f"{self._source}_{self._light}".lower())
            self._abort_if_unique_id_configured()
            return await self.async_step_options()
        return self.async_show_form(step_id="user", data_schema=_user_schema())

    async def async_step_options(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        assert self._source is not None
        source_type = source_type_for(self._source)
        event_options = _event_options_for(self.hass, self._source) if source_type == SOURCE_TYPE_EVENT else []
        if user_input is not None:
            return self.async_create_entry(
                title=self._name,
                data={
                    CONF_NAME: self._name,
                    CONF_ON_OFF_SOURCE: self._source,
                    CONF_LIGHT_ENTITY: self._light,
                },
                options=user_input,
            )
        return self.async_show_form(
            step_id="options",
            data_schema=_options_schema(source_type, event_options),
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> OptionsFlow:
        return PseudoLightSwitchOptionsFlow(config_entry)


class PseudoLightSwitchOptionsFlow(OptionsFlow):
    """Handle the options flow for Pseudo Light Switch."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        source = self._config_entry.data[CONF_ON_OFF_SOURCE]
        source_type = source_type_for(source)
        event_options = _event_options_for(self.hass, source) if source_type == SOURCE_TYPE_EVENT else []
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        return self.async_show_form(
            step_id="init",
            data_schema=_options_schema(
                source_type,
                event_options,
                defaults=self._config_entry.options,
            ),
        )
