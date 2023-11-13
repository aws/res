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

from ideasdk.utils import Utils
from ideadatamodel import exceptions, errorcodes, constants
from ideasdk.context import SocaContext

from ideadatamodel.user_input import (
    SocaInputParamSpec, SocaUserInputParamMetadata, SocaUserInputParamType, SocaUserInputChoice,
    SocaUserInputTag, SocaUserInputSectionMetadata, SocaUserInputModuleMetadata,
    SocaInputParamValidationResult,
    SocaInputParamValidationEntry, SocaUserInputParamCondition
)

from abc import ABC
from typing import Optional, Dict, List, Union, Type, Callable, Any, Generic, TypeVar
from questionary import unsafe_prompt, Style, Validator, Choice, Separator, ValidationError
from rich.console import Console
from rich.style import Style as RichStyle
import queue
from collections import OrderedDict
import os
import yaml
from pyhocon import ConfigFactory, ConfigTree, tool
from prompt_toolkit.document import Document
import re

T = TypeVar('T')

DEFAULT_SELECT_STYLE = Style([("text", "fg:#8a850b")])
DEFAULT_COMPLETE_STYLE = 'MULTI_COLUMN'
DEFAULT_PATH_COMPLETE_STYLE = DEFAULT_COMPLETE_STYLE
DEFAULT_UNICODE = '?'
DEFAULT_ASCII = '?'

INTERRUPT_OPTION_EXIT = 'exit'
INTERRUPT_OPTION_RESTART_MODULE = 'restart-module'
INTERRUPT_OPTION_RESTART_SECTION = 'restart-section'
INTERRUPT_OPTION_CANCEL = 'cancel'

SocaPromptDefaultFactory = Optional[Callable[[bool], T]]
SocaUserInputDefaultType = Union[Optional[T], SocaPromptDefaultFactory]
SocaUserInputChoicesType = Union[Optional[List[SocaUserInputChoice]], Callable[..., List[SocaUserInputChoice]]]

console = Console()


class SocaUserInputArgs:
    def __init__(self, context: SocaContext,
                 initial_config: Optional[Dict] = None,
                 cli_args: Optional[Dict] = None,
                 file: str = None,
                 file_format: str = 'yaml',
                 param_registry: 'SocaUserInputParamRegistry' = None,
                 debug: bool = False):

        self.context = context

        self._cli_args = Utils.get_as_dict(cli_args, {})
        self._file = file
        self._file_format = file_format
        self._debug = debug

        self._initial_config = Utils.get_as_dict(initial_config, {})
        self._config_tree: Optional[ConfigTree] = None
        self._param_registry = param_registry
        self._validation_result = SocaInputParamValidationResult(entries=[])

        self.initialize()

    # Begin: Private Methods

    def _arg_to_param(self, arg_name: str) -> str:
        param = self._param_registry.arg_to_param(arg_name)
        return param.name

    def _param_to_arg(self, name: str) -> Optional[str]:
        param = self._param_registry.get_param(name)
        return param.cli_arg_name

    def _is_cli_arg_defined(self, arg_name: str) -> bool:
        try:
            self.param_registry.arg_to_param(arg_name)
            return True
        except exceptions.SocaException as e:
            if e.error_code == errorcodes.INPUT_PARAM_NOT_DEFINED:
                return False
            else:
                raise e

    def _get_strict_type_value(self, param_name: str, value: Optional[Any]) -> Any:
        if value is None:
            return None
        raise_exc = not param_name.startswith('_')
        meta = self.get_meta(param_name, raise_exc=raise_exc)
        if meta is None:
            return value
        data_type = meta.data_type
        multiple = Utils.get_as_bool(meta.multiple, False)
        if data_type == 'str':
            if multiple:
                return Utils.get_as_string_list(value)
            else:
                return Utils.get_as_string(value)
        elif data_type == 'int':
            if multiple:
                return Utils.get_as_int_list(value)
            else:
                return Utils.get_as_int(value)
        elif data_type == 'float':
            if multiple:
                return Utils.get_as_float_list(value)
            else:
                return Utils.get_as_string(value)
        elif data_type == 'bool':
            if multiple:
                return Utils.get_as_bool_list(value)
            else:
                return Utils.get_as_bool(value)

        return value

    def _set(self, key: str, value: Optional[Any], append=False, type_check=True):
        if type_check:
            value_ = self._get_strict_type_value(param_name=key, value=value)
        else:
            value_ = value
        self._config_tree.put(key, value_, append=append)

    def _merge(self, config: Dict):
        config_tree = ConfigFactory.from_dict(config)
        self._config_tree = config_tree.with_fallback(self._config_tree)

    # Begin Public Methods

    def initialize(self):
        self.sanitize_cli_args()
        self.validate_cli_args()

        self._config_tree = ConfigFactory.from_dict(self._initial_config)

        for arg_name, value in self._cli_args.items():
            if value is None:
                continue
            param_name = self._arg_to_param(arg_name)

            # if initial config has a value, do not apply changes from cli args.
            # this handles case where cli defaults should not override initial config
            existing_value = self.get(param_name)
            if existing_value is None:
                self.set(param_name, value, initial=True)

    def sanitize_cli_args(self):
        sanitized = {}
        # sanitize cli values from click
        for arg_name in self._cli_args:
            value = self._cli_args.get(arg_name)

            if Utils.is_empty(value):
                continue

            if not self._is_cli_arg_defined(arg_name):
                continue

                # convert tuples to list.
            if isinstance(value, tuple):
                value = list(value)

            param_name = self._arg_to_param(arg_name)
            param_meta = self.get_meta(param_name)

            # auto-prefix
            if Utils.is_not_empty(param_meta.validate_) and Utils.is_not_empty(param_meta.validate_.auto_prefix):
                value = Utils.get_as_string(value)
                prefix = param_meta.validate_.auto_prefix
                if Utils.is_not_empty(value) and not value.startswith(prefix):
                    value = f'{prefix}{value}'

            sanitized[arg_name] = value
        self._cli_args = sanitized

    def validate_cli_args(self):
        """
        child class can override this method to extend validation functionality
        :return:
        """
        pass

    def add_validation_entry(self, message: str,
                             param_name: Optional[str] = None,
                             section: Optional[str] = None):
        # if same message is already added, return.
        for entry in self._validation_result.entries:
            if message == entry.message:
                return

        meta = None

        name = None
        if param_name is not None:
            meta = self.param_registry.get_param(param_name)
            name = param_name

        self._validation_result.entries.append(SocaInputParamValidationEntry(
            name=name,
            section=section,
            message=message,
            meta=meta
        ))

    def validation_fail(self, message: str = None) -> exceptions.SocaException:
        return exceptions.soca_exception(
            error_code=errorcodes.INSTALLER_PARAM_VALIDATION_FAILED,
            message=message,
            ref=self._validation_result
        )

    def get_meta(self, param_name: str, raise_exc: bool = True) -> SocaUserInputParamMetadata:
        return self.param_registry.get_param(name=param_name, raise_exc=raise_exc)

    def get(self, param_name: str) -> Optional[Any]:
        value = self._config_tree.get(param_name, default=None)
        if value is None:
            return None
        return self._get_strict_type_value(param_name=param_name, value=value)

    def set(self, param_name: str, value: Optional[Any], append=False, initial=False):
        self._set(param_name, value, append=append, type_check=False)

    def cli_args(self):
        return self._cli_args

    def initial_config(self):
        return self._initial_config

    def as_dict(self) -> Dict:
        return self._config_tree.as_plain_ordered_dict()

    def as_yaml(self) -> str:
        return tool.HOCONConverter().to_yaml(self._config_tree)

    def as_json(self) -> str:
        return tool.HOCONConverter().to_json(self._config_tree)

    # Begin Public Properties

    @property
    def param_registry(self) -> 'SocaUserInputParamRegistry':
        return self._param_registry

    @property
    def is_debug(self) -> bool:
        return Utils.get_as_bool(self._debug, False)

    def build(self) -> Dict:
        return self._config_tree.as_plain_ordered_dict()


