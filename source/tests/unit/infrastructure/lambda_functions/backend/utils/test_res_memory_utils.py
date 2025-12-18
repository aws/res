#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
import sys
import pytest

# Add the backend directory to Python path to match utils import context
backend_path = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "../../../../../../idea/infrastructure/resources/lambda_functions/backend",
    )
)
sys.path.insert(0, backend_path)

from api.utils import res_memory_utils
from api.models.res_memory import ResMemory


class TestResMemoryUtils:
    """Test class for res_memory_utils module."""

    def test_convert_to_mib_with_none(self):
        """Test convert_to_mib with None input."""
        result = res_memory_utils.convert_to_mib(None)
        assert result == 0.0

    def test_convert_to_mib_with_none_value(self):
        """Test convert_to_mib with ResMemory having None value."""
        memory = ResMemory(value=None, unit="GiB")
        result = res_memory_utils.convert_to_mib(memory)
        assert result == 0.0

    def test_convert_to_mib_mib_unit(self):
        """Test convert_to_mib with MiB unit."""
        memory = ResMemory(value=1024.0, unit="MiB")
        result = res_memory_utils.convert_to_mib(memory)
        assert result == 1024.0

    def test_convert_to_mib_mib_unit_lowercase(self):
        """Test convert_to_mib with lowercase mib unit."""
        memory = ResMemory(value=1024.0, unit="mib")
        result = res_memory_utils.convert_to_mib(memory)
        assert result == 1024.0

    def test_convert_to_mib_gib_unit(self):
        """Test convert_to_mib with GiB unit."""
        memory = ResMemory(value=2.0, unit="GiB")
        result = res_memory_utils.convert_to_mib(memory)
        assert result == 2048.0  # 2 * 1024

    def test_convert_to_mib_gb_unit(self):
        """Test convert_to_mib with GB unit."""
        memory = ResMemory(value=4.0, unit="GB")
        result = res_memory_utils.convert_to_mib(memory)
        assert result == 4096.0  # 4 * 1024

    def test_convert_to_mib_tib_unit(self):
        """Test convert_to_mib with TiB unit."""
        memory = ResMemory(value=1.0, unit="TiB")
        result = res_memory_utils.convert_to_mib(memory)
        assert result == 1048576.0  # 1 * 1024 * 1024

    def test_convert_to_mib_tb_unit(self):
        """Test convert_to_mib with TB unit."""
        memory = ResMemory(value=1.0, unit="TB")
        result = res_memory_utils.convert_to_mib(memory)
        assert result == 1048576.0  # 1 * 1024 * 1024

    def test_convert_to_mib_kib_unit(self):
        """Test convert_to_mib with KiB unit."""
        memory = ResMemory(value=2048.0, unit="KiB")
        result = res_memory_utils.convert_to_mib(memory)
        assert result == 2.0  # 2048 / 1024

    def test_convert_to_mib_kb_unit(self):
        """Test convert_to_mib with KB unit."""
        memory = ResMemory(value=1024.0, unit="KB")
        result = res_memory_utils.convert_to_mib(memory)
        assert result == 1.0  # 1024 / 1024

    def test_convert_to_mib_bytes_unit(self):
        """Test convert_to_mib with bytes unit."""
        memory = ResMemory(value=2097152.0, unit="bytes")  # 2 MiB in bytes
        result = res_memory_utils.convert_to_mib(memory)
        assert result == 2.0  # 2097152 / (1024 * 1024)

    def test_convert_to_mib_b_unit(self):
        """Test convert_to_mib with B unit."""
        memory = ResMemory(value=1048576.0, unit="B")  # 1 MiB in bytes
        result = res_memory_utils.convert_to_mib(memory)
        assert result == 1.0  # 1048576 / (1024 * 1024)

    def test_convert_to_mib_unknown_unit(self):
        """Test convert_to_mib with unknown unit defaults to MiB."""
        memory = ResMemory(value=512.0, unit="unknown")
        result = res_memory_utils.convert_to_mib(memory)
        assert result == 512.0  # Default to MiB

    def test_convert_to_mib_empty_unit(self):
        """Test convert_to_mib with empty unit defaults to MiB."""
        memory = ResMemory(value=256.0, unit="")
        result = res_memory_utils.convert_to_mib(memory)
        assert result == 256.0  # Default to MiB

    def test_convert_to_mib_none_unit(self):
        """Test convert_to_mib with None unit defaults to MiB."""
        memory = ResMemory(value=128.0, unit=None)
        result = res_memory_utils.convert_to_mib(memory)
        assert result == 128.0  # Default to MiB

    def test_compare_memory_both_none(self):
        """Test compare_memory with both None inputs."""
        result = res_memory_utils.compare_memory(None, None)
        assert result == 0

    def test_compare_memory_first_none(self):
        """Test compare_memory with first input None."""
        memory2 = ResMemory(value=1.0, unit="GiB")
        result = res_memory_utils.compare_memory(None, memory2)
        assert result == -1

    def test_compare_memory_second_none(self):
        """Test compare_memory with second input None."""
        memory1 = ResMemory(value=1.0, unit="GiB")
        result = res_memory_utils.compare_memory(memory1, None)
        assert result == 1

    def test_compare_memory_equal(self):
        """Test compare_memory with equal memory values."""
        memory1 = ResMemory(value=2.0, unit="GiB")
        memory2 = ResMemory(value=2048.0, unit="MiB")  # Same as 2 GiB
        result = res_memory_utils.compare_memory(memory1, memory2)
        assert result == 0

    def test_compare_memory_first_greater(self):
        """Test compare_memory with first memory greater."""
        memory1 = ResMemory(value=4.0, unit="GiB")
        memory2 = ResMemory(value=2048.0, unit="MiB")  # 2 GiB
        result = res_memory_utils.compare_memory(memory1, memory2)
        assert result == 1

    def test_compare_memory_first_smaller(self):
        """Test compare_memory with first memory smaller."""
        memory1 = ResMemory(value=1.0, unit="GiB")
        memory2 = ResMemory(value=2048.0, unit="MiB")  # 2 GiB
        result = res_memory_utils.compare_memory(memory1, memory2)
        assert result == -1

    def test_is_greater_than_true(self):
        """Test is_greater_than returns True when first is greater."""
        memory1 = ResMemory(value=8.0, unit="GiB")
        memory2 = ResMemory(value=4096.0, unit="MiB")  # 4 GiB
        result = res_memory_utils.is_greater_than(memory1, memory2)
        assert result is True

    def test_is_greater_than_false(self):
        """Test is_greater_than returns False when first is smaller."""
        memory1 = ResMemory(value=2.0, unit="GiB")
        memory2 = ResMemory(value=4096.0, unit="MiB")  # 4 GiB
        result = res_memory_utils.is_greater_than(memory1, memory2)
        assert result is False

    def test_is_greater_than_equal(self):
        """Test is_greater_than returns False when equal."""
        memory1 = ResMemory(value=4.0, unit="GiB")
        memory2 = ResMemory(value=4096.0, unit="MiB")  # 4 GiB
        result = res_memory_utils.is_greater_than(memory1, memory2)
        assert result is False

    def test_is_greater_than_none_first(self):
        """Test is_greater_than returns False when first is None."""
        memory2 = ResMemory(value=4.0, unit="GiB")
        result = res_memory_utils.is_greater_than(None, memory2)
        assert result is False

    def test_is_greater_than_none_second(self):
        """Test is_greater_than returns True when second is None."""
        memory1 = ResMemory(value=4.0, unit="GiB")
        result = res_memory_utils.is_greater_than(memory1, None)
        assert result is True

    def test_is_less_than_true(self):
        """Test is_less_than returns True when first is smaller."""
        memory1 = ResMemory(value=2.0, unit="GiB")
        memory2 = ResMemory(value=4096.0, unit="MiB")  # 4 GiB
        result = res_memory_utils.is_less_than(memory1, memory2)
        assert result is True

    def test_is_less_than_false(self):
        """Test is_less_than returns False when first is greater."""
        memory1 = ResMemory(value=8.0, unit="GiB")
        memory2 = ResMemory(value=4096.0, unit="MiB")  # 4 GiB
        result = res_memory_utils.is_less_than(memory1, memory2)
        assert result is False

    def test_is_less_than_equal(self):
        """Test is_less_than returns False when equal."""
        memory1 = ResMemory(value=4.0, unit="GiB")
        memory2 = ResMemory(value=4096.0, unit="MiB")  # 4 GiB
        result = res_memory_utils.is_less_than(memory1, memory2)
        assert result is False

    def test_is_equal_true(self):
        """Test is_equal returns True when memories are equal."""
        memory1 = ResMemory(value=4.0, unit="GiB")
        memory2 = ResMemory(value=4096.0, unit="MiB")  # 4 GiB
        result = res_memory_utils.is_equal(memory1, memory2)
        assert result is True

    def test_is_equal_false(self):
        """Test is_equal returns False when memories are different."""
        memory1 = ResMemory(value=2.0, unit="GiB")
        memory2 = ResMemory(value=4096.0, unit="MiB")  # 4 GiB
        result = res_memory_utils.is_equal(memory1, memory2)
        assert result is False

    def test_is_equal_both_none(self):
        """Test is_equal returns True when both are None."""
        result = res_memory_utils.is_equal(None, None)
        assert result is True

    def test_is_greater_than_or_equal_greater(self):
        """Test is_greater_than_or_equal returns True when first is greater."""
        memory1 = ResMemory(value=8.0, unit="GiB")
        memory2 = ResMemory(value=4096.0, unit="MiB")  # 4 GiB
        result = res_memory_utils.is_greater_than_or_equal(memory1, memory2)
        assert result is True

    def test_is_greater_than_or_equal_equal(self):
        """Test is_greater_than_or_equal returns True when equal."""
        memory1 = ResMemory(value=4.0, unit="GiB")
        memory2 = ResMemory(value=4096.0, unit="MiB")  # 4 GiB
        result = res_memory_utils.is_greater_than_or_equal(memory1, memory2)
        assert result is True

    def test_is_greater_than_or_equal_smaller(self):
        """Test is_greater_than_or_equal returns False when first is smaller."""
        memory1 = ResMemory(value=2.0, unit="GiB")
        memory2 = ResMemory(value=4096.0, unit="MiB")  # 4 GiB
        result = res_memory_utils.is_greater_than_or_equal(memory1, memory2)
        assert result is False

    def test_is_less_than_or_equal_smaller(self):
        """Test is_less_than_or_equal returns True when first is smaller."""
        memory1 = ResMemory(value=2.0, unit="GiB")
        memory2 = ResMemory(value=4096.0, unit="MiB")  # 4 GiB
        result = res_memory_utils.is_less_than_or_equal(memory1, memory2)
        assert result is True

    def test_is_less_than_or_equal_equal(self):
        """Test is_less_than_or_equal returns True when equal."""
        memory1 = ResMemory(value=4.0, unit="GiB")
        memory2 = ResMemory(value=4096.0, unit="MiB")  # 4 GiB
        result = res_memory_utils.is_less_than_or_equal(memory1, memory2)
        assert result is True

    def test_is_less_than_or_equal_greater(self):
        """Test is_less_than_or_equal returns False when first is greater."""
        memory1 = ResMemory(value=8.0, unit="GiB")
        memory2 = ResMemory(value=4096.0, unit="MiB")  # 4 GiB
        result = res_memory_utils.is_less_than_or_equal(memory1, memory2)
        assert result is False

    def test_real_world_scenario_software_stack_validation(self):
        """Test real-world scenario: software stack RAM requirement validation."""
        # Software stack requires 8 GiB RAM
        software_stack_min_ram = ResMemory(value=8.0, unit="GiB")
        
        # Instance has 4 GiB RAM
        instance_ram = ResMemory(value=4096.0, unit="MiB")
        
        # Should return True (software stack requires more than instance provides)
        requires_more = res_memory_utils.is_greater_than(software_stack_min_ram, instance_ram)
        assert requires_more is True
        
        # Instance with enough RAM
        large_instance_ram = ResMemory(value=16.0, unit="GiB")
        
        # Should return False (software stack requirement is met)
        requires_more = res_memory_utils.is_greater_than(software_stack_min_ram, large_instance_ram)
        assert requires_more is False

    def test_edge_case_zero_values(self):
        """Test edge case with zero memory values."""
        memory1 = ResMemory(value=0.0, unit="GiB")
        memory2 = ResMemory(value=0.0, unit="MiB")
        
        assert res_memory_utils.is_equal(memory1, memory2) is True
        assert res_memory_utils.is_greater_than(memory1, memory2) is False
        assert res_memory_utils.is_less_than(memory1, memory2) is False

    def test_edge_case_very_large_values(self):
        """Test edge case with very large memory values."""
        memory1 = ResMemory(value=1024.0, unit="TiB")  # 1024 TiB
        memory2 = ResMemory(value=1.0, unit="GiB")      # 1 GiB
        
        assert res_memory_utils.is_greater_than(memory1, memory2) is True
        assert res_memory_utils.is_less_than(memory2, memory1) is True

    def test_edge_case_fractional_values(self):
        """Test edge case with fractional memory values."""
        memory1 = ResMemory(value=0.5, unit="GiB")     # 512 MiB
        memory2 = ResMemory(value=512.0, unit="MiB")   # 512 MiB
        
        assert res_memory_utils.is_equal(memory1, memory2) is True
        assert res_memory_utils.convert_to_mib(memory1) == 512.0
        assert res_memory_utils.convert_to_mib(memory2) == 512.0
