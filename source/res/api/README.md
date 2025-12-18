# AWS RES API

## API Specification
The RES API specification, defined in the `spec/` directory, is available in two different formats:
[OpenAPI](https://swagger.io/specification/) and [Smithy](https://awslabs.github.io/smithy/).

The OpenAPI definition can be found in the `spec/openapi/RES.openapi.yaml` file while the Smithy model is
defined in the `spec/smithy` directory.

The OpenAPI model can be automatically generated from the Smithy one by using the following Gradle task:
```bash
./gradlew buildSmithyModel
```

Additional Gradle tasks are available in order to streamline the development of the API:

```
./gradlew tasks

Research and Engineering Studio API tasks
-----------------------------------------
buildSmithyModel - Build Smithy model and generate the OpenAPI spec file
cleanGenerated - Clean generated folder before generation
fixImports - Fix imports in generated Python server code
generatePythonClient - Generate a Python client using Open API Tools Generator.
generatePythonServer - Generate a Python server using Open API Tools Generator.
redoc - Generate a standalone html page with the redoc documentation of the API
swaggerUI - Run a Docker container hosting a Swagger UI with the Research and Engineering Studio API specs.
```

### Development Workflow

The usual development workflow to follow when extending the ParallelCluster API is the following:
1. Modify the Smithy model under `spec/smithy` in order to reflect the necessary API changes
2. Build and validate the Smithy model by running `./gradlew buildSmithyModel`. Review and solve errors and warnings produced by the Smithy build.
3. Review the OpenAPI model that is generated under `spec/openapi/RES.openapi.yaml` by eventually using
   one of the available documentation tools described above. Commit the changes.
4. Run `./gradlew generatePythonServer` to generate the server stub under the generated/server-stub directory. The generated stub will have a similar code structure to `source/idea/infrastructure/resources/lambda_functions/backend/`.
   Import the newly applied changes to the backend lambda source code:
   1. Changes to the API request/response model require changes to files under `source/idea/infrastructure/resources/lambda_functions/models`. The newly generated models in the server stub can be imported as is, just mind fixing unused imports and formatting. To avoid huge diffs import only models related to your modifications.
   2. Changes to the API operations and request/response model require an update to the controllers (namely the handlers of the various API endpoints). The updated controller signature can be retrieved from the generated stub files and relevant changes need to be applied to controllers under the `source/idea/infrastructure/resources/lambda_functions/controllers` directory.
   3. Any API change will generate a change in the OpenAPI spec. Please import the newly changes available in the generated stub to `source/idea/infrastructure/resources/lambda_functions/openapi/RES.openapi.yaml`. For each diff with the respect to the generated file please add an `#  override: reason` comment documenting why this is required.
5. Run `./gradlew generateTypeScriptClient` to generate the TypeScript client under the generated/client/typescript/src directory. 
   Import the newly applied changes to the webapp code:
   1. Copy all the .ts files to the `source/idea/idea-cluster-manager/webapp/src/client/generated` directory.
   2. Update the existing RES client code under `source/idea/idea-cluster-manager/webapp/src/client` directory to invoke the new API.
6. Open a PR to review the changes to the API.

### OpenAPI Documentation Tools
From the OpenAPI model, a visual documentation can be produced, in either the [Swagger UI](https://swagger.io/tools/swagger-ui/) or the [ReDoc](https://github.com/Redocly/redoc) format.

To run local server hosting the Swagger UI with live reloading enabled run the following command:
`./gradlew swaggerUI`.

You can then review the documentation by opening a browser to http://0.0.0.0:8080.
To stop the Docker container exposing the Swagger UI run `docker stop res-swagger-ui`.

To generate a standalone HTML page with the API documentation in the ReDoc format run the following command:
`./gradlew redoc`. Once compiled the file will be available at `spec/openapi/RES.openapi.redoc.html`.


