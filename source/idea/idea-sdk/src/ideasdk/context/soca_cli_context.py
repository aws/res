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

from ideasdk.context import SocaContext, SocaContextOptions
from ideasdk.artwork import ascii_banner
from ideasdk.shell import ShellInvoker
from ideasdk.utils import Utils
from ideasdk.client import SocaClient, SocaClientOptions
from ideadatamodel import (
    exceptions, errorcodes,
    SocaKeyValue,
    SocaUserInputChoice,
    SocaUserInputParamMetadata,
    SocaUserInputSectionMetadata,
    SocaUserInputModuleMetadata,
    SocaInputParamSpec
)
from ideasdk.aws import AwsClientProvider, AWSUtil, AWSClientProviderOptions, AwsResources
from ideasdk.user_input.framework import (
    SocaUserInputArgs,
    SocaUserInputParamRegistry,
    SocaUserInputModule,
    SocaUserInputSection,
    SocaPromptRegistry,
    SocaPrompt
)

from typing import Any, Union, Optional, Dict, List
from pydantic import BaseModel
import os
import sys
from rich.console import Console
from rich.text import Text
from rich.rule import Rule
from rich.markdown import Markdown
from rich.markup import escape
from rich.style import Style
from questionary import unsafe_prompt, Choice
from contextlib import contextmanager
import arrow

if sys.version_info >= (3, 8):
    from typing import Literal
else:
    from typing_extensions import Literal  # pragma: no cover


