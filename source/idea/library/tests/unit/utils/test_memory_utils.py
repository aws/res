#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import pytest
from res.utils import memory_utils


class TestMemoryUtils:
    """Test class for memory_utils module."""

    def test_convert_to_mib_with_none(self):
        """Test convert_to_mib with None input."""
        result = memory_utils.convert_to_mib(None, "GiB")
        assert result == 0.0

    def test_convert_to_mib_with_none_value(self):
        """Test convert_to_mib with None value."""
        result = memory_utils.convert_to_mib(None, "GiB")
        assert result == 0.0

    def test_convert_to_mib_mib_unit(self):
        """Test convert_to_mib with MiB unit."""
        result = memory_utils.convert_to_mib(1024.0, "MiB")
        assert result == 1024.0

    def test_convert_to_mib_mib_unit_lowercase(self):
        """Test convert_to_mib with lowercase mib unit."""
        result = memory_utils.convert_to_mib(1024.0, "mib")
        assert result == 1024.0

    def test_convert_to_mib_gib_unit(self):
        """Test convert_to_mib with GiB unit."""
        result = memory_utils.convert_to_mib(2.0, "GiB")
        assert result == 2048.0  # 2 * 1024

    def test_convert_to_mib_gb_unit(self):
        """Test convert_to_mib with GB unit."""
        result = memory_utils.convert_to_mib(4.0, "GB")
        assert result == 4096.0  # 4 * 1024

    def test_convert_to_mib_tib_unit(self):
        """Test convert_to_mib with TiB unit."""
        result = memory_utils.convert_to_mib(1.0, "TiB")
        assert result == 1048576.0  # 1 * 1024 * 1024

    def test_convert_to_mib_tb_unit(self):
        """Test convert_to_mib with TB unit."""
        result = memory_utils.convert_to_mib(1.0, "TB")
        assert result == 1048576.0  # 1 * 1024 * 1024

    def test_convert_to_mib_kib_unit(self):
        """Test convert_to_mib with KiB unit."""
        result = memory_utils.convert_to_mib(2048.0, "KiB")
        assert result == 2.0  # 2048 / 1024

    def test_convert_to_mib_kb_unit(self):
        """Test convert_to_mib with KB unit."""
        result = memory_utils.convert_to_mib(1024.0, "KB")
        assert result == 1.0  # 1024 / 1024

    def test_convert_to_mib_bytes_unit(self):
        """Test convert_to_mib with bytes unit."""
        result = memory_utils.convert_to_mib(2097152.0, "bytes")  # 2 MiB in bytes
        assert result == 2.0  # 2097152 / (1024 * 1024)

    def test_convert_to_mib_b_unit(self):
        """Test convert_to_mib with B unit."""
        result = memory_utils.convert_to_mib(1048576.0, "B")  # 1 MiB in bytes
        assert result == 1.0  # 1048576 / (1024 * 1024)

    def test_convert_to_mib_unknown_unit(self):
        """Test convert_to_mib with unknown unit defaults to MiB."""
        result = memory_utils.convert_to_mib(512.0, "unknown")
        assert result == 512.0  # Default to MiB

    def test_convert_to_mib_empty_unit(self):
        """Test convert_to_mib with empty unit defaults to MiB."""
        result = memory_utils.convert_to_mib(256.0, "")
        assert result == 256.0  # Default to MiB

    def test_convert_to_mib_none_unit(self):
        """Test convert_to_mib with None unit defaults to MiB."""
        result = memory_utils.convert_to_mib(128.0, None)
        assert result == 128.0  # Default to MiB

    def test_compare_memory_both_none(self):
        """Test compare_memory with both None inputs."""
        result = memory_utils.compare_memory(None, None, None, None)
        assert result == 0

    def test_compare_memory_first_none(self):
        """Test compare_memory with first input None."""
        result = memory_utils.compare_memory(None, None, 1.0, "GiB")
        assert result == -1

    def test_compare_memory_second_none(self):
        """Test compare_memory with second input None."""
        result = memory_utils.compare_memory(1.0, "GiB", None, None)
        assert result == 1

    def test_compare_memory_equal(self):
        """Test compare_memory with equal memory values."""
        result = memory_utils.compare_memory(2.0, "GiB", 2048.0, "MiB")  # Same as 2 GiB
        assert result == 0

    def test_compare_memory_first_greater(self):
        """Test compare_memory with first memory greater."""
        result = memory_utils.compare_memory(4.0, "GiB", 2048.0, "MiB")  # 2 GiB
        assert result == 1

    def test_compare_memory_first_smaller(self):
        """Test compare_memory with first memory smaller."""
        result = memory_utils.compare_memory(1.0, "GiB", 2048.0, "MiB")  # 2 GiB
        assert result == -1

    def test_is_greater_than_true(self):
        """Test is_greater_than returns True when first is greater."""
        result = memory_utils.is_greater_than(8.0, "GiB", 4096.0, "MiB")  # 4 GiB
        assert result is True

    def test_is_greater_than_false(self):
        """Test is_greater_than returns False when first is smaller."""
        result = memory_utils.is_greater_than(2.0, "GiB", 4096.0, "MiB")  # 4 GiB
        assert result is False

    def test_is_greater_than_equal(self):
        """Test is_greater_than returns False when equal."""
        result = memory_utils.is_greater_than(4.0, "GiB", 4096.0, "MiB")  # 4 GiB
        assert result is False

    def test_is_greater_than_none_first(self):
        """Test is_greater_than returns False when first is None."""
        result = memory_utils.is_greater_than(None, None, 4.0, "GiB")
        assert result is False

    def test_is_greater_than_none_second(self):
        """Test is_greater_than returns True when second is None."""
        result = memory_utils.is_greater_than(4.0, "GiB", None, None)
        assert result is True

    def test_is_less_than_true(self):
        """Test is_less_than returns True when first is smaller."""
        result = memory_utils.is_less_than(2.0, "GiB", 4096.0, "MiB")  # 4 GiB
        assert result is True

    def test_is_less_than_false(self):
        """Test is_less_than returns False when first is greater."""
        result = memory_utils.is_less_than(8.0, "GiB", 4096.0, "MiB")  # 4 GiB
        assert result is False

    def test_is_less_than_equal(self):
        """Test is_less_than returns False when equal."""
        result = memory_utils.is_less_than(4.0, "GiB", 4096.0, "MiB")  # 4 GiB
        assert result is False

    def test_is_equal_true(self):
        """Test is_equal returns True when memories are equal."""
        result = memory_utils.is_equal(4.0, "GiB", 4096.0, "MiB")  # 4 GiB
        assert result is True

    def test_is_equal_false(self):
        """Test is_equal returns False when memories are different."""
        result = memory_utils.is_equal(2.0, "GiB", 4096.0, "MiB")  # 4 GiB
        assert result is False

    def test_is_equal_both_none(self):
        """Test is_equal returns True when both are None."""
        result = memory_utils.is_equal(None, None, None, None)
        assert result is True

    def test_is_greater_than_or_equal_greater(self):
        """Test is_greater_than_or_equal returns True when first is greater."""
        result = memory_utils.is_greater_than_or_equal(
            8.0, "GiB", 4096.0, "MiB"
        )  # 4 GiB
        assert result is True

    def test_is_greater_than_or_equal_equal(self):
        """Test is_greater_than_or_equal returns True when equal."""
        result = memory_utils.is_greater_than_or_equal(
            4.0, "GiB", 4096.0, "MiB"
        )  # 4 GiB
        assert result is True

    def test_is_greater_than_or_equal_smaller(self):
        """Test is_greater_than_or_equal returns False when first is smaller."""
        result = memory_utils.is_greater_than_or_equal(
            2.0, "GiB", 4096.0, "MiB"
        )  # 4 GiB
        assert result is False

    def test_is_less_than_or_equal_smaller(self):
        """Test is_less_than_or_equal returns True when first is smaller."""
        result = memory_utils.is_less_than_or_equal(2.0, "GiB", 4096.0, "MiB")  # 4 GiB
        assert result is True

    def test_is_less_than_or_equal_equal(self):
        """Test is_less_than_or_equal returns True when equal."""
        result = memory_utils.is_less_than_or_equal(4.0, "GiB", 4096.0, "MiB")  # 4 GiB
        assert result is True

    def test_is_less_than_or_equal_greater(self):
        """Test is_less_than_or_equal returns False when first is greater."""
        result = memory_utils.is_less_than_or_equal(8.0, "GiB", 4096.0, "MiB")  # 4 GiB
        assert result is False

    def test_real_world_scenario_software_stack_validation(self):
        """Test real-world scenario: software stack RAM requirement validation."""
        # Software stack requires 8 GiB RAM
        software_stack_min_ram_value = 8.0
        software_stack_min_ram_unit = "GiB"

        # Instance has 4 GiB RAM
        instance_ram_value = 4096.0
        instance_ram_unit = "MiB"

        # Should return True (software stack requires more than instance provides)
        requires_more = memory_utils.is_greater_than(
            software_stack_min_ram_value,
            software_stack_min_ram_unit,
            instance_ram_value,
            instance_ram_unit,
        )
        assert requires_more is True

        # Instance with enough RAM
        large_instance_ram_value = 16.0
        large_instance_ram_unit = "GiB"

        # Should return False (software stack requirement is met)
        requires_more = memory_utils.is_greater_than(
            software_stack_min_ram_value,
            software_stack_min_ram_unit,
            large_instance_ram_value,
            large_instance_ram_unit,
        )
        assert requires_more is False

    def test_edge_case_zero_values(self):
        """Test edge case with zero memory values."""
        assert memory_utils.is_equal(0.0, "GiB", 0.0, "MiB") is True
        assert memory_utils.is_greater_than(0.0, "GiB", 0.0, "MiB") is False
        assert memory_utils.is_less_than(0.0, "GiB", 0.0, "MiB") is False

    def test_edge_case_very_large_values(self):
        """Test edge case with very large memory values."""
        assert memory_utils.is_greater_than(1024.0, "TiB", 1.0, "GiB") is True
        assert memory_utils.is_less_than(1.0, "GiB", 1024.0, "TiB") is True

    def test_edge_case_fractional_values(self):
        """Test edge case with fractional memory values."""
        assert memory_utils.is_equal(0.5, "GiB", 512.0, "MiB") is True
        assert memory_utils.convert_to_mib(0.5, "GiB") == 512.0
        assert memory_utils.convert_to_mib(512.0, "MiB") == 512.0
