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

__all__ = (
    'SocaInputParamCliOptions',
    'SocaUserInputParamExposeOptions',
    'SocaUserInputParamType',
    'SocaUserInputChoice',
    'SocaUserInputRange',
    'SocaUserInputCondition',
    'SocaUserInputHandlers',
    'SocaUserInputParamCondition',
    'SocaUserInputValidate',
    'SocaUserInputParamMetadata',
    'SocaInputParamValidationEntry',
    'SocaInputParamValidationResult',
    'SocaUserInputGroupMetadata',
    'SocaUserInputSectionReview',
    'SocaUserInputSectionMetadata',
    'SocaUserInputModuleMetadata',
    'SocaUserInputTag',
    'SocaInputParamSpec'
)

from ideadatamodel import SocaBaseModel
from ideadatamodel.model_utils import ModelUtils

from pydantic import Field
from typing import Optional, List, Union, Any, Dict
from enum import Enum


class SocaInputParamCliOptions(SocaBaseModel):
    long_name: Optional[str]
    short_name: Optional[str]
    required: Optional[str]
    help_text: Optional[str]


class SocaUserInputParamExposeOptions(SocaBaseModel):
    cli: Optional[SocaInputParamCliOptions]
    web_app: Optional[bool]


class SocaUserInputParamType(str, Enum):
    TEXT = 'text'
    PASSWORD = 'password'
    NEW_PASSWORD = 'new-password'
    PATH = 'path'
    CONFIRM = 'confirm'
    SELECT = 'select'
    RAW_SELECT = 'raw_select'
    CHECKBOX = 'checkbox'
    AUTOCOMPLETE = 'autocomplete'
    SELECT_OR_TEXT = 'select_or_text'
    CHOICES = 'choices'
    AUTO = 'auto'
    IMAGE_UPLOAD = 'image_upload'
    HEADING1 = 'heading1'
    HEADING2 = 'heading2'
    HEADING3 = 'heading3'
    HEADING4 = 'heading4'
    HEADING5 = 'heading5'
    HEADING6 = 'heading6'
    PARAGRAPH = 'paragraph'
    CODE = 'code'
    DATEPICKER = 'datepicker'

    def __str__(self):
        return self.value


class SocaUserInputChoice(SocaBaseModel):
    title: Optional[str]
    value: Optional[Any]
    disabled: Optional[bool]
    checked: Optional[bool]
    options: Optional[List['SocaUserInputChoice']]
    description: Optional[str]

    def __repr__(self):
        return self.value

    def __str__(self):
        return self.value


class SocaUserInputRange(SocaBaseModel):
    type_: Optional[str] = Field(alias='type')
    from_: Optional[List[Union[Any]]] = Field(alias='from')
    to: Optional[List[Union[Any]]]


class SocaUserInputCondition(SocaBaseModel):
    eq: Optional[Any]
    not_eq: Optional[Any]
    in_: Optional[Union[str, List[Any]]] = Field(alias='in')
    not_in: Optional[Union[str, List[Any]]]
    gt: Optional[Union[Any]]
    gte: Optional[Union[Any]]
    lt: Optional[Union[Any]]
    lte: Optional[Union[Any]]
    min: Optional[Union[Any]]
    max: Optional[Union[Any]]
    range: Optional[SocaUserInputRange]
    not_in_range: Optional[SocaUserInputRange]
    regex: Optional[str]
    not_regex: Optional[str]
    exact: Optional[str]
    starts_with: Optional[str]
    ends_with: Optional[str]
    empty: Optional[bool]
    not_empty: Optional[bool]
    contains: Optional[Any]
    not_contains: Optional[Any]


class SocaUserInputHandlers(SocaBaseModel):
    class_: Optional[str] = Field(alias='class')
    choices: Optional[str]
    default: Optional[str]
    validate_: Optional[str] = Field(alias='validate')
    autocomplete: Optional[str]
    filter: Optional[str]