class SocaCliContext(SocaContext):
    def __init__(self,
                 options: Optional[SocaContextOptions] = None,
                 api_context_path: Optional[str] = None,
                 unix_socket_timeout: Optional[int] = None):
        super().__init__(
            options=options
        )
        self._shell = ShellInvoker()
        self._console = Console()
        self._api_context_path = api_context_path
        self._unix_socket_client: Optional[SocaClient] = None
        self._aws_resources = AwsResources(context=self, aws=self._aws, aws_util=self._aws_util)
        self._unix_socket_timeout: Optional[int] = unix_socket_timeout

    @property
    def shell(self) -> ShellInvoker:
        return self._shell

    @property
    def user_home(self) -> str:
        return os.path.expanduser('~')

    @contextmanager
    def cd(self, path: str):
        self._shell.cwd = path
        try:
            yield
        finally:
            self._shell.cwd = None

    @staticmethod
    def is_windows() -> bool:
        return os.name == 'nt'

    @staticmethod
    def is_root() -> bool:
        return os.geteuid() == 0

    def check_root_access(self):
        if not self.is_root():
            raise exceptions.soca_exception(
                error_code=errorcodes.NOT_AUTHORIZED,
                message='Access Denied: root access is required to use resctl.'
            )

    # BEGIN: STDOUT FUNCTIONS

    @property
    def console(self) -> Console:
        return self._console

    def print_banner(self, meta_info: List[SocaKeyValue] = None):
        if self.is_windows():
            # todo - need to investigate why rich banner printing on windows gives index out of bounds error
            banner = ascii_banner(meta_info=meta_info, rich=False)
            print(banner)
        else:
            banner = ascii_banner(meta_info=meta_info, rich=True)
            self.console.print(banner)
        self.new_line()

    def spinner(self, message: Any):
        return self.console.status(status=message)

    def print(self, message: Any, style=None, end=f'{os.linesep}', new_line=False, highlight=True, **kwargs):
        if Utils.is_not_empty(message):
            try:
                self.console.print(message, end=end, style=style, highlight=highlight, **kwargs)
            except BlockingIOError:
                print(message, end='\r\n')
        if new_line:
            self.new_line()

    def print_title(self, message: str, new_line=False):
        self.print(Text(text=message, style=Style(bold=True, italic=True, color='bright_white')), new_line=new_line)

    def new_line(self, count: int = 1):
        self.console.line(count)

    def print_rule(self, title: Optional[str] = None, align: Literal["left", "center", "right"] = 'left', style=None):
        if Utils.is_empty(title):
            text = ''
        else:
            text = Text(text=title, style=Style(bold=True, italic=True, color='bright_white'))
        if style is None:
            style = 'rule.line'
        self.print(Rule(text, align=align, style=style))

    def print_json(self, payload: Union[str, BaseModel, Any]):
        if isinstance(payload, str):
            json_content = payload
        else:
            json_content = Utils.to_json(payload)
        self.console.print_json(json_content)

    @staticmethod
    def get_label(label: str, style: str) -> Text:
        text = Text(label)
        text.stylize(style)
        return text

    def echo(self, message: str, end=f'{os.linesep}', highlight=False):
        self.console.out(message, end=end, highlight=highlight)

    def debug(self, message: Any):
        if isinstance(message, str):
            message = f'[DEBUG] {message}'
        self.console.print(escape(message), style='dim')

    def success(self, message: Any):
        self.console.print(escape(message), style='bold green')

    def warning(self, message=None):
        self.console.print(escape(message), style='bold yellow')

    def info(self, message=None):
        self.console.print(escape(message), style='cyan')

    def error(self, message=Any):
        self.console.print(escape(message), style='bold red')

    def exception(self, message=None, markdown=False, error_code=errorcodes.CLI_ERROR, ref=None):
        if markdown:
            md_message = Markdown(message)
            self.console.print(md_message)
            raise SystemExit
        else:
            return exceptions.SocaException(
                error_code=error_code,
                message=message,
                ref=ref
            )

    def get_log_message(self, tag: str = None, message: Optional[Union[str, Dict]] = None) -> str:
        if Utils.is_not_empty(tag):
            log = f'[{arrow.now()}] ({tag}) '
        else:
            log = ''
        if message is not None:
            if isinstance(message, str):
                log += message.rstrip()
            else:
                log += Utils.to_json(message)
        return log

    def log(self, tag: str = None, message: Optional[Union[str, Dict]] = None):
        log_message = self.get_log_message(tag, message)
        if Utils.is_empty(log_message):
            return
        self.console.out(log_message.rstrip())

    @staticmethod
    def prompt(message: str, default: Union[bool, str, SocaUserInputChoice] = None, auto_enter=True, icon='?', choices: List[Union[str, SocaUserInputChoice]] = None) -> Union[bool, str]:
        if Utils.is_empty(choices):
            if default is None:
                default = False
            result = unsafe_prompt(questions=[{
                'type': 'confirm',
                'name': 'result',
                'message': message,
                'default': default,
                'auto_enter': auto_enter,
                'qmark': icon
            }])
            return Utils.get_value_as_bool('result', result, default)
        else:
            choices_ = []
            default_choice_ = None
            for choice in choices:
                if isinstance(choice, str):
                    choice_ = Choice(
                        title=choice,
                        value=choice
                    )
                    choices_.append(choice_)
                    if default is not None:
                        if default == choice:
                            default_choice_ = choice_
                else:
                    choice_ = Choice(
                        title=choice.title,
                        value=choice.value,
                        disabled=choice.disabled,
                        checked=choice.checked
                    )
                    choices_.append(choice_)
                    if default is not None:
                        if default.value == choice.value:
                            default_choice_ = choice_

            if default_choice_ is None:
                default_choice_ = choices_[0]

            result = unsafe_prompt(questions=[{
                'type': 'select',
                'name': 'result',
                'message': message,
                'choices': choices_,
                'default': default_choice_,
                'qmark': icon
            }])
            return Utils.get_value_as_string('result', result)

    @property
    def unix_socket_client(self) -> SocaClient:
        if Utils.is_empty(self._api_context_path):
            raise exceptions.general_exception('API Context Path not found')
        if self._unix_socket_client is None:
            self._unix_socket_client = SocaClient(
                context=self,
                options=SocaClientOptions(
                    enable_logging=False,
                    endpoint=f'http://localhost{self._api_context_path}',
                    unix_socket='/run/idea.sock',
                    timeout=self._unix_socket_timeout
                )
            )
        return self._unix_socket_client

    def aws_init(self, aws_profile: Optional[str] = None, aws_region: Optional[str] = None):
        try:
            self._aws = AwsClientProvider(
                options=AWSClientProviderOptions(
                    profile=aws_profile,
                    region=aws_region
                ))
            self._aws_util = AWSUtil(context=self, aws=self._aws)
            self._aws_resources = AwsResources(
                context=self,
                aws=self._aws,
                aws_util=self._aws_util
            )

        except Exception as e:
            self.aws_util().handle_aws_exception(e)

    def refresh_aws_credentials(self):
        if not self.aws().are_credentials_expired():
            return
        self.aws_init(self._aws.aws_profile(), self._aws.aws_region())

    def get_aws_resources(self):
        return self._aws_resources

    def aws(self) -> AwsClientProvider:
        if self._aws.are_credentials_expired():
            self.aws_init(self._options.aws_profile, self._options.aws_region)
        return self._aws

    def ask(self, questions: List[SocaUserInputParamMetadata], title: str = None, description: str = None, module_name: str = None) -> Dict:
        if Utils.is_empty(module_name):
            module_name = 'default'

        spec = SocaInputParamSpec(
            params=questions,
            modules=[
                SocaUserInputModuleMetadata(
                    name=module_name,
                    title=title,
                    description=description,
                    sections=[
                        SocaUserInputSectionMetadata(
                            name='default',
                            params=questions
                        )
                    ]
                )
            ]
        )

        param_registry = SocaUserInputParamRegistry(context=self, spec=spec)
        args = SocaUserInputArgs(context=self, param_registry=param_registry)
        prompt_registry = SocaPromptRegistry(context=self, param_spec=param_registry)

        module_meta = param_registry.get_module(module=module_name)

        section_prompts = []
        params = param_registry.get_params(module=module_name)
        for param_meta in params:
            section_prompts.append(SocaPrompt(
                context=self,
                args=args,
                param=param_meta,
                registry=prompt_registry
            ))

        sections = []
        for section_meta in module_meta.sections:
            sections.append(SocaUserInputSection(
                context=self,
                section=section_meta,
                prompts=section_prompts
            ))

        user_input_module = SocaUserInputModule(
            context=self,
            module=module_meta,
            sections=sections,
            restart_errorcodes=[errorcodes.INSTALLER_MISSING_PERMISSIONS]
        )

        user_input_module.safe_ask()

        return args.build()
