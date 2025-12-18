#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

"""
Utility functions for ResMemory operations and comparisons.

This module provides comparison operations for ResMemory objects that are missing
in the auto-generated code. The implementation follows the same pattern as the
SocaMemory class for consistency.
"""

from typing import Optional
from api.models.res_memory import ResMemory


def convert_to_mib(memory: ResMemory) -> float:
    """
    Convert ResMemory to MiB for comparison purposes.
    Based on SocaMemory implementation pattern.
    
    :param memory: ResMemory object to convert
    :return: Memory value in MiB
    """
    if not memory or memory.value is None:
        return 0.0
    
    value = float(memory.value)
    unit = (memory.unit or "").lower()
    
    # Convert to MiB based on unit
    if unit in ("mib", "mi"):
        return value
    elif unit in ("gib", "gi", "gb"):
        return value * 1024
    elif unit in ("tib", "ti", "tb"):
        return value * 1024 * 1024
    elif unit in ("kib", "ki", "kb"):
        return value / 1024
    elif unit in ("b", "bytes"):
        return value / (1024 * 1024)
    else:
        # Default to MiB if unit is unknown or empty
        return value


def compare_memory(memory1: Optional[ResMemory], memory2: Optional[ResMemory]) -> int:
    """
    Compare two ResMemory objects.
    
    :param memory1: First ResMemory object
    :param memory2: Second ResMemory object  
    :return: -1 if memory1 < memory2, 0 if equal, 1 if memory1 > memory2
    """
    if not memory1 and not memory2:
        return 0
    if not memory1:
        return -1
    if not memory2:
        return 1
    
    mib1 = convert_to_mib(memory1)
    mib2 = convert_to_mib(memory2)
    
    if mib1 < mib2:
        return -1
    elif mib1 > mib2:
        return 1
    else:
        return 0


def is_greater_than(memory1: Optional[ResMemory], memory2: Optional[ResMemory]) -> bool:
    """
    Check if memory1 is greater than memory2.
    
    :param memory1: First ResMemory object
    :param memory2: Second ResMemory object
    :return: True if memory1 > memory2, False otherwise
    """
    return compare_memory(memory1, memory2) > 0


def is_less_than(memory1: Optional[ResMemory], memory2: Optional[ResMemory]) -> bool:
    """
    Check if memory1 is less than memory2.
    
    :param memory1: First ResMemory object
    :param memory2: Second ResMemory object
    :return: True if memory1 < memory2, False otherwise
    """
    return compare_memory(memory1, memory2) < 0


def is_equal(memory1: Optional[ResMemory], memory2: Optional[ResMemory]) -> bool:
    """
    Check if memory1 is equal to memory2.
    
    :param memory1: First ResMemory object
    :param memory2: Second ResMemory object
    :return: True if memory1 == memory2, False otherwise
    """
    return compare_memory(memory1, memory2) == 0


def is_greater_than_or_equal(memory1: Optional[ResMemory], memory2: Optional[ResMemory]) -> bool:
    """
    Check if memory1 is greater than or equal to memory2.
    
    :param memory1: First ResMemory object
    :param memory2: Second ResMemory object
    :return: True if memory1 >= memory2, False otherwise
    """
    return compare_memory(memory1, memory2) >= 0


def is_less_than_or_equal(memory1: Optional[ResMemory], memory2: Optional[ResMemory]) -> bool:
    """
    Check if memory1 is less than or equal to memory2.
    
    :param memory1: First ResMemory object
    :param memory2: Second ResMemory object
    :return: True if memory1 <= memory2, False otherwise
    """
    return compare_memory(memory1, memory2) <= 0
