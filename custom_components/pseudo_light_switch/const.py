"""Constants for the Pseudo Light Switch integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "pseudo_light_switch"

# Config-entry keys
CONF_ON_OFF_SOURCE: Final = "on_off_source"
CONF_LIGHT_ENTITY: Final = "light_entity"
CONF_NAME: Final = "name"
CONF_INVERT_STATE: Final = "invert_state"
CONF_FORWARD_ON_OFF: Final = "forward_on_off"
CONF_EVENT_ACTIONS: Final = "event_actions"

# Defaults
DEFAULT_NAME: Final = "Pseudo Light"
DEFAULT_INVERT_STATE: Final = False
DEFAULT_FORWARD_ON_OFF: Final = False
DEFAULT_EVENT_ACTIONS: Final[list[str]] = []

# Source-type identifiers (derived from the source entity's domain)
SOURCE_TYPE_SWITCH: Final = "switch"
SOURCE_TYPE_BUTTON: Final = "button"
SOURCE_TYPE_EVENT: Final = "event"

# Domains the source picker accepts
SOURCE_DOMAINS: Final[list[str]] = ["switch", "button", "input_button", "event"]
