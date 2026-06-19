# AWS RES API

## API Specification
The RES API specifications, defined in the `spec/` directory, are available in two different formats:
[OpenAPI](https://swagger.io/specification/) and [Smithy](https://awslabs.github.io/smithy/).

There are two separate API specifications, one for each Lambda function:

| API | Smithy Model | OpenAPI Spec | Description |
|-----|-------------|--------------|-------------|
| RES Backend | `spec/smithy/backend/` | `spec/openapi/RES.openapi.yaml` | Public-facing RES API served by the backend Lambda |
| DCV Session Management | `spec/smithy/dcv-session-management/` | `spec/openapi/DCVSessionManagement.openapi.yaml` | Private API for DCV session management Lambda |

### Smithy Project Structure

Both Smithy models are organized as subprojects of a single Gradle multi-project build under `spec/smithy/`:

```
spec/smithy/
├── build.gradle.kts              # Shared plugin, dependencies, and repositories
├── settings.gradle.kts           # Includes backend and dcv-session-management subprojects
├── gradle.properties             # Shared smithy version
├── .gitignore
├── shared/                       # Shared Smithy files (symlinked into each subproject)
│   ├── Errors.smithy             # Common error types (namespace: res)
│   └── Validators.smithy         # Common validators
├── backend/                      # RES Backend Lambda API
│   ├── build.gradle.kts
│   ├── smithy-build.json         # Service: res#RES
│   └── model/
│       ├── res.smithy            # Service definition
│       ├── Errors.smithy → ../../shared/Errors.smithy
│       ├── Validators.smithy → ../../shared/Validators.smithy
│       ├── types/                # Data model types
│       └── operations/           # API operations
└── dcv-session-management/       # DCV Session Management Lambda API
    ├── build.gradle.kts
    ├── smithy-build.json         # Service: res.dcvsessionmanagement#DCVSessionManagement
    └── model/
        ├── dcv-session-management.smithy  # Service definition
        ├── Errors.smithy → ../../shared/Errors.smithy
        ├── Validators.smithy → ../../shared/Validators.smithy
        └── operations/           # API operations
```

## Building

The OpenAPI specs can be automatically generated from the Smithy models by using the following Gradle task:
```bash
./gradlew buildSmithyModel
```

This builds both Smithy models and generates the corresponding OpenAPI YAML files under `spec/openapi/`. These generated files are gitignored — they are build artifacts, not source files.

### Available Gradle Tasks

```
./gradlew tasks

RES API tasks
-------------
redoc - Generate a standalone html page with the redoc documentation of the API
swaggerUI - Run a Docker container hosting a Swagger UI with the Research and Engineering Studio API specs.
buildSmithyModel - Build all Smithy models and generate OpenAPI spec files
cleanGenerated - Clean all generated folders
generatePythonClient - Generate Python clients for all Lambda APIs
generatePythonServer - Generate Python servers for all Lambda APIs
generateTypeScriptClient - Generate TypeScript client for the Backend Lambda API
```

The aggregate tasks (`generatePythonServer`, `generatePythonClient`) generate code for all Lambda APIs in one command. `generateTypeScriptClient` currently only covers the Backend Lambda. Per-Lambda tasks are also available (e.g. `generateBackendPythonServer`, `generateDcvSessionManagementPythonServer`) and can be listed with `./gradlew tasks --all`.

## Development Workflow

1. Modify the Smithy model under the corresponding subproject directory:
   - Backend Lambda: `spec/smithy/backend/`
   - DCV Session Management Lambda: `spec/smithy/dcv-session-management/`
2. Build and validate all Smithy models by running `./gradlew buildSmithyModel`. Review and solve errors and warnings produced by the Smithy build.
3. Review the generated OpenAPI specs under `spec/openapi/`.
4. Run `./gradlew generatePythonServer` to generate server stubs for all Lambda APIs. The generated stubs will be under:
   - `generated/backend/server-stub/` for the Backend Lambda
   - `generated/dcv-session-management/server-stub/` for the DCV Session Management Lambda
5. Import the newly applied changes to the lambda source code:
   1. Models, serializers, base files (`base_model.py`, `base_serializer.py`), and utilities (`util.py`, `typing_utils.py`, `jsonifier.py`) are automatically copied to `source/idea/data-model/src/datamodel/` by `copy_to_data_model.sh` (runs as part of post-generation). Shared models (from `spec/smithy/shared/`) are placed in the parent `models/` directory; Lambda-specific files go into `models/<lambda-name>/` subdirectories. Existing serializers with manual changes are preserved.
   2. Changes to the API operations and request/response model require an update to the controllers (namely the handlers of the various API endpoints). The updated controller signature can be retrieved from the generated stub files and relevant changes need to be applied to controllers under the `source/idea/<lambda-name>/api/controllers` directory.
   3. To customize serialization / de-serialization, override methods in the serializers under `source/idea/data-model/src/datamodel/serializers/<lambda-name>`. Manual changes are preserved across regeneration.
   4. Any API change will generate a change in the OpenAPI spec. Please import the newly changes available in the generated stub to the corresponding OpenAPI spec file (`source/idea/backend/api/openapi/RES.openapi.yaml` or `source/idea/dcv-session-management/api/openapi/DCVSessionManagement.openapi.yaml`). For each diff with the respect to the generated file please add an `#  override: reason` comment documenting why this is required.
6. Run `./gradlew generateTypeScriptClient` to generate TypeScript clients. Import the newly applied changes to the webapp code:
   1. Copy all the .ts files to the `source/idea/idea-cluster-manager/webapp/src/client/generated` directory.
   2. Update the existing RES client code under `source/idea/idea-cluster-manager/webapp/src/client` directory to invoke the new API.
7. Run `./gradlew generatePythonClient` to generate Python clients for all Lambda APIs. For the DCV Session Management client, this runs a pipeline that cleans stale generated output, generates the client from the OpenAPI spec, adds copyright headers, then replaces the existing client at `source/idea/library/src/res/clients/dcv_session_management_client/`. If any step fails, the existing client is preserved.
8. Open a PR to review the changes to the API.

## OpenAPI Documentation Tools
From the OpenAPI model, a visual documentation can be produced, in either the [Swagger UI](https://swagger.io/tools/swagger-ui/) or the [ReDoc](https://github.com/Redocly/redoc) format.

To run local server hosting the Swagger UI with live reloading enabled run the following command:
`./gradlew swaggerUI`.

You can then review the documentation by opening a browser to http://0.0.0.0:8080.
To stop the Docker container exposing the Swagger UI run `docker stop res-swagger-ui`.

To generate a standalone HTML page with the API documentation in the ReDoc format run the following command:
`./gradlew redoc`. Once compiled the file will be available at `spec/openapi/RES.openapi.redoc.html`.
