"""Tests for translation files."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture
def strings_path() -> Path:
    """Return the path to strings.json."""
    return Path(__file__).parent.parent / "custom_components" / "zowietek" / "strings.json"


@pytest.fixture
def translations_path() -> Path:
    """Return the path to translations/en.json."""
    return (
        Path(__file__).parent.parent / "custom_components" / "zowietek" / "translations" / "en.json"
    )


@pytest.fixture
def strings_data(strings_path: Path) -> dict[str, object]:
    """Load and return strings.json data."""
    with strings_path.open(encoding="utf-8") as f:
        data: dict[str, object] = json.load(f)
    return data


@pytest.fixture
def translations_data(translations_path: Path) -> dict[str, object]:
    """Load and return translations/en.json data."""
    with translations_path.open(encoding="utf-8") as f:
        data: dict[str, object] = json.load(f)
    return data


class TestStringsJsonExists:
    """Test that strings.json exists and is valid JSON."""

    def test_strings_json_exists(self, strings_path: Path) -> None:
        """Test that strings.json file exists."""
        assert strings_path.exists(), "strings.json must exist"

    def test_strings_json_is_valid_json(self, strings_path: Path) -> None:
        """Test that strings.json contains valid JSON."""
        with strings_path.open(encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, dict), "strings.json must be a JSON object"


class TestTranslationsEnJsonExists:
    """Test that translations/en.json exists and is valid JSON."""

    def test_translations_en_json_exists(self, translations_path: Path) -> None:
        """Test that translations/en.json file exists."""
        assert translations_path.exists(), "translations/en.json must exist"

    def test_translations_en_json_is_valid_json(self, translations_path: Path) -> None:
        """Test that translations/en.json contains valid JSON."""
        with translations_path.open(encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, dict), "translations/en.json must be a JSON object"


class TestTranslationsMatch:
    """Test that translations/en.json matches strings.json."""

    def test_translations_matches_strings(
        self,
        strings_data: dict[str, object],
        translations_data: dict[str, object],
    ) -> None:
        """Test that translations/en.json content matches strings.json."""
        assert strings_data == translations_data, (
            "translations/en.json must be an exact copy of strings.json"
        )


class TestConfigFlowStrings:
    """Test config flow translation strings."""

    def test_config_step_user_exists(self, strings_data: dict[str, object]) -> None:
        """Test that config.step.user section exists."""
        config = strings_data.get("config")
        assert isinstance(config, dict), "config section must exist"
        step = config.get("step")
        assert isinstance(step, dict), "config.step section must exist"
        user = step.get("user")
        assert isinstance(user, dict), "config.step.user section must exist"

    def test_config_step_user_has_title(self, strings_data: dict[str, object]) -> None:
        """Test that config.step.user has title."""
        config = strings_data.get("config")
        assert isinstance(config, dict)
        step = config.get("step")
        assert isinstance(step, dict)
        user = step.get("user")
        assert isinstance(user, dict)
        assert "title" in user, "config.step.user must have title"
        assert isinstance(user["title"], str), "title must be a string"

    def test_config_step_user_has_description(self, strings_data: dict[str, object]) -> None:
        """Test that config.step.user has description."""
        config = strings_data.get("config")
        assert isinstance(config, dict)
        step = config.get("step")
        assert isinstance(step, dict)
        user = step.get("user")
        assert isinstance(user, dict)
        assert "description" in user, "config.step.user must have description"
        assert isinstance(user["description"], str), "description must be a string"

    def test_config_step_user_has_data_fields(self, strings_data: dict[str, object]) -> None:
        """Test that config.step.user has required data fields."""
        config = strings_data.get("config")
        assert isinstance(config, dict)
        step = config.get("step")
        assert isinstance(step, dict)
        user = step.get("user")
        assert isinstance(user, dict)
        data = user.get("data")
        assert isinstance(data, dict), "config.step.user.data must exist"

        required_fields = ["host", "username", "password"]
        for field in required_fields:
            assert field in data, f"config.step.user.data must have {field}"
            assert isinstance(data[field], str), f"{field} must be a string"

    def test_config_step_user_has_data_descriptions(self, strings_data: dict[str, object]) -> None:
        """Test that config.step.user has data_description for host."""
        config = strings_data.get("config")
        assert isinstance(config, dict)
        step = config.get("step")
        assert isinstance(step, dict)
        user = step.get("user")
        assert isinstance(user, dict)
        data_desc = user.get("data_description")
        assert isinstance(data_desc, dict), "config.step.user.data_description must exist"
        assert "host" in data_desc, "data_description must have host"

    def test_config_errors_exist(self, strings_data: dict[str, object]) -> None:
        """Test that config.error section exists with required errors."""
        config = strings_data.get("config")
        assert isinstance(config, dict)
        error = config.get("error")
        assert isinstance(error, dict), "config.error section must exist"

        required_errors = ["cannot_connect", "invalid_auth", "unknown"]
        for err in required_errors:
            assert err in error, f"config.error must have {err}"
            assert isinstance(error[err], str), f"{err} must be a string"

    def test_config_abort_exists(self, strings_data: dict[str, object]) -> None:
        """Test that config.abort section exists with required abort reasons."""
        config = strings_data.get("config")
        assert isinstance(config, dict)
        abort = config.get("abort")
        assert isinstance(abort, dict), "config.abort section must exist"

        required_aborts = ["already_configured"]
        for ab in required_aborts:
            assert ab in abort, f"config.abort must have {ab}"
            assert isinstance(abort[ab], str), f"{ab} must be a string"


class TestSensorEntityStrings:
    """Test sensor entity translation strings."""

    def test_entity_sensor_section_exists(self, strings_data: dict[str, object]) -> None:
        """Test that entity.sensor section exists."""
        entity = strings_data.get("entity")
        assert isinstance(entity, dict), "entity section must exist"
        sensor = entity.get("sensor")
        assert isinstance(sensor, dict), "entity.sensor section must exist"

    def test_sensor_translation_keys_match_entity_descriptions(
        self, strings_data: dict[str, object]
    ) -> None:
        """Test that all sensor translation_keys have corresponding strings."""
        from custom_components.zowietek.sensor import SENSOR_DESCRIPTIONS

        entity = strings_data.get("entity")
        assert isinstance(entity, dict)
        sensor = entity.get("sensor")
        assert isinstance(sensor, dict)

        for desc in SENSOR_DESCRIPTIONS:
            key = desc.translation_key
            assert key is not None, f"Sensor {desc.key} must have translation_key"
            assert key in sensor, f"entity.sensor must have translation for {key}"
            sensor_entry = sensor[key]
            assert isinstance(sensor_entry, dict), f"sensor.{key} must be a dict"
            assert "name" in sensor_entry, f"sensor.{key} must have name"
            assert isinstance(sensor_entry["name"], str), f"sensor.{key}.name must be a string"


class TestBinarySensorEntityStrings:
    """Test binary_sensor entity translation strings."""

    def test_entity_binary_sensor_section_exists(self, strings_data: dict[str, object]) -> None:
        """Test that entity.binary_sensor section exists."""
        entity = strings_data.get("entity")
        assert isinstance(entity, dict), "entity section must exist"
        binary_sensor = entity.get("binary_sensor")
        assert isinstance(binary_sensor, dict), "entity.binary_sensor section must exist"

    def test_binary_sensor_translation_keys_match_entity_descriptions(
        self, strings_data: dict[str, object]
    ) -> None:
        """Test that all binary_sensor translation_keys have corresponding strings."""
        from custom_components.zowietek.binary_sensor import BINARY_SENSOR_DESCRIPTIONS

        entity = strings_data.get("entity")
        assert isinstance(entity, dict)
        binary_sensor = entity.get("binary_sensor")
        assert isinstance(binary_sensor, dict)

        for desc in BINARY_SENSOR_DESCRIPTIONS:
            key = desc.translation_key
            assert key is not None, f"Binary sensor {desc.key} must have translation_key"
            assert key in binary_sensor, f"entity.binary_sensor must have translation for {key}"
            entry = binary_sensor[key]
            assert isinstance(entry, dict), f"binary_sensor.{key} must be a dict"
            assert "name" in entry, f"binary_sensor.{key} must have name"
            assert isinstance(entry["name"], str), f"binary_sensor.{key}.name must be a string"


class TestSwitchEntityStrings:
    """Test switch entity translation strings."""

    def test_entity_switch_section_exists(self, strings_data: dict[str, object]) -> None:
        """Test that entity.switch section exists."""
        entity = strings_data.get("entity")
        assert isinstance(entity, dict), "entity section must exist"
        switch = entity.get("switch")
        assert isinstance(switch, dict), "entity.switch section must exist"

    def test_switch_translation_keys_match_entity_descriptions(
        self, strings_data: dict[str, object]
    ) -> None:
        """Test that all switch translation_keys have corresponding strings."""
        from custom_components.zowietek.switch import SWITCH_DESCRIPTIONS

        entity = strings_data.get("entity")
        assert isinstance(entity, dict)
        switch = entity.get("switch")
        assert isinstance(switch, dict)

        for desc in SWITCH_DESCRIPTIONS:
            key = desc.translation_key
            assert key is not None, f"Switch {desc.key} must have translation_key"
            assert key in switch, f"entity.switch must have translation for {key}"
            entry = switch[key]
            assert isinstance(entry, dict), f"switch.{key} must be a dict"
            assert "name" in entry, f"switch.{key} must have name"
            assert isinstance(entry["name"], str), f"switch.{key}.name must be a string"


class TestButtonEntityStrings:
    """Test button entity translation strings.

    Button entities are defined in the issue but not yet implemented.
    These translations are included for future use.
    """

    def test_entity_button_section_exists(self, strings_data: dict[str, object]) -> None:
        """Test that entity.button section exists."""
        entity = strings_data.get("entity")
        assert isinstance(entity, dict), "entity section must exist"
        button = entity.get("button")
        assert isinstance(button, dict), "entity.button section must exist"

    def test_button_has_reboot(self, strings_data: dict[str, object]) -> None:
        """Test that button has reboot translation."""
        entity = strings_data.get("entity")
        assert isinstance(entity, dict)
        button = entity.get("button")
        assert isinstance(button, dict)
        assert "reboot" in button, "entity.button must have reboot"
        reboot = button["reboot"]
        assert isinstance(reboot, dict)
        assert "name" in reboot

    def test_button_has_refresh(self, strings_data: dict[str, object]) -> None:
        """Test that button has refresh translation."""
        entity = strings_data.get("entity")
        assert isinstance(entity, dict)
        button = entity.get("button")
        assert isinstance(button, dict)
        assert "refresh" in button, "entity.button must have refresh"
        refresh = button["refresh"]
        assert isinstance(refresh, dict)
        assert "name" in refresh


class TestSelectEntityStrings:
    """Test select entity translation strings.

    Select entities are defined in the issue but not yet implemented.
    These translations are included for future use.
    """

    def test_entity_select_section_exists(self, strings_data: dict[str, object]) -> None:
        """Test that entity.select section exists."""
        entity = strings_data.get("entity")
        assert isinstance(entity, dict), "entity section must exist"
        select = entity.get("select")
        assert isinstance(select, dict), "entity.select section must exist"

    def test_select_has_video_mode(self, strings_data: dict[str, object]) -> None:
        """Test that select has video_mode translation."""
        entity = strings_data.get("entity")
        assert isinstance(entity, dict)
        select = entity.get("select")
        assert isinstance(select, dict)
        assert "video_mode" in select, "entity.select must have video_mode"
        video_mode = select["video_mode"]
        assert isinstance(video_mode, dict)
        assert "name" in video_mode

    def test_select_has_resolution(self, strings_data: dict[str, object]) -> None:
        """Test that select has resolution translation."""
        entity = strings_data.get("entity")
        assert isinstance(entity, dict)
        select = entity.get("select")
        assert isinstance(select, dict)
        assert "resolution" in select, "entity.select must have resolution"
        resolution = select["resolution"]
        assert isinstance(resolution, dict)
        assert "name" in resolution

    def test_select_has_encoder_type(self, strings_data: dict[str, object]) -> None:
        """Test that select has encoder_type translation."""
        entity = strings_data.get("entity")
        assert isinstance(entity, dict)
        select = entity.get("select")
        assert isinstance(select, dict)
        assert "encoder_type" in select, "entity.select must have encoder_type"
        encoder_type = select["encoder_type"]
        assert isinstance(encoder_type, dict)
        assert "name" in encoder_type
