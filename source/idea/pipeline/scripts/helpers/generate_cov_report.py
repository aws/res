#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
import re
import subprocess

import yaml

COVERAGE_FILE = "codeCoverage.yml"
coverage_report_cmd = ["coverage", "report", "-i"]


class bcolors:
    """
    Colors to be used for different threshold of coverage
    """

    PASS = "\033[92m"
    FAIL = "\033[91m"
    END_ESCAPE_SEQUENCE = "\033[0m"


def split_report_line(clean_line):
    """
    Splits coverage report line into array of words
    """
    cwd = os.getcwd()
    lencwd = len(cwd)
    tmp_array = re.split(r" {1,}", clean_line)
    if len(tmp_array) == 4 and not tmp_array[0].startswith("Name"):
        if tmp_array[0].startswith("/"):
            tmp_array[0] = tmp_array[0][lencwd:]
        line_array = [tmp_array[0]]
        line_array = list(filter(None, line_array))
        line_array.append(tmp_array[1])
        line_array.append(tmp_array[2])
        line_array.append(tmp_array[3].replace("%", ""))
        return line_array


def filter_lines_out(line_array):
    """
    filters out the lines not of interest from our
    coverage logic
    """
    if line_array and "tests" not in line_array and line_array[1] != "Name":
        return True
    else:
        return False


def get_prefix_in_actual_coverage(full_path, coverage):
    """
    Returns the longest subtree that this file belongs to associate
    with the right coverage key specified in `codeCoverage.yml`
    """
    longest_common_prefix = ""
    for coverage_tree in coverage.keys():
        if full_path.startswith(coverage_tree):
            common_prefix = coverage_tree
            if len(common_prefix) > len(longest_common_prefix):
                longest_common_prefix = common_prefix
    return longest_common_prefix


def get_actual_coverage(coverage, coverage_line):
    """
    The gathers the coverage values to the correct tree specified
    in `codeCoverage.yml`
    """
    full_path = coverage_line[0]
    coverage_tree = get_prefix_in_actual_coverage(full_path, coverage)
    if coverage_tree in coverage.keys():
        coverage[coverage_tree][1] += int(coverage_line[1])
        coverage[coverage_tree][2] += int(coverage_line[2])


def normalize_actual_coverage(coverage):
    """
    returns the actual coverage for each tree in `codeCoverage.yml`
    """
    for coverage_tree in coverage.keys():
        total_statements = coverage[coverage_tree][1]
        total_missed = coverage[coverage_tree][2]
        coverage[coverage_tree][3] = (
            total_statements - total_missed
        ) / total_statements


def print_colors(line, coverage_flag):
    """
    Sets the color based on flag
    """
    if coverage_flag == 0:
        return f"{bcolors.PASS}{line}{bcolors.END_ESCAPE_SEQUENCE}"
    else:
        return f"{bcolors.FAIL}{line}{bcolors.END_ESCAPE_SEQUENCE}"


def print_coverage_report(coverage, file_handle):
    """
    Print the pretty formatted report
    """
    tree_name = "Source Tree"
    required_coverage = "Required"
    achieved_coverage = "Achieved"
    statements = "Statements"
    missed = "Missed"
    printable_string = f"{tree_name:75s}   {required_coverage:10s} {achieved_coverage:10s} {statements:10s} {missed:10s}\n"
    file_handle.write(f"{'-'*120}\n")
    file_handle.write(print_colors(printable_string, 0))
    file_handle.write(f"{'-'*120}\n")
    i = 0
    total_statements = 0
    missed_statements = 0
    overall_required = 0.0
    for key, values in coverage.items():
        printable_string = f"{key:80s}   {values[0]:4.2f}   {values[3]:4.2f}   {values[1]:6d}   {values[2]:6d}\n"
        flag = int(float(values[0]) / float(values[3]))
        file_handle.write(print_colors(printable_string, flag))
        total_statements += values[1]
        missed_statements += values[2]
        overall_required = max(overall_required, float(values[0]))
        i += 1
    overall_achieved = float(total_statements - missed_statements) / float(
        total_statements
    )
    file_handle.write(f"{'-'*120}\n")
    total = "Overall"
    printable_string = f"{total:80s}   {overall_required:4.2f}   {overall_achieved:4.2f}   {total_statements:6d}   {missed_statements:6d}\n"
    file_handle.write(print_colors(printable_string, 0))
    file_handle.write(f"{'-'*120}\n")


def get_required_coverage(input_file):
    """
    Load the required coverage from the file
       0: required coverage
       1: total_statements
       2: missed_statements
       3: evaluated coverage
    """
    with open(input_file, "r") as file_handle:
        coverage = yaml.safe_load(file_handle)
    for key, val in coverage.items():
        coverage[key] = [val, 0, 0, 0.0]
    return coverage


coverage = get_required_coverage(COVERAGE_FILE)

with subprocess.Popen(
    coverage_report_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
) as proc:
    for line in proc.stdout.readlines():
        clean_line = line.decode("utf-8").rstrip()
        line_array = split_report_line(clean_line)
        if filter_lines_out(line_array):
            get_actual_coverage(coverage, line_array)

normalize_actual_coverage(coverage)

with open("summary_report.txt", "w") as file_handle:
    print_coverage_report(coverage, file_handle)