class SocaUserInputParamCondition(SocaUserInputCondition):
    param: Optional[str]
    and_: Optional[List['SocaUserInputParamCondition']] = Field(alias='and')
    or_: Optional[List['SocaUserInputParamCondition']] = Field(alias='or')


SocaUserInputParamCondition.update_forward_refs()


class SocaUserInputValidate(SocaUserInputCondition):
    required: Optional[bool]
    auto_prefix: Optional[str]


class SocaUserInputParamMetadata(SocaBaseModel):
    name: Optional[str]
    template: Optional[str]
    title: Optional[str]
    optional: Optional[bool]
    prompt: Optional[bool]
    description: Optional[str]
    description2: Optional[str]
    help_text: Optional[str]
    param_type: Optional[SocaUserInputParamType]
    data_type: Optional[str]
    custom_type: Optional[str]
    multiple: Optional[bool]
    multiline: Optional[bool]
    auto_enter: Optional[bool]
    auto_focus: Optional[bool]
    unique: Optional[bool]
    default: Optional[Union[List, Any]]
    readonly: Optional[bool]
    validate_: Optional[SocaUserInputValidate] = Field(alias='validate')
    choices: Optional[List[SocaUserInputChoice]]
    choices_meta: Optional[Dict[str, Any]]
    dynamic_choices: Optional[bool]
    choices_empty_label: Optional[str]
    refreshable: Optional[bool]
    ignore_case: Optional[bool]
    match_middle: Optional[bool]
    tag: Optional[str]
    export: Optional[bool]
    when: Optional[SocaUserInputParamCondition]
    expose: Optional[SocaUserInputParamExposeOptions]
    markdown: Optional[str]
    developer_notes: Optional[str]
    custom: Optional[Dict]

    @property
    def is_required(self) -> bool:
        validate = self.validate_
        if ModelUtils.is_empty(validate):
            return False
        return ModelUtils.get_as_bool(validate.required, False)

    @property
    def is_prompt(self) -> bool:
        return ModelUtils.get_as_bool(self.prompt, True)

    @property
    def is_multiple(self) -> bool:
        return ModelUtils.get_as_bool(self.multiple, False)

    @property
    def is_export(self) -> bool:
        return ModelUtils.get_as_bool(self.export, True)

    @property
    def is_cli_exposed(self) -> bool:
        if self.expose is None:
            return False
        if self.expose.cli is None:
            return False
        return not ModelUtils.is_empty(self.expose.cli.long_name)

    @property
    def cli_arg_name(self) -> Optional[str]:
        if not self.is_cli_exposed:
            return None
        return self.expose.cli.long_name.replace('--', '', 1).replace('-', '_')

    @property
    def is_cli_arg_required(self) -> bool:
        if not self.is_cli_exposed:
            return False
        return ModelUtils.get_as_bool(self.expose.cli.required, False)

    @property
    def cli_arg_format(self) -> Optional[str]:
        if not self.is_cli_exposed:
            return None
        cli_options = self.expose.cli
        long_name = cli_options.long_name
        short_name = cli_options.short_name
        s = ''
        if long_name:
            s += long_name
        if short_name:
            s += f'/{short_name}'
        return s

    @property
    def cli_help(self) -> str:
        help_text = None
        if self.is_cli_exposed:
            help_text = self.expose.cli.help_text
        if ModelUtils.is_empty(help_text):
            help_text = self.description
        if ModelUtils.is_empty(help_text):
            help_text = self.title

        if help_text.endswith(':'):
            help_text = help_text[:-1]

        help_text = self.try_convert_select_to_enter(help_text)

        return help_text

    @staticmethod
    def try_convert_select_to_enter(message: str) -> str:
        """
        on a best effort basis - lazy implementation
        devs can set install_params.yml -> (param) -> expose.cli.help_text to set the exact text.
        also called for description2 use case from SocaQuestion
        """
        token = message.strip()
        if token.startswith(('Select the', 'Select an', 'Select a', 'Choose ')):
            token = token.replace('Select the', 'Enter the', 1)
            token = token.replace('Select an', 'Enter a', 1)
            token = token.replace('Select a', 'Enter a', 1)
            token = token.replace('Choose ', 'Enter ', 1)
            token = token.replace('Choose the', 'Enter the', 1)
        return token

    @staticmethod
    def get_choice_value(choice: Union[str, SocaUserInputChoice]) -> Any:
        if isinstance(choice, str):
            return choice
        else:
            return choice.value

    def get_first_choice(self) -> Optional[Any]:
        choices = ModelUtils.get_as_list(self.choices, [])
        if len(choices) == 0:
            return None
        return self.get_choice_value(choices[0])

    def get_default(self) -> Optional[Any]:

        multiple = ModelUtils.get_as_bool(self.multiple, False)
        if self.data_type == 'bool':
            if multiple:
                default = ModelUtils.get_as_bool_list(self.default)
            else:
                default = self.default
                if default == '$first':
                    default = self.get_first_choice()
                default = ModelUtils.get_as_bool(default)
        elif self.data_type == 'int':
            if multiple:
                default = ModelUtils.get_as_int_list(self.default)
            else:
                default = self.default
                if default == '$first':
                    default = self.get_first_choice()
                default = ModelUtils.get_as_int(default)
        elif self.data_type == 'float':
            if multiple:
                default = ModelUtils.get_as_float_list(self.default)
            else:
                default = self.default
                if default == '$first':
                    default = self.get_first_choice()
                default = ModelUtils.get_as_float(default)
        else:
            if multiple:
                default = ModelUtils.get_as_string_list(self.default)
            else:
                default = self.default
                if default == '$first':
                    default = self.get_first_choice()

        if multiple:
            first = ModelUtils.get_first(self.default)
            if first is not None:
                if first == '$all':
                    default = []
                    choices = ModelUtils.get_as_list(self.choices, [])
                    for choice in choices:
                        default.append(self.get_choice_value(choice))
                if first == '$first':
                    default = self.get_first_choice()
                    if default is not None:
                        default = [default]

        return default


