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

# Copyright (c) 2020 Phillip Dupuis
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE
# FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import tasks.idea as idea

from ideasdk import notice
from ideasdk.utils import Utils

import importlib
import inspect
import json
import os
import shutil
import sys
from importlib.util import spec_from_file_location, module_from_spec
from tempfile import mkdtemp
from types import ModuleType
from typing import Type, Dict, Any, List, Set, Tuple, Optional
from uuid import uuid4
from pydantic import BaseModel, Extra, create_model

try:
    from pydantic.generics import GenericModel
except ImportError:
    GenericModel = None


class TypingsGenerator:
    """
    Convert IDEA Python models to TypeScript
    This is a modified implementation of @phillipdupuis's pydantic-to-typescript to satisfy IDEA requirements.

    Source: https://github.com/phillipdupuis/pydantic-to-typescript
    """

    def __init__(self):
        pass

    def import_module(self, path: str) -> ModuleType:
        """
        Helper which allows modules to be specified by either dotted path notation or by filepath.

        If we import by filepath, we must also assign a name to it and add it to sys.modules BEFORE
        calling 'spec.loader.exec_module' because there is code in pydantic which requires that the
        definition exist in sys.modules under that name.
        """
        try:
            if os.path.exists(path):
                name = uuid4().hex
                spec = spec_from_file_location(name, path, submodule_search_locations=[])
                module = module_from_spec(spec)
                sys.modules[name] = module
                spec.loader.exec_module(module)
                return module
            else:
                return importlib.import_module(path)
        except BaseException as e:
            idea.console.error(
                "The --module argument must be a module path separated by dots or a valid filepath"
            )
            raise e

    def is_submodule(self, obj, module_name: str) -> bool:
        """
        Return true if an object is a submodule
        """
        return inspect.ismodule(obj) and getattr(obj, "__name__", "").startswith(
            f"{module_name}."
        )

    def is_concrete_pydantic_model(self, obj) -> bool:
        """
        Return true if an object is a concrete subclass of pydantic's BaseModel.
        'concrete' meaning that it's not a GenericModel.
        """
        if not inspect.isclass(obj):
            return False
        elif obj is BaseModel:
            return False
        elif GenericModel and issubclass(obj, GenericModel):
            return bool(obj.__concrete__)
        else:
            return issubclass(obj, BaseModel)

    def extract_pydantic_models(self, module: ModuleType) -> Set[Tuple[str, Type[BaseModel]]]:
        """
        Given a module, return a list of the pydantic models contained within it.
        """
        models = set()
        module_name = module.__name__

        for name, model in inspect.getmembers(module, self.is_concrete_pydantic_model):
            models.add((name, model))

        for name, submodule in inspect.getmembers(
            module, lambda obj: self.is_submodule(obj, module_name)
        ):
            sub_models = self.extract_pydantic_models(submodule)
            for sub_model in sub_models:
                models.add((name, sub_model))

        return models

    def remove_master_model_from_output(self, output: str) -> None:
        """
        A faux 'master model' with references to all the pydantic models is necessary for generating
        clean typescript definitions without any duplicates, but we don't actually want it in the
        output. This function handles removing it from the generated typescript file.
        """
        with open(output, "r") as f:
            lines = f.readlines()

        start, end = 0, len(lines)
        for i, line in enumerate(lines):
            if line.rstrip("\r\n") == "export interface _Master_ {":
                start = i
            elif (start is not None) and line.rstrip("\r\n") == "}":
                end = i
                break

        new_lines = lines[:start] + lines[(end + 1):]
        with open(output, "w") as f:
            f.writelines(new_lines)

    def clean_schema(self, schema: Dict[str, Any]) -> None:
        """
        Clean up the resulting JSON schemas by:

        1) Removing titles from JSON schema properties.
           If we don't do this, each property will have its own interface in the
           resulting typescript file (which is a LOT of unnecessary noise).
        2) Getting rid of the useless "An enumeration." description applied to Enums
           which don't have a docstring.
        """
        for prop in schema.get("properties", {}).values():
            prop.pop("title", None)

        if "enum" in schema and schema.get("description") == "An enumeration.":
            del schema["description"]

    @staticmethod
    def fix_anomalies(schema: Dict):
        """
        the original json schema gets generated as below, where inner model classes,
        that are referred from API request response classes, are generated with
        multiple references in definitions.

        schema:
            properties: {
                Car: {
                    $ref: #/definitions/<uuid>__Car
                }
            }
            definitions: {
                <uuid>__Car: {
                },
                ideadatamodel__Car: {
                },
                ListCars: {
                    listing: {
                        $ref: <uuid>__Car
                    }
                }
            }

        goal is to unify all these references to a single reference:
            #/definitions/Car

        one major caveat to this implementation is the Model class names must be unique.
        this issue can be eliminated as long as all model class names are unique across modules.
        """

        definitions = Utils.get_value_as_dict('definitions', schema)

        # find anomalies in schema properties
        properties = Utils.get_value_as_dict('properties', schema)
        if properties is not None:
            for name, value in properties.items():
                ref = Utils.get_value_as_string('$ref', value)
                if '__' not in ref:
                    continue
                definition_key = ref.replace('#/definitions/', '')
                definition = Utils.get_value_as_dict(definition_key, definitions)
                definitions[name] = definition
                updated_ref = f'#/definitions/{name}'
                value['$ref'] = updated_ref

        # traverse definitions and replace anomalies

        add_definitions = {}

        def get_update_ref(ref_value: Optional[str]) -> Optional[str]:
            if ref_value is None:
                return None
            if '__' not in ref:
                return ref
            ref_type_name = ref.split('__')[-1]
            return f'#/definitions/{ref_type_name}'

        if definitions is not None:
            for name, value in definitions.items():
                if '__' in name:
                    title = Utils.get_value_as_string('title', value)
                    add_definitions[title] = value
                current_properties = Utils.get_value_as_dict('properties', value)
                if current_properties is None:
                    continue
                for prop_name, prop_value in current_properties.items():
                    prop_type = Utils.get_value_as_string('type', prop_value)
                    if prop_type is not None and prop_type == 'array':
                        array_items = Utils.get_value_as_dict('items', prop_value)
                        any_of_types = Utils.get_value_as_list('anyOf', array_items)
                        if any_of_types is not None:
                            for any_of in any_of_types:
                                ref = Utils.get_value_as_string('$ref', any_of)
                                updated_ref = get_update_ref(ref)
                                if updated_ref is not None:
                                    any_of['$ref'] = updated_ref
                        else:
                            ref = Utils.get_value_as_string('$ref', array_items)
                            updated_ref = get_update_ref(ref)
                            if updated_ref is not None:
                                array_items['$ref'] = updated_ref
                    else:
                        ref = Utils.get_value_as_string('$ref', prop_value)
                        updated_ref = get_update_ref(ref)
                        if updated_ref is not None:
                            prop_value['$ref'] = updated_ref

            # clean-up definitions
            to_delete = []
            for name in definitions:
                if '__' in name:
                    to_delete.append(name)
            for name in to_delete:
                del definitions[name]

            # add updated refs
            for name in add_definitions:
                definitions[name] = add_definitions[name]

    def generate_json_schema(self, models: List[Type[BaseModel]]) -> str:
        """
        Create a top-level '_Master_' model with references to each of the actual models.
        Generate the schema for this model, which will include the schemas for all the
        nested models. Then clean up the schema.

        One weird thing we do is we temporarily override the 'extra' setting in models,
        changing it to 'forbid' UNLESS it was explicitly set to 'allow'. This prevents
        '[k: string]: any' from being added to every interface. This change is reverted
        once the schema has been generated.

        IDEA Modifications: Updated to fix duplicate anomalies in the generated JSON schema
        """
        model_extras = [getattr(m.Config, "extra", None) for m in models]

        try:
            for m in models:
                if getattr(m.Config, "extra", None) != Extra.allow:
                    m.Config.extra = Extra.forbid

            master_model = create_model(
                "_Master_", **{m.__name__: (m, ...) for m in models}
            )
            master_model.Config.extra = Extra.forbid
            master_model.Config.schema_extra = staticmethod(self.clean_schema)

            schema = json.loads(master_model.schema_json())

            self.fix_anomalies(schema)

            schema_definitions = Utils.get_value_as_dict('definitions', schema, {})

            for name, definition in schema_definitions.items():
                self.clean_schema(definition)

            return json.dumps(schema, indent=2)

        finally:
            for m, x in zip(models, model_extras):
                if x is not None:
                    m.Config.extra = x

    def generate_typescript_defs(self, modules: List[str], output: str, exclude: Set[str] = None, json2ts_cmd: str = "json2ts") -> None:
        """
        Convert the pydantic models in a python module into typescript interfaces.

        :param modules: python modules containing pydantic model definitions, ex: my_project.api.schemas
        :param output: file that the typescript definitions will be written to
        :param exclude: optional, a Set of names for pydantic models which should be omitted from the typescript output.
        :param json2ts_cmd: optional, the command that will execute json2ts. Use this if it's installed in a strange spot.
        """
        if not shutil.which(json2ts_cmd):
            raise Exception(
                "json2ts must be installed. Instructions can be found here: "
                "https://www.npmjs.com/package/json-schema-to-typescript"
            )

        idea.console.info("Finding pydantic models...")

        existing = set()
        models = set()
        for module in modules:
            extracted = self.extract_pydantic_models(self.import_module(module))
            for name, model in extracted:
                if name in existing:
                    continue
                existing.add(name)
                models.add(model)

        if exclude:
            models = [m for m in models if m.__name__ not in exclude]

        idea.console.info("Generating JSON schema from pydantic models...")

        schema = self.generate_json_schema(models)
        schema_dir = mkdtemp()
        schema_file_path = os.path.join(schema_dir, "schema.json")

        with open(schema_file_path, "w") as f:
            f.write(schema)

        idea.console.info("Converting JSON schema to typescript definitions...")

        banner_comment_items = ['/* tslint:disable */',
                                '/* eslint-disable */',
                                '/* This file is generated using IDEA invoke typings task. */',
                                '/* Do not modify this file manually. */',
                                '/**']
        for line in notice.COPYRIGHT_NOTICE.splitlines():
            banner_comment_items.append(f' * {line}')
        banner_comment_items.append(' */')

        banner_comment = "\n".join(banner_comment_items)
        os.system(
            f'{json2ts_cmd} -i {schema_file_path} -o {output} --bannerComment "{banner_comment}"'
        )
        shutil.rmtree(schema_dir)
        self.remove_master_model_from_output(output)

        idea.console.success(f"Saved typescript definitions to {output}.")