class SocaUserInputParamRegistry:
    def __init__(self, context: SocaContext, file: str = None, spec: Optional[SocaInputParamSpec] = None):
        self._context = context

        if file is None and spec is None:
            raise exceptions.invalid_params('either file or spec is required')

        self._file = file
        self._spec: Optional[SocaInputParamSpec] = spec

        self._is_initialized = False
        self._params: OrderedDict[str, SocaUserInputParamMetadata] = OrderedDict()
        self._cli_args_inverse_index: Optional[Dict[str, SocaUserInputParamMetadata]] = {}
        self._tags: Optional[Dict[str, SocaUserInputTag]] = {}

    # Begin: Private Methods

    def _process_tags(self):
        if self._spec.tags is None:
            return
        for tag in self._spec.tags:
            self._tags[tag.name] = tag

    def _register_param(self, param: SocaUserInputParamMetadata):
        if param is None:
            return
        self._params[param.name] = param
        self._cli_args_inverse_index[param.cli_arg_name] = param

    def _process_params(self):
        if self._spec.params is None:
            return
        for param in self._spec.params:
            self._register_param(param)

    def _get_template_param(self, name: str, template_param: str) -> Optional[SocaUserInputParamMetadata]:
        if template_param not in self._params:
            return None
        template = self._params[template_param]
        template = template.copy(deep=True)
        template.template = None
        template.name = name
        template.title = name
        return template

    def _process_modules(self):
        if Utils.is_empty(self._spec.modules):
            return

        for module in self._spec.modules:
            if Utils.is_empty(module.sections):
                continue
            for section in module.sections:
                section.module = module.name
                if Utils.is_not_empty(section.params):
                    for section_param in section.params:
                        if Utils.is_empty(section_param.template):
                            continue
                        template_param = self._get_template_param(section_param.name, section_param.template)
                        self._register_param(template_param)

                if Utils.is_empty(section.groups):
                    continue

                for group in section.groups:
                    group.module = module.name
                    group.section = section.name

                    if Utils.is_not_empty(group.params):
                        for group_param in group.params:
                            if Utils.is_empty(group_param.template):
                                continue
                            template_param = self._get_template_param(group_param.name, group_param.template)
                            self._register_param(template_param)

    def load_input_param_spec(self):
        if Utils.is_not_empty(self._file):
            if not os.path.isfile(self._file):
                raise exceptions.soca_exception(
                    error_code=errorcodes.INPUT_PARAM_SPEC_NOT_FOUND,
                    message=f'InputParams .yml spec file not found: {self._file}'
                )
            with open(self._file, 'r') as f:
                content = f.read()

            docs = yaml.safe_load(content)
            spec = docs.get('SocaInputParamSpec')
            self._spec = SocaInputParamSpec(**spec)

        self._process_tags()
        self._process_params()
        self._process_modules()

    # Begin: Public Methods

    def _check_initialized(self):
        if not self._is_initialized:
            self.load_input_param_spec()
            self._is_initialized = True

    @property
    def version(self) -> str:
        self._check_initialized()
        return self._spec.version

    def get_unicode(self, tag_name: str) -> Optional[str]:
        self._check_initialized()
        if self._tags is None:
            return DEFAULT_UNICODE
        tag = self._tags.get(tag_name, None)
        if tag is None:
            return DEFAULT_UNICODE
        return tag.unicode

    def get_ascii(self, tag_name: str) -> Optional[str]:
        self._check_initialized()
        if self._tags is None:
            return DEFAULT_ASCII
        tag = self._tags.get(tag_name, None)
        if tag is None:
            return DEFAULT_ASCII
        return tag.ascii

    def get_param(self, name: str, raise_exc=True) -> Optional[SocaUserInputParamMetadata]:
        self._check_initialized()

        param = self._params.get(name, None)
        if param is None:
            if raise_exc:
                raise exceptions.soca_exception(
                    error_code=errorcodes.INPUT_PARAM_NOT_DEFINED,
                    message=f'InstallParam: {name} not found in InstallParamRegistry'
                )
            return None

        return param.copy(deep=True)

    def arg_to_param(self, arg_name: str) -> SocaUserInputParamMetadata:
        self._check_initialized()
        param = self._cli_args_inverse_index.get(arg_name, None)
        if param is None:
            raise exceptions.soca_exception(
                error_code=errorcodes.INPUT_PARAM_NOT_DEFINED,
                message=f'InstallArg: {arg_name} not found in InstallParamRegistry'
            )
        return param.copy(deep=True)

    def get_params(self, module: str = None, section: str = None, group: str = None, all_=True) -> List[SocaUserInputParamMetadata]:
        self._check_initialized()

        result = []
        if Utils.is_empty(module) and all_:
            for key in self._params:
                result.append(self._params[key])
            return result

        module_info = self.get_module(module)
        if module_info is None:
            return result

        if Utils.is_empty(module_info.sections):
            return result

        def merge(to: SocaUserInputParamMetadata, from_: SocaUserInputParamMetadata) -> SocaUserInputParamMetadata:
            to_dict = to.copy(deep=True).dict(exclude_unset=True, exclude_none=True, exclude_defaults=True, by_alias=True)
            from_dict = from_.dict(by_alias=True)
            for key in from_dict:
                value = from_dict[key]
                if key not in to_dict:
                    to_dict[key] = value
            return SocaUserInputParamMetadata(**to_dict)

        for section_info in module_info.sections:

            if Utils.is_not_empty(section) and section != section_info.name:
                continue

            if Utils.is_empty(group) or Utils.is_not_empty(group) and all_:
                if Utils.is_not_empty(section_info.params):
                    for section_param in section_info.params:
                        param_info = self.get_param(section_param.name)
                        result.append(merge(section_param, param_info))

            if all_ or Utils.is_not_empty(group):
                if Utils.is_not_empty(section_info.groups):
                    for group_info in section_info.groups:

                        if Utils.is_not_empty(group) and group != group_info.name:
                            continue

                        if Utils.is_not_empty(group_info.params):
                            for group_param in group_info.params:
                                param_info = self.get_param(group_param.name)
                                result.append(merge(group_param, param_info))

        return result

    def get_section(self, module: str, section: str) -> SocaUserInputSectionMetadata:

        module_ = self.get_module(module)

        if Utils.is_empty(module_.sections):
            raise exceptions.soca_exception(
                error_code=errorcodes.GENERAL_ERROR,
                message=f'sections not found for module: {module_.name} in {self._file}'
            )

        for section_ in module_.sections:
            if section_.name != section:
                continue
            return section_.copy(deep=True)

        raise exceptions.soca_exception(
            error_code=errorcodes.GENERAL_ERROR,
            message=f'section: {section} not found for module: {module} in {self._file}'
        )

    def get_module(self, module: str, deep_copy: bool = True) -> SocaUserInputModuleMetadata:
        self._check_initialized()

        if Utils.is_empty(self._spec.modules):
            raise exceptions.soca_exception(
                error_code=errorcodes.GENERAL_ERROR,
                message=f'modules not found in {self._file}'
            )

        for module_ in self._spec.modules:
            if module_.name != module:
                continue
            return module_.copy(deep=deep_copy)

        raise exceptions.soca_exception(
            error_code=errorcodes.GENERAL_ERROR,
            message=f'module: {module} not found in {self._file}'
        )


