# Research and Engineering Studio on AWS

# Documentation

https://docs.aws.amazon.com/res/latest/ug/overview.html

# Directories

## datamodel

This library contains RES data models and serializers that are auto-generated from Smithy models and can be installed and utilized by various computational components in RES.

### models

Auto-generated Python data model classes organized by Lambda function:

- `models/backend/` — Backend Lambda models
- `models/dcv_session_management/` — DCV Session Management Lambda models
- `models/base_model.py` — Shared base class for all models
- `models/*.py` — Shared models (e.g., error types from `spec/smithy/shared/`) live at the parent level and are imported from there by each Lambda's subpackage. If the same module name exists in multiple subdirs, an `ImportError` is raised to catch accidental collisions.

A `SubdirFinder` in `__init__.py` enables importing from any subdir using the parent package path:

```python
from datamodel.models.virtual_desktop_session import VirtualDesktopSession  # from backend/
from datamodel.models.health_check_response_content import HealthCheckResponseContent  # from dcv_session_management/
```

### serializers

Auto-generated serializers organized by Lambda function:

- `serializers/backend/` — Backend Lambda serializers
- `serializers/base_serializer.py` — Shared base class for all serializers

Serializers handle conversion between Python models and DynamoDB/JSON formats. Existing serializers with manual customizations are preserved during regeneration; only new serializers are added and stale ones removed.

### Regenerating models and serializers

Run `./gradlew generatePythonServer` from `source/res/api/`. The post-generation script (`copy_to_data_model.sh`) automatically copies generated models and serializers to the correct subdirectories.

## datamodel_meta

Defines basic metadata for the datamodel package.

## tests

Contains tests for the datamodel library.
