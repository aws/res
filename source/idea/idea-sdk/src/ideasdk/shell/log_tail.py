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

from ideasdk.context import SocaCliContext
from ideasdk.utils import Utils

from typing import Optional, Union, List
import sh
import re
from rich.text import Text


class LogTail:

    def __init__(self, context: SocaCliContext,
                 files: List[str],
                 search_tokens: Optional[Union[str, List[str]]],
                 **kwargs):
        self.context = context
        self.files = files
        self._search_tokens = search_tokens
        self.kwargs = kwargs

    @property
    def is_and(self):
        return Utils.get_value_as_bool('and', self.kwargs, False)

    @property
    def is_follow(self) -> bool:
        return Utils.get_value_as_bool('follow', self.kwargs)

    @property
    def is_command(self) -> bool:
        return Utils.get_value_as_bool('command', self.kwargs)

    @property
    def tail(self):
        return Utils.get_value_as_int('tail', self.kwargs, 100)

    @property
    def search_tokens(self) -> Optional[List[str]]:
        if self._search_tokens is None:
            return None
        if isinstance(self._search_tokens, str):
            return [self._search_tokens]
        else:
            return self._search_tokens

    def _print_cmd(self, cmd: Union[str, List[str]]) -> bool:
        if isinstance(cmd, str):
            msg = cmd
        else:
            msg = " ".join(cmd)
        if self.is_command:
            self.context.print(msg)
            return False
        else:
            self.context.debug(f'> {msg}')
            return True

    def _print_logs(self):

        tail = sh.Command('tail')

        tail_params = []

        if len(self.files) == 1:
            if self.is_follow:
                tail_params.append(f'-{self.tail}f')
            else:
                tail_params.append(f'-{self.tail}')
        else:
            if self.is_follow:
                tail_params.append('-f')

        tail_params += self.files

        tokens = self.search_tokens
        has_tokens = tokens and len(tokens) > 0

        def print_line(line):
            if not has_tokens:
                self.context.echo(line, end='')
                return

            if self.is_and:
                if re.match(regex_expr, line):
                    text = Text(line.rstrip())
                    text.highlight_words(self.search_tokens, style='green')
                    self.context.print(text)
                return

            found = False
            for t in self.search_tokens:
                if t in line:
                    found = True
                    break

            if not found:
                return

            text = Text(line.rstrip())
            text.highlight_regex(regex_expr, style='green')
            self.context.print(text)

        if has_tokens:

            if self.is_and:
                regex_expr = ''
                for token in tokens:
                    regex_expr += f'(?=.*?\\b{token}\\b)'
                regex_expr += '.*'

                tail = tail.bake(*tail_params, _iter=True, _bg=True, _out=print_line)

                if not self._print_cmd(cmd=f'{tail} > custom regex filter: {regex_expr}'):
                    return

                process = tail()

            else:
                regex_expr = f"({'|'.join(tokens)})"

                tail = tail.bake(*tail_params, _iter=True, _bg=True, _out=print_line)

                if not self._print_cmd(cmd=f'{tail} | grep -E \'{regex_expr}\''):
                    return

                process = tail()

        else:

            tail = tail.bake(*tail_params, _iter=True, _bg=True, _out=print_line)
            if not self._print_cmd(cmd=str(tail)):
                return

            process = tail()

        try:
            process.wait()
        except KeyboardInterrupt:
            print()
            process.kill()

    def invoke(self):
        self._print_logs()
