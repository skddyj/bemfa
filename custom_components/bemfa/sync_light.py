"""Support for bemfa service."""
from __future__ import annotations

from collections.abc import Mapping, Callable
from typing import Any
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_BRIGHTNESS_PCT,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_MIN_COLOR_TEMP_KELVIN,
    ATTR_MAX_COLOR_TEMP_KELVIN,
    ATTR_RGB_COLOR,
    ATTR_SUPPORTED_COLOR_MODES,
    DOMAIN,
    ColorMode,
)
from homeassistant.const import SERVICE_TURN_OFF, SERVICE_TURN_ON, STATE_ON
from homeassistant.util.read_only_dict import ReadOnlyDict
from .const import MSG_OFF, MSG_ON, TopicSuffix
from .utils import has_key
from .sync import SYNC_TYPES, ControllableSync


def _clamp(value: int, min_value: int, max_value: int) -> int:
    return min(max(value, min_value), max_value)


def _kelvin_to_mired(kelvin: int) -> int:
    return 1000000 // kelvin


def _mired_to_kelvin(mired: int) -> int:
    return 1000000 // mired


def _is_supported_color_temp_mired(
    value: int, attributes: ReadOnlyDict[Mapping[str, Any]]
) -> bool:
    if (
        value <= 0
        or not has_key(attributes, ATTR_MIN_COLOR_TEMP_KELVIN)
        or not has_key(attributes, ATTR_MAX_COLOR_TEMP_KELVIN)
    ):
        return False

    min_mired = _kelvin_to_mired(attributes[ATTR_MAX_COLOR_TEMP_KELVIN])
    max_mired = _kelvin_to_mired(attributes[ATTR_MIN_COLOR_TEMP_KELVIN])
    return min_mired <= value <= max_mired


def _light_color_msg(attributes: ReadOnlyDict[Mapping[str, Any]]) -> str | int:
    if has_key(attributes, ATTR_COLOR_TEMP_KELVIN):
        return _kelvin_to_mired(attributes[ATTR_COLOR_TEMP_KELVIN])
    if has_key(attributes, ATTR_RGB_COLOR):
        return (
            attributes[ATTR_RGB_COLOR][0] * 256 * 256
            + attributes[ATTR_RGB_COLOR][1] * 256
            + attributes[ATTR_RGB_COLOR][2]
        )
    return ""


def _resolve_light_msg(
    msg: list[str | int], attributes: ReadOnlyDict[Mapping[str, Any]]
) -> tuple[str, str, dict[str, Any]]:
    if len(msg) <= 1:
        return DOMAIN, SERVICE_TURN_ON if msg[0] == MSG_ON else SERVICE_TURN_OFF, {}

    data: dict[str, Any] = {ATTR_BRIGHTNESS_PCT: msg[1]}
    if len(msg) <= 2:
        return DOMAIN, SERVICE_TURN_ON if msg[0] == MSG_ON else SERVICE_TURN_OFF, data

    color_value = msg[2]
    supports_color_temp = (
        has_key(attributes, ATTR_SUPPORTED_COLOR_MODES)
        and ColorMode.COLOR_TEMP in attributes[ATTR_SUPPORTED_COLOR_MODES]
    )
    if (
        isinstance(color_value, int)
        and supports_color_temp
        and _is_supported_color_temp_mired(color_value, attributes)
    ):
        kelvin = _mired_to_kelvin(color_value)
        data[ATTR_COLOR_TEMP_KELVIN] = _clamp(
            kelvin,
            attributes[ATTR_MIN_COLOR_TEMP_KELVIN],
            attributes[ATTR_MAX_COLOR_TEMP_KELVIN],
        )
    elif isinstance(color_value, int):
        data[ATTR_RGB_COLOR] = [
            color_value // 256 // 256,
            color_value // 256 % 256,
            color_value % 256,
        ]

    return DOMAIN, SERVICE_TURN_ON if msg[0] == MSG_ON else SERVICE_TURN_OFF, data


@SYNC_TYPES.register("light")
class Light(ControllableSync):
    """Sync a hass light entity to bemfa light device."""

    @staticmethod
    def get_config_step_id() -> str:
        return "sync_config_light"

    @staticmethod
    def _get_topic_suffix() -> TopicSuffix:
        return TopicSuffix.LIGHT

    @staticmethod
    def _supported_domain() -> str:
        return DOMAIN

    def _msg_generators(
        self,
    ) -> list[Callable[[str, ReadOnlyDict[Mapping[str, Any]]], str | int]]:
        return [
            lambda state, attributes: MSG_ON if state == STATE_ON else MSG_OFF,
            lambda state, attributes: round(attributes[ATTR_BRIGHTNESS] / 2.55)
            if has_key(attributes, ATTR_BRIGHTNESS)
            else "",
            lambda state, attributes: _light_color_msg(attributes),
        ]

    def _msg_resolvers(
        self,
    ) -> list[
        (
            int,
            int,
            Callable[
                [list[str | int], ReadOnlyDict[Mapping[str, Any]]],
                (str, str, dict[str, Any]),
            ],
        )
    ]:
        return [
            (
                0,
                3,
                _resolve_light_msg,
            )
        ]