class SocaPromptRegistry:
    def __init__(self, context: SocaContext, param_spec: SocaUserInputParamRegistry):
        self.context = context
        self.spec = param_spec
        self.questions = {}

    def add(self, prompt: 'SocaPrompt'):
        self.questions.setdefault(prompt.name, prompt)

    def get(self, param_name: str) -> 'SocaPrompt':
        prompt = self.questions.get(param_name, None)
        if prompt is None:
            raise exceptions.soca_exception(
                error_code=errorcodes.INPUT_PROMPT_NOT_FOUND,
                message=f'Prompt not found for param name: {param_name}'
            )
        return prompt


class SocaPromptBaseClass(ABC):
    pass


class SocaPrompt(SocaPromptBaseClass, Generic[T]):
    def __init__(self, context: SocaContext,
                 args: SocaUserInputArgs,
                 param: SocaUserInputParamMetadata,
                 default: SocaUserInputDefaultType = None,
                 choices: SocaUserInputChoicesType = None,
                 registry: SocaPromptRegistry = None):
        self.context = context
        self.param = param

        self._args = args

        self._default_factory: SocaPromptDefaultFactory = None
        self._default: Optional[T] = None

        if default is not None:
            if isinstance(default, Callable):
                self._default_factory = default
            else:
                self._default = default

        self._choices: Optional[List[SocaUserInputChoice]] = None
        self._choices_factory: Optional[Callable[..., List[SocaUserInputChoice]]] = None
        if choices is not None:
            if isinstance(choices, Callable):
                self._choices_factory = choices
            else:
                self._choices = choices

        self._registry: Optional[SocaPromptRegistry] = registry
        if self._registry:
            self._registry.add(self)

    @property
    def args(self) -> SocaUserInputArgs:
        return self._args

    @property
    def name(self) -> str:
        return self.param.name

    @property
    def title(self) -> str:
        return self.param.title

    @property
    def prompt(self) -> bool:
        return self.param.is_prompt

    @property
    def description(self) -> Optional[str]:
        return self.param.description

    @property
    def description2(self) -> Optional[str]:
        return self.param.description2

    @property
    def help_text(self) -> Optional[str]:
        return self.param.help_text

    def default(self, reset: bool = False) -> Optional[T]:
        if self._default_factory is not None:
            self._default = self._default_factory(reset)

        if self._default is not None:
            if self.multiple:
                if len(self._default) > 0:
                    return self._default
            else:
                return self._default

        param_default = self.param.get_default()
        if param_default is None and Utils.is_not_empty(self.param.default):
            meta_default = self.param.default
            if meta_default in ('$first', '$all'):
                choices = self.get_choices()
                if len(choices) > 0:
                    if meta_default == '$first':
                        param_default = Utils.get_first(choices).value
                        if self.multiple:
                            param_default = [param_default]
                    if meta_default == '$all':
                        param_default = []
                        for choice in choices:
                            param_default.append(choice.value)
        return param_default

    @property
    def param_type(self) -> SocaUserInputParamType:
        if self.param.param_type is None:
            return SocaUserInputParamType.TEXT
        return self.param.param_type

    @property
    def data_type(self) -> str:
        return Utils.get_as_string(self.param.data_type, 'str')

    @property
    def multiple(self) -> bool:
        return Utils.get_as_bool(self.param.multiple, False)

    @property
    def multiline(self) -> bool:
        return Utils.get_as_bool(self.param.multiline, False)

    @property
    def auto_enter(self) -> bool:
        return Utils.get_as_bool(self.param.auto_enter, True)

    @property
    def tag(self) -> Optional[str]:
        return self.param.tag

    @property
    def unicode_icon(self) -> Optional[str]:
        if self._registry:
            return self._registry.spec.get_ascii(self.tag)
        return None

    def get_choices(self, refresh: bool = False) -> List[SocaUserInputChoice]:
        if self._choices is not None:
            return self._choices

        if self._choices_factory is not None:
            self._choices = self._choices_factory()
            return self._choices

        choices = []
        available_choices = Utils.get_as_list(self.param.choices, [])
        for choice in available_choices:

            if isinstance(choice, str):
                choice_ = SocaUserInputChoice(
                    title=f'{choice}',
                    value=f'{choice}'
                )
            else:
                choice_: SocaUserInputChoice = choice

            if Utils.is_not_empty(choice_.title) and Utils.is_empty(choice_.value):
                choice_.value = choice_.title
            if Utils.is_not_empty(choice_.value) and Utils.is_empty(choice_.title):
                choice_.title = choice_.value

            choices.append(choice_)

        return choices

    @property
    def when(self) -> Optional[SocaUserInputParamCondition]:
        return self.param.when

    def should_show_prompt(self, when: Optional[SocaUserInputParamCondition]) -> bool:
        """
        Evaluate the given when clause
        :param when:
        :return: True, if prompt 'should' be shown, False otherwise
        """

        if when is None:
            return True

        if Utils.are_empty(when.param, when.and_, when.or_):
            return True

        if Utils.is_not_empty(when.param):

            param_value = self.args.get(when.param)

            # todo - between, min, max

            if Utils.is_true(when.empty) and Utils.is_empty(param_value):
                return True
            elif Utils.is_true(when.not_empty) and Utils.is_not_empty(param_value):
                return True
            elif Utils.is_not_empty(when.eq) and param_value == when.eq:
                return True
            elif Utils.is_not_empty(when.not_eq) and param_value != when.not_eq:
                return True
            elif Utils.is_not_empty(when.gt) and param_value > when.gt:
                return True
            elif Utils.is_not_empty(when.gte) and param_value >= when.gte:
                return True
            elif Utils.is_not_empty(when.lt) and param_value < when.lt:
                return True
            elif Utils.is_not_empty(when.lte) and param_value <= when.lte:
                return True
            elif Utils.is_not_empty(when.in_) and param_value in when.in_:
                return True
            elif Utils.is_not_empty(when.contains) and param_value is not None and when.contains in param_value:
                return True
            elif Utils.is_not_empty(when.not_contains) and param_value is not None and when.not_contains not in param_value:
                return True
            elif Utils.is_not_empty(when.not_in) and param_value not in when.not_in:
                return True

            return False

        if Utils.is_not_empty(when.and_):
            for condition in when.and_:
                if not self.should_show_prompt(condition):
                    return False
            return True

        if Utils.is_not_empty(when.or_):
            for condition in when.or_:
                if self.should_show_prompt(condition):
                    return True
            return False

        return True

    def can_skip(self, review_mode: bool = False) -> bool:

        when = self.when

        if review_mode:

            return True

        else:

            # we can not skip, if prompt should be shown
            if self.should_show_prompt(when):
                return False

            return True

    @property
    def is_required(self) -> bool:
        return self.param.is_required

    def ask(self, review_mode: bool = False) -> Optional[T]:
        question = self.build(review_mode)
        if question is None:
            return None
        return self._ask(question)

    def get_prompt(self, message: str = None) -> str:
        if message is None:
            message = self.prompt
        if message is None:
            return self.title
        return f'[{self.title}] {message}'

    def build(self, review_mode: bool = False) -> Optional[Union[List[Dict], Dict]]:

        if self.can_skip(review_mode):
            return None

        param_type = self.param_type

        questions = []
        num_choices = 0
        default = self.default()

        def common() -> Dict:
            help_text = self.help_text
            if help_text is not None:
                help_text = f'({help_text})'

            return {
                'type': str(param_type),
                'name': self.name,
                'default': default,
                'message': self.get_prompt(self.description),
                'filter': self.get_filter(),
                'qmark': self.unicode_icon,
                'instruction': help_text
            }

        def eval_select_or_text(result) -> bool:
            return result.get(self.name) == constants.SELECT_CHOICE_OTHER

        if param_type in (SocaUserInputParamType.SELECT,
                          SocaUserInputParamType.RAW_SELECT,
                          SocaUserInputParamType.SELECT_OR_TEXT):
            choices = self.get_choices()
            choices_ = []
            default_choice = None
            for choice in choices:
                choice_ = Choice(
                    title=choice.title,
                    value=choice.value,
                    disabled=choice.disabled,
                    checked=choice.checked
                )
                if choice.value == default:
                    default_choice = choice_
                choices_.append(choice_)

            num_choices = len(choices_)

            param_type_ = param_type
            if param_type_ == SocaUserInputParamType.SELECT_OR_TEXT:
                if num_choices > 0:
                    param_type_ = SocaUserInputParamType.SELECT
                    choices_.append(Separator())
                    choices_.append(Choice(
                        title=constants.SELECT_CHOICE_OTHER,
                        value=constants.SELECT_CHOICE_OTHER
                    ))

            if num_choices > 0:
                questions.append({**common(), **{
                    'type': str(param_type_),
                    'choices': choices_,
                    'default': default_choice
                }})
            else:
                param_type = SocaUserInputParamType.TEXT

        if param_type in (SocaUserInputParamType.TEXT,
                          SocaUserInputParamType.SELECT_OR_TEXT):
            override = {
                'validate': self.get_validator(),
                'multiline': self.multiline
            }

            if param_type == SocaUserInputParamType.SELECT_OR_TEXT:
                if self.description2:
                    message = self.get_prompt(self.description2)
                else:
                    prompt = self.param.try_convert_select_to_enter(self.description)
                    message = self.get_prompt(prompt)

                override['type'] = str(SocaUserInputParamType.TEXT)
                override['message'] = message
                if num_choices > 0:
                    override['when'] = eval_select_or_text

            questions.append({**common(), **override})

        override = None
        if param_type == SocaUserInputParamType.PASSWORD:
            override = {
                'validate': self.get_validator()
            }
        elif param_type == SocaUserInputParamType.PATH:
            override = {
                'validate': self.get_validator()
            }
        elif param_type == SocaUserInputParamType.CONFIRM:
            override = {
                'type': 'confirm',
                'auto_enter': self.auto_enter
            }
        elif param_type == SocaUserInputParamType.CHECKBOX:
            choices = self.get_choices()

            choices_ = []
            defaults = Utils.get_as_list(self.default(), [])

            for choice in choices:
                choice_ = Choice(
                    title=choice.title,
                    value=choice.value,
                    disabled=choice.disabled,
                    checked=choice.value in defaults
                )
                choices_.append(choice_)
            override = {
                'choices': choices_,
                'validate': self.get_validator()
            }
        elif param_type == SocaUserInputParamType.AUTOCOMPLETE:
            choices = self.get_choices()
            choices_ = []
            for choice in choices:
                value = choice.title
                if Utils.is_empty(value):
                    value = str(choice.value)
                if Utils.is_empty(value):
                    continue
                choices_.append(value)

            override = {
                'choices': choices_,
                'default': default,
                'validate': self.get_validator()
            }

        if len(questions) > 0:
            return questions

        if override is None:
            return None

        questions.append({**common(), **override})
        return questions

    def _ask(self, question: Optional[Union[List[Dict], Dict]]) -> Optional[T]:
        questions = []
        try:
            if question is None:
                return None

            if isinstance(question, List):
                questions += question
            else:
                questions += [question]

            for question in questions:
                question_type = Utils.get_value_as_string('type', question)

                if 'qmark' in question:
                    qmark = question['qmark']
                    if qmark != '?':
                        question['qmark'] = f'{qmark}'

                if 'filter' not in question:
                    question['filter'] = self.get_filter()

                if 'name' not in question:
                    question['name'] = self.name

                if question_type == 'select' and 'style' not in question:
                    question['style'] = DEFAULT_SELECT_STYLE

                if question_type == 'checkbox':
                    # checkbox defaults are handled using choice.checked
                    del question['default']

                if 'instruction' in question:
                    if question_type in ('path', 'confirm', 'checkbox'):
                        # instruction is not supported by questionary for: path, confirm
                        message = question['message']
                        instruction = Utils.get_value_as_string('instruction', question)
                        if not Utils.is_empty(instruction):
                            message += f' {instruction}'
                            question['message'] = message
                        del question['instruction']

                if question_type == 'text' and Utils.get_value_as_bool('multiline', question, False):
                    instruction = Utils.get_value_as_string('instruction', question)
                    exit_note = 'Alt+Enter to exit'
                    if Utils.is_empty(instruction):
                        message = f'({exit_note})'
                    else:
                        if instruction.startswith('(') and instruction.endswith(')'):
                            message = instruction[1:-1]
                        else:
                            message = instruction
                        message = f'({message} | ${exit_note})'
                    question['instruction'] = message

                if question_type == 'path' and 'complete_style' not in question:
                    question['complete_style'] = DEFAULT_PATH_COMPLETE_STYLE

                if question_type in ('text', 'password', 'path') and 'default' in question:
                    default_val = question.get('default')
                    if default_val is None:
                        question['default'] = ''
                    elif not isinstance(default_val, str):
                        if isinstance(default_val, list):
                            entries = default_val
                            default_values = ''
                            for entry in entries:
                                default_values = f'{default_values},{entry}'
                            question['default'] = default_values.strip(',')
                        else:
                            question['default'] = str(default_val)

            result = unsafe_prompt(questions=questions)
            return Utils.get_any_value(self.name, result)

        except KeyboardInterrupt:
            raise exceptions.soca_exception(
                error_code=errorcodes.USER_INPUT_FLOW_INTERRUPT,
                message='',
                ref=self
            )
        except Exception as e:
            if isinstance(e, exceptions.SocaException):
                raise e
            else:
                question_debug_str = ''
                for question in questions:
                    question_name = Utils.get_value_as_string('name', question)
                    question_type = Utils.get_value_as_string('type', question)
                    question_debug_str = f'Name: {question_name}, Type: {question_type}'
                    break

                raise exceptions.soca_exception(
                    error_code=errorcodes.GENERAL_ERROR,
                    message=f'Unhandled exception occurred while processing the question: {question_debug_str}',
                    ref=e
                )

    def get_validator(self) -> Optional[Union[Type[Validator], Callable]]:

        if self.param_type == SocaUserInputParamType.CHECKBOX:
            def validate(values):
                try:
                    self.validate(value=values)
                    return True
                except exceptions.SocaException as e:
                    if e.error_code == errorcodes.VALIDATION_FAILED:
                        return e.message
                    else:
                        raise e

            return validate

        else:

            class ParamValidator(Validator):
                def validate(self_, document: Document):  # noqa
                    try:
                        self.validate(value=document.text)
                    except exceptions.SocaException as e:
                        if e.error_code == errorcodes.VALIDATION_FAILED:
                            raise ValidationError(message=e.message)
                        else:
                            raise e

            return ParamValidator

    def validation_error(self, message: str) -> exceptions.SocaException:
        return exceptions.soca_exception(
            error_code=errorcodes.VALIDATION_FAILED,
            message=message,
            ref=self.param
        )

    def flow_error(self, message: str) -> exceptions.SocaException:
        return exceptions.soca_exception(
            error_code=errorcodes.USER_INPUT_FLOW_ERROR,
            message=message,
            ref=self
        )

    def get_filter(self) -> Callable:
        return self.filter

    def validate(self, value: Any):
        if Utils.is_empty(self.param.validate_):
            return
        validate = self.param.validate_
        if Utils.is_true(validate.required) and Utils.is_empty(value):
            raise self.validation_error(message=f'{self.title} is required')
        if Utils.is_not_empty(validate.regex):
            pattern = re.compile(validate.regex)
            if not pattern.match(value):
                raise self.validation_error(message=f'{self.title} must match regex: {validate.regex}')

    def filter(self, value: Any) -> Optional[T]:
        self.args.set(self.param.name, value)
        return value


