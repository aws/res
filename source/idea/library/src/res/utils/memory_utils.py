#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import Optional


def convert_to_mib(value: Optional[float], unit: Optional[str]) -> float:
    """
    Convert memory value to MiB for comparison purposes.

    :param value: Memory value
    :param unit: Memory unit (e.g., 'MiB', 'GiB', 'TiB', 'KiB', 'B')
    :return: Memory value in MiB
    """
    if value is None:
        return 0.0

    value = float(value)
    unit = (unit or "").lower()

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


def compare_memory(
    value1: Optional[float],
    unit1: Optional[str],
    value2: Optional[float],
    unit2: Optional[str],
) -> int:
    """
    Compare two memory values.

    :param value1: First memory value
    :param unit1: First memory unit
    :param value2: Second memory value
    :param unit2: Second memory unit
    :return: -1 if memory1 < memory2, 0 if equal, 1 if memory1 > memory2
    """
    if value1 is None and value2 is None:
        return 0
    if value1 is None:
        return -1
    if value2 is None:
        return 1

    mib1 = convert_to_mib(value1, unit1)
    mib2 = convert_to_mib(value2, unit2)

    if mib1 < mib2:
        return -1
    elif mib1 > mib2:
        return 1
    else:
        return 0


def is_greater_than(
    value1: Optional[float],
    unit1: Optional[str],
    value2: Optional[float],
    unit2: Optional[str],
) -> bool:
    """
    Check if memory1 is greater than memory2.

    :param value1: First memory value
    :param unit1: First memory unit
    :param value2: Second memory value
    :param unit2: Second memory unit
    :return: True if memory1 > memory2, False otherwise
    """
    return compare_memory(value1, unit1, value2, unit2) > 0


def is_less_than(
    value1: Optional[float],
    unit1: Optional[str],
    value2: Optional[float],
    unit2: Optional[str],
) -> bool:
    """
    Check if memory1 is less than memory2.

    :param value1: First memory value
    :param unit1: First memory unit
    :param value2: Second memory value
    :param unit2: Second memory unit
    :return: True if memory1 < memory2, False otherwise
    """
    return compare_memory(value1, unit1, value2, unit2) < 0


def is_equal(
    value1: Optional[float],
    unit1: Optional[str],
    value2: Optional[float],
    unit2: Optional[str],
) -> bool:
    """
    Check if memory1 is equal to memory2.

    :param value1: First memory value
    :param unit1: First memory unit
    :param value2: Second memory value
    :param unit2: Second memory unit
    :return: True if memory1 == memory2, False otherwise
    """
    return compare_memory(value1, unit1, value2, unit2) == 0


def is_greater_than_or_equal(
    value1: Optional[float],
    unit1: Optional[str],
    value2: Optional[float],
    unit2: Optional[str],
) -> bool:
    """
    Check if memory1 is greater than or equal to memory2.

    :param value1: First memory value
    :param unit1: First memory unit
    :param value2: Second memory value
    :param unit2: Second memory unit
    :return: True if memory1 >= memory2, False otherwise
    """
    return compare_memory(value1, unit1, value2, unit2) >= 0


def is_less_than_or_equal(
    value1: Optional[float],
    unit1: Optional[str],
    value2: Optional[float],
    unit2: Optional[str],
) -> bool:
    """
    Check if memory1 is less than or equal to memory2.

    :param value1: First memory value
    :param unit1: First memory unit
    :param value2: Second memory value
    :param unit2: Second memory unit
    :return: True if memory1 <= memory2, False otherwise
    """
    return compare_memory(value1, unit1, value2, unit2) <= 0