class SocaInputParamValidationEntry(SocaBaseModel):
    name: Optional[str]
    section: Optional[str]
    message: Optional[str]
    meta: Optional[SocaUserInputParamMetadata]


class SocaInputParamValidationResult(SocaBaseModel):
    entries: Optional[List[SocaInputParamValidationEntry]]

    def __bool__(self):
        return self.is_valid

    @property
    def is_valid(self) -> bool:
        return len(self.entries) == 0


class SocaUserInputGroupMetadata(SocaBaseModel):
    name: Optional[str]
    module: Optional[str]
    section: Optional[str]
    title: Optional[str]
    description: Optional[str]
    params: Optional[List[SocaUserInputParamMetadata]]


class SocaUserInputSectionReview(SocaBaseModel):
    prompt: Optional[str]


class SocaUserInputSectionMetadata(SocaBaseModel):
    name: Optional[str]
    module: Optional[str]
    title: Optional[str]
    description: Optional[str]
    required: Optional[bool]
    review: Optional[SocaUserInputSectionReview]
    params: Optional[List[SocaUserInputParamMetadata]]
    groups: Optional[List[SocaUserInputGroupMetadata]]
    markdown: Optional[str]

    @property
    def is_required(self) -> bool:
        return ModelUtils.get_as_bool(self.required, False)


class SocaUserInputModuleMetadata(SocaBaseModel):
    name: Optional[str]
    title: Optional[str]
    description: Optional[str]
    sections: Optional[List[SocaUserInputSectionMetadata]]
    markdown: Optional[str]


class SocaUserInputTag(SocaBaseModel):
    name: Optional[str]
    title: Optional[str]
    description: Optional[str]
    markdown: Optional[str]
    unicode: Optional[str]
    ascii: Optional[str]
    icon: Optional[str]


class SocaInputParamSpec(SocaBaseModel):
    name: Optional[str]
    version: Optional[str]
    tags: Optional[List[SocaUserInputTag]]
    modules: Optional[List[SocaUserInputModuleMetadata]]
    params: Optional[List[SocaUserInputParamMetadata]]
