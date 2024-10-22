# Research and Engineering Studio on AWS

# Documentation

https://docs.aws.amazon.com/res/latest/ug/overview.html

# Directories

## res

Represents a shared library that can be installed and utilized by various computational components in RES.

### resources

Containes sub-directories for all the RES specific resources. Includes files that define the schema of the resource and business logic functions along with DDB interactios.

The resources directory will follow a structure as follows

    resources
    - <resource_name>
    -- schema.py
    -- model.py

## res_meta

Defines basic meta data for the res package

## tests

Contains tests for the res library