class SocaUserInputSection:
    def __init__(self, context: SocaContext,
                 section: SocaUserInputSectionMetadata,
                 prompts: List[SocaPrompt],
                 skip_section_callback: Optional[Callable[['SocaUserInputSection'], bool]] = None):
        self.context = context
        self.section = section
        self.prompts = prompts
        self._skip_section_callback = skip_section_callback
        self._current_prompt = 0

    @property
    def name(self) -> str:
        return self.section.name

    @property
    def module(self) -> str:
        return self.section.module

    @property
    def title(self) -> Optional[str]:
        return self.section.title

    @property
    def current_prompt(self) -> int:
        return self._current_prompt

    def print_title(self, prefix: str = None):
        title = self.title
        if title is None:
            return
        if not Utils.is_empty(prefix):
            title = f'({prefix}) {title}'
        console.print(title,
                      style=RichStyle(bold=True, underline=True, italic=True),
                      highlight=False)
        console.line(1)

    def ask_review_prompt(self, message: str = None, auto_enter: bool = True) -> bool:
        try:

            if Utils.is_empty(message):
                message = f'Are the {self.section.title} OK?'

            result = 'result'
            response = unsafe_prompt(questions=[{
                'type': 'confirm',
                'name': result,
                'message': message,
                'default': False,
                'auto_enter': auto_enter,
                'qmark': '?'
            }])
            return Utils.get_value_as_bool(result, response)

        except KeyboardInterrupt:

            title = self.title
            if title is None:
                title = self.section.name

            raise exceptions.soca_exception(
                error_code=errorcodes.USER_INPUT_FLOW_INTERRUPT,
                message=f'"{title}" review canceled by user',
                ref=self
            )

    def _reset(self):
        self._current_prompt = 0

    def ask(self, restart: bool = False, review_mode: bool = False) -> Optional[Dict]:
        try:

            if restart:
                self._reset()

            result = {}
            for index, question in enumerate(self.prompts):
                if index < self.current_prompt:
                    continue

                answer = question.ask(review_mode)
                if answer is not None:
                    result[question.name] = answer

                self._current_prompt += 1

            return result
        except exceptions.SocaException as e:
            if e.error_code == errorcodes.USER_INPUT_FLOW_INTERRUPT:
                raise exceptions.soca_exception(
                    error_code=errorcodes.USER_INPUT_FLOW_INTERRUPT,
                    message=e.message,
                    ref=self
                )
            else:
                raise e


