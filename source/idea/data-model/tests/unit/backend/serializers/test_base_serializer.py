#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from types import ModuleType
from unittest.mock import patch, MagicMock
from enum import Enum
import importlib
import pytest

from datamodel.serializers.base_serializer import BaseSerializer


class _FakeEnum(str, Enum):
    VALUE_A = "value_a"


def _make_fake_model(name="FakeModel"):
    """Create a stub model type with from_ddb_dict to trigger serializer lookup."""
    cls = type(name, (), {
        "from_ddb_dict": staticmethod(lambda data: data),
    })
    return cls


FakeModel = _make_fake_model("FakeModel")


class TestConvertDdbValueToType:
    """Tests for BaseSerializer._convert_ddb_value_to_type singleton resolution."""

    def setup_method(self):
        self.serializer = BaseSerializer()

    def test_resolves_singleton_with_lowercased_class_name(self):
        """Singleton name must be lowercased class name, not snake_case module name.

        Generated serializers create singletons like:
            fakemodel_serializer = FakeModelSerializer()
        The lookup must use 'fakemodel_serializer', NOT 'fake_model_serializer'.
        """
        mock_inner_serializer = MagicMock()
        mock_inner_serializer.from_ddb_dict.return_value = {"converted": True}

        fake_module = ModuleType("datamodel.serializers.fake_model_serializer")
        fake_module.fakemodel_serializer = mock_inner_serializer

        with patch.object(importlib, "import_module", return_value=fake_module) as mock_import:
            result = self.serializer._convert_ddb_value_to_type(
                {"raw": "data"}, FakeModel
            )

        mock_import.assert_called_once_with(
            "datamodel.serializers.fake_model_serializer"
        )
        mock_inner_serializer.from_ddb_dict.assert_called_once_with({"raw": "data"})
        assert result == {"converted": True}


    def test_import_error_fallback_returns_raw_dict(self):
        """When the serializer module doesn't exist, return the raw dict."""
        with patch.object(
            importlib, "import_module", side_effect=ImportError("no module")
        ):
            result = self.serializer._convert_ddb_value_to_type(
                {"raw": "data"}, FakeModel
            )

        assert result == {"raw": "data"}

    def test_attribute_error_fallback_returns_raw_dict(self):
        """When the singleton attribute is missing, return the raw dict."""
        empty_module = ModuleType("datamodel.serializers.fake_model_serializer")

        with patch.object(importlib, "import_module", return_value=empty_module):
            result = self.serializer._convert_ddb_value_to_type(
                {"raw": "data"}, FakeModel
            )

        assert result == {"raw": "data"}

    def test_enum_conversion(self):
        """Enum string values are converted back to enum instances."""
        result = self.serializer._convert_ddb_value_to_type("value_a", _FakeEnum)
        assert result == _FakeEnum.VALUE_A
        assert isinstance(result, _FakeEnum)

    def test_none_value_returns_none(self):
        result = self.serializer._convert_ddb_value_to_type(None, FakeModel)
        assert result is None

    def test_primitive_value_returned_as_is(self):
        result = self.serializer._convert_ddb_value_to_type("hello", str)
        assert result == "hello"

    def test_fallback_logs_debug_message(self):
        """Verify the debug log fires on ImportError fallback."""
        import datamodel.serializers.base_serializer as base_mod

        with patch.object(
            importlib, "import_module", side_effect=ImportError("no module")
        ), patch.object(base_mod, "logger") as mock_logger:
            self.serializer._convert_ddb_value_to_type({"x": 1}, FakeModel)

        mock_logger.debug.assert_called_once()
        assert "FakeModel" in mock_logger.debug.call_args[0][0]
