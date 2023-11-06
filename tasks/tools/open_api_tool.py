#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
#  with the License. A copy of the License is located at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
#  and limitations under the License.

from openapi_schema_pydantic import *
from ideadatamodel import (
    constants,
    IdeaOpenAPISpecEntry,
    SocaEnvelope
)

from tasks import idea
from ideasdk.utils import Utils
from typing import Dict, Type, Optional, List
from pydantic import BaseModel, AnyHttpUrl


class OpenAPITool:
    """
    Generate OpenAPI 3.0 Specification for IDEA APIs

    Refer: https://github.com/OAI/OpenAPI-Specification and https://swagger.io/docs/specification/about/ for more details on OpenAPI 3.0 Specification
    """

    def __init__(self, entries: List[IdeaOpenAPISpecEntry],
                 api_doc: Optional[Dict],
                 enable_file_transfer_entries: bool = False,
                 module_id: str = None,
                 module_version: str = None,
                 server_url: str = None):

        self.entries = entries

        # dynamic variables rendered by SocaServer at run time based on request.
        self.module_id = Utils.get_as_string(module_id, '{{ module_id }}')
        self.module_version = Utils.get_as_string(module_version, '{{ module_version }}')
        self.server_url = Utils.get_as_string(server_url, '{{ server_url }}')

        self.enable_file_transfer_entries = Utils.get_as_bool(enable_file_transfer_entries, False)

        # spec - top level - enforce mandatory items
        self.api_doc_spec = api_doc['spec']
        self.title = self.api_doc_spec['title']
        self.description = self.api_doc_spec['description']

        # initialize spec tags
        self.spec_tags: List[Tag] = []
        doc_tags = Utils.get_value_as_list('tags', self.api_doc_spec, [])
        for doc_tag in doc_tags:
            spec_tag = Tag(
                name=doc_tag['name'],
                description=doc_tag['description']
            )
            external_docs = Utils.get_value_as_dict('external_docs', doc_tag)
            if external_docs is not None:
                external_doc_url = external_docs['url']
                external_doc_description = Utils.get_value_as_string('description', external_docs)
                spec_tag.externalDocs = ExternalDocumentation(
                    url=AnyHttpUrl(url=external_doc_url, scheme=external_doc_url.split(':')[0]),
                    description=external_doc_description
                )
            self.spec_tags.append(spec_tag)

        # initialize doc entries as a map
        self.api_doc_entries: Dict[str, Dict] = {}
        entries = Utils.get_value_as_list('entries', self.api_doc_spec, [])
        for entry in entries:
            namespace = entry['namespace']
            self.api_doc_entries[namespace] = entry

        # spec component schemas
        self.schemas: Dict[str, Schema] = {}

        # open api spec
        self.open_api_spec: Optional[OpenAPI] = None

    @staticmethod
    def get_mutable_json_schema(model: Type[BaseModel]) -> Dict:
        """
        convert a Pydantic data model class to JSON Schema
        return a deep copy as model.schema() returns a cached copy
        """
        return Utils.deep_copy(model.schema())

    def build_schema(self, payload_type: Type[BaseModel], request: bool, listing: bool) -> Dict:
        """
        convert a request or response payload to OpenAPI Spec request or response operation component

        * convert IDEA datamodel objects to JSON Schema
        * clean up JSON schema based on IDEA functionality and operation type
        * generate unique Envelope per request/response operation, so that generated clients can serialize/deserialize the applicable payloads for the right type.
        * collect all JSON schema definitions along the way
        :param Type[BaseModel] payload_type: IDEA API Request or Response Payload Type
        :param bool request: indicate if the operation is a request or response operation
        :param bool listing: indicate if the operation is a listing operation
        :return:
        """
        envelope_schema = self.get_mutable_json_schema(SocaEnvelope)
        for name, value in envelope_schema['definitions'].items():
            if name == 'SocaAuthScope':
                continue
            self.schemas[name] = Schema(**value)
        del envelope_schema['properties']['scope']
        if request:
            del envelope_schema['properties']['error_code']
            del envelope_schema['properties']['message']
            del envelope_schema['properties']['success']
        del envelope_schema['definitions']

        api_schema = self.get_mutable_json_schema(payload_type)
        request_title = api_schema["title"]
        if 'definitions' in api_schema:
            for name, value in api_schema['definitions'].items():
                self.schemas[name] = Schema(**value)
            del api_schema['definitions']

        if request and listing:
            if 'listing' in api_schema['properties']:
                del api_schema['properties']['listing']
        self.schemas[request_title] = Schema(**api_schema)

        envelope_schema['properties']['payload']['$ref'] = f'#/definitions/{request_title}'
        envelope_schema['title'] = f'{request_title}Envelope'

        content = Utils.to_yaml(envelope_schema)
        content = content.replace('#/definitions', '#/components/schemas')
        return Utils.from_yaml(content)

    @staticmethod
    def add_file_transfer_paths(spec_paths: Paths):
        """
        file transfer routes for upload and download are served via special routes exposed in SocaServer.
        needs separate handling for these routes as the Http Methods are different from all other IDEA APIs.
        """

        response_json = Schema(
            type='object',
            properties={
                'error_code': Schema(
                    type='string'
                ),
                'success': Schema(
                    type='boolean'
                ),
                'message': Schema(
                    type='string'
                )
            }
        )

        # file upload
        spec_paths['/FileBrowser.UploadFile'] = PathItem(
            put=Operation(
                tags=['FileBrowser'],
                operationId='FileBrowser.UploadFile',
                security=[{
                    'BearerToken': []
                }],
                parameters=[
                    Parameter(
                        name='cwd',
                        description='Current Working Directory',
                        required=True,
                        param_in='query',
                        param_schema=Schema(type='string')
                    )
                ],
                requestBody=RequestBody(
                    content={
                        'multipart/form-data': MediaType(
                            media_type_schema=Schema(
                                type='object',
                                properties={
                                    'files[]': Schema(
                                        type='array',
                                        items=Schema(
                                            type='string',
                                            schema_format='binary'
                                        )
                                    )
                                }
                            )
                        )
                    }
                ),
                responses={
                    '200': Response(
                        description='UploadFile Response',
                        content={
                            'application/json': MediaType(
                                media_type_schema=response_json
                            )
                        }
                    )
                }
            )
        )

        # file download
        spec_paths['/FileBrowser.DownloadFile'] = PathItem(
            get=Operation(
                tags=['FileBrowser'],
                operationId='FileBrowser.DownloadFile',
                security=[{
                    'BearerToken': []
                }],
                parameters=[
                    Parameter(
                        name='file',
                        description='Path of the file to download',
                        required=True,
                        param_in='query',
                        param_schema=Schema(type='string')
                    )
                ],
                responses={
                    '200': Response(
                        description='DownloadFile Response',
                        content={
                            'application/json': MediaType(
                                media_type_schema=response_json
                            ),
                            'text/plain': MediaType(
                                media_type_schema=Schema(
                                    type='string'
                                )
                            ),
                            'application/xml': MediaType(
                                media_type_schema=Schema(
                                    type='string'
                                )
                            ),
                            'image/*': MediaType(
                                media_type_schema=Schema(
                                    type='string',
                                    schema_format='binary'
                                )
                            ),
                            '*/*': MediaType(
                                media_type_schema=Schema(
                                    type='string',
                                    schema_format='binary'
                                )
                            )
                        }
                    )
                }
            )
        )

    def get_examples(self, namespace: str, is_request: bool) -> Optional[Dict[str, Example]]:
        api_doc_entry = Utils.get_value_as_dict(namespace, self.api_doc_entries)
        if api_doc_entry is None:
            return None

        if is_request:
            operation_type = Utils.get_value_as_dict('request', api_doc_entry)
        else:
            operation_type = Utils.get_value_as_dict('response', api_doc_entry)

        if operation_type is None:
            return None

        examples = Utils.get_value_as_list('examples', operation_type)
        if examples is None or len(examples) == 0:
            return None

        result = {}
        for example_entry in examples:
            example_name = example_entry['name']
            try:
                result[example_name] = Example(
                    summary=Utils.get_value_as_string('description', example_entry),
                    value=Utils.from_json(example_entry['value'])
                )
            except Exception as e:
                operation_tag = 'request' if is_request else 'response'
                idea.console.warning(f'[{namespace}] ({operation_tag}) failed to parse json value for example: {example_name}, {e}')

        if len(result) == 0:
            return None

        return result

    def build_paths(self) -> Paths:
        """
        convert spec entry to OpenAPISpec operations.
        :return: Paths
        """
        spec_paths = {}
        for entry in self.entries:
            path = f'/{entry.namespace}'
            component_tag = entry.namespace.split('.')[0]
            operation_title_prefix = entry.namespace.split('.')[-1]
            request_schema = Schema(**self.build_schema(
                payload_type=entry.request,
                request=True,
                listing=entry.is_listing
            ))
            result_schema = Schema(**self.build_schema(
                payload_type=entry.result,
                request=False,
                listing=entry.is_listing
            ))

            spec_paths[path] = PathItem(
                post=Operation(
                    operationId=entry.namespace,
                    tags=[component_tag],
                    security=[] if entry.is_public else [{
                        'BearerToken': []
                    }],
                    requestBody=RequestBody(
                        description=f'{operation_title_prefix} Request',
                        content={
                            'application/json': MediaType(
                                media_type_schema=request_schema,
                                examples=self.get_examples(namespace=entry.namespace, is_request=True)
                            )
                        },
                        required=True
                    ),
                    responses={
                        "200": Response(
                            description=f'{operation_title_prefix} Response',
                            content={
                                'application/json': MediaType(
                                    media_type_schema=result_schema,
                                    examples=self.get_examples(namespace=entry.namespace, is_request=False)
                                )
                            }
                        )
                    }
                )
            )

        if self.enable_file_transfer_entries:
            self.add_file_transfer_paths(spec_paths)

        return spec_paths

    def build(self) -> OpenAPI:

        return OpenAPI(
            info=Info(
                title=self.title,
                description=f'{self.description} (ModuleId: {self.module_id})',
                version=self.module_version,
            ),
            servers=[
                Server(url=self.server_url)
            ],
            tags=self.spec_tags,
            openapi=constants.OPEN_API_SPEC_VERSION,
            paths=self.build_paths(),
            components=Components(
                securitySchemes={
                    'BearerToken': SecurityScheme(
                        type='http',
                        scheme='bearer'
                    )
                },
                schemas=self.schemas
            )
        )

    def generate(self, output_format: str = 'yaml') -> str:

        if self.open_api_spec is None:
            idea.console.print('processing openapi spec entries and documentation ...')
            self.open_api_spec = self.build()

        if output_format == 'json':
            idea.console.print('converting to json ...')
            content = Utils.to_json(self.open_api_spec)
        else:
            idea.console.print('converting to yaml ...')
            content = Utils.to_yaml(self.open_api_spec)

        idea.console.print('post-processing ...')
        return content.replace('#/definitions', '#/components/schemas')