SocaContextType = TypeVar('SocaContextType', bound=SocaContext)
SectionCallback = Callable[[SocaContextType, SocaUserInputSection, Any], bool]


class QueuedSection:
    def __init__(self, index: int, section: SocaUserInputSection, review_mode: bool = False):
        self.priority = index
        self.section = section
        self.review_mode = review_mode

    def __eq__(self, other: 'QueuedSection'):
        return self.priority == other.priority

    def __lt__(self, other: 'QueuedSection'):
        return self.priority < other.priority

    def __hash__(self):
        return self.priority


class SocaUserInputModule:
    def __init__(self, context: SocaContext,
                 module: SocaUserInputModuleMetadata,
                 sections: List[SocaUserInputSection],
                 section_callback: Optional[SectionCallback] = None,
                 section_callback_kwargs: Optional[Dict] = None,
                 restart_errorcodes: Optional[List[str]] = None,
                 persistent: bool = True,
                 start_section: Optional[int] = None,
                 start_section_name: Optional[str] = None,
                 display_info: bool = True,
                 display_steps: bool = True):
        self.context = context
        self.module = module
        self.sections = sections
        self._persistent = persistent
        self._section_callback: Optional[SectionCallback] = section_callback
        self._section_callback_kwargs: Optional[Dict] = section_callback_kwargs
        self._restart_errorcodes = restart_errorcodes
        self._display_info = display_info
        self._display_steps = display_steps

        start_section_index = None
        if start_section is not None:
            start_section_index = start_section
        elif start_section_name is not None:
            for index, section in enumerate(self.sections):
                if section.name == start_section_name:
                    start_section_index = index
        self._start_section_index = start_section_index

        self._queue: Optional[queue.PriorityQueue[QueuedSection]] = queue.PriorityQueue()
        self._current_section = 0
        self._total_sections = 0

        self._reset()

    def _drain_queue(self):
        while True:
            try:
                self._queue.get(block=False)
            except queue.Empty:
                break

    def _reset(self):
        self._current_section = 0
        self._total_sections = self.compute_total_sections()
        self._drain_queue()
        for index, section in enumerate(self.sections):
            self._queue.put(QueuedSection(index, section))

    def start_section_index(self) -> int:
        return Utils.get_as_int(self._start_section_index, 0)

    def compute_total_sections(self) -> int:
        total = 0
        for section in self.sections:
            if isinstance(section, SocaUserInputSection):
                total += 1
        return total

    @property
    def total_sections(self) -> int:
        return self._total_sections

    @property
    def next_section(self) -> int:
        return self._current_section + 1

    @property
    def current_section(self) -> int:
        return self._current_section

    @property
    def current_section_step(self) -> int:
        return self.current_section + 1

    def get_section_title(self, index: int = None) -> Optional[str]:
        if Utils.is_empty(self.sections):
            return None
        if index is None:
            section = Utils.get_first(self.sections)
        else:
            section = self.sections[index]
        if isinstance(section, SocaUserInputSection):
            return section.title
        return None

    @property
    def title(self) -> Optional[str]:
        return self.module.title

    @property
    def description(self) -> Optional[str]:
        return self.module.description

    @property
    def name(self) -> str:
        return self.module.name

    def print_title(self):
        if not self._display_info:
            return
        title = self.title
        if title is None:
            return
        console.print(title, style=RichStyle(bold=True, underline=True))
        description = self.description
        if Utils.is_empty(description):
            console.line(1)

    def print_description(self):
        if not self._display_info:
            return
        description = self.description
        if description is None:
            return
        console.print(description)
        console.line(1)

    def ask(self, restart: bool = False,
            restart_section: bool = True) -> Optional[Dict]:

        if len(self.sections) == 0:
            return None

        if restart:
            self._reset()
            self.print_title()
            self.print_description()

        result = {}
        queued_section = None

        while not self._queue.empty():
            try:
                queued_section = self._queue.get()
                section = queued_section.section

                if restart_section:
                    section_prefix = None
                    if self._display_steps:
                        section_prefix = f'Step {self.current_section_step} of {self.total_sections}'
                    section.print_title(prefix=section_prefix)

                answers = section.ask(restart=restart_section, review_mode=queued_section.review_mode)
                result = {**result, **answers}

                queued_section.review_mode = False
                callback_result = True
                if self._section_callback:
                    callback_kwargs = Utils.get_as_dict(self._section_callback_kwargs, {})
                    callback_result = self._section_callback(self.context, section, **callback_kwargs)
                    if not callback_result:
                        queued_section.review_mode = False
                        self._queue.put(queued_section)

                if callback_result:
                    self._current_section += 1

                console.line(1)

            except exceptions.SocaException as e:
                if e.error_code == errorcodes.USER_INPUT_FLOW_INTERRUPT:
                    raise exceptions.soca_exception(
                        error_code=errorcodes.USER_INPUT_FLOW_INTERRUPT,
                        message=e.message,
                        ref=queued_section
                    )
                else:
                    raise e

        return result

    def is_restart_error_code(self, error_code: str) -> bool:
        if Utils.is_empty(self._restart_errorcodes):
            return False
        return error_code in self._restart_errorcodes

    @property
    def is_persistent(self) -> bool:
        return self._persistent

    def flow_interrupt_prompt(self) -> Optional[str]:
        choices = [
            Choice(title='Cancel', value='cancel')
        ]
        default_choice = choices[0]

        restart_module_choice = 'Restart'
        if self.current_section > 0:
            restart_module_choice += ' from Step 1'
            first_section_title = self.get_section_title()
            if first_section_title is not None:
                restart_module_choice += f': {first_section_title}'
        choices.append(Choice(title=restart_module_choice, value='restart-module'))

        if self.current_section > 0:
            current_section_title = self.get_section_title(index=self.current_section)
            restart_section_choice = f'Restart current, Step {self.current_section_step}'
            if current_section_title is not None:
                restart_section_choice += f': {current_section_title}'
            choices.append(Choice(title=restart_section_choice, value='restart-section'))

        choices.append(Choice(title='Yes, Exit.', value='exit'))

        instruction = None
        if self.is_persistent:
            if self.current_section > 1:
                instruction = "Don't worry. We've saved the progress up until now."
        else:
            instruction = 'Warning! All progress will be lost.'

        instruction_suffix = 'Select an option below. Use shortcuts'
        if instruction is None:
            instruction = instruction_suffix
        else:
            instruction = f'{instruction} {instruction_suffix}'
        instruction = f'({instruction})'

        option = 'interrupt_option'
        prompt = {
            'type': 'select',
            'name': option,
            'message': 'Do you want to exit?',
            'instruction': instruction,
            'choices': choices,
            'default': default_choice
        }
        result = unsafe_prompt(questions=[prompt])
        return Utils.get_value_as_string(option, result)

    def safe_ask(self, restart: bool = True, restart_section: bool = True) -> Optional[Dict]:
        try:

            return self.ask(restart=restart,
                            restart_section=restart_section)

        except exceptions.SocaException as e:
            if e.error_code == errorcodes.USER_INPUT_FLOW_INTERRUPT:
                if Utils.is_not_empty(e.message):
                    console.print(e.message, style='bold yellow')
                option = self.flow_interrupt_prompt()
                if option == INTERRUPT_OPTION_CANCEL:
                    self._queue.put(e.ref)
                    return self.safe_ask(restart=False, restart_section=False)
                elif option == INTERRUPT_OPTION_RESTART_MODULE:
                    console.line(1)
                    return self.safe_ask(restart=True, restart_section=True)
                elif option == INTERRUPT_OPTION_RESTART_SECTION:
                    console.line(1)
                    self._queue.put(e.ref)
                    return self.safe_ask(restart=False, restart_section=True)
                else:
                    raise e
            else:
                raise e
