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
import os
from typing import Union, List, Optional
from rich.text import Text
from ideadatamodel.common import SocaKeyValue

BANNER = """
'########::'########::'######::
 ##.... ##: ##.....::'##... ##:
 ##:::: ##: ##::::::: ##:::..::
 ########:: ######:::. ######::
 ##.. ##::: ##...:::::..... ##:
 ##::. ##:: ##:::::::'##::: ##:
 ##:::. ##: ########:. ######::
..:::::..::........:::......:::

"""


def ascii_banner(title: str = 'Research and Engineering Studio on AWS', meta_info: Optional[List[SocaKeyValue]] = None, rich=False) -> Union[Text, str]:
    banner_lines = BANNER.splitlines()
    banner_width = len(banner_lines[2])
    banner_lines.append(str.center(title, banner_width))

    if not rich:
        meta_lines = []
        if meta_info:
            for meta in meta_info:
                tokens = []
                if meta.key:
                    tokens.append(meta.key)
                if meta.value:
                    tokens.append(f'({meta.value})')
                meta_lines.append(str.center(' '.join(tokens), banner_width))
        return os.linesep.join(banner_lines + meta_lines)

    banner_content = os.linesep.join(banner_lines)

    banner_text = Text(banner_content)
    banner_text.highlight_words(['.', ':'], style='orange1 dim')
    banner_text.highlight_words(['\''], style='white')
    banner_text.highlight_words([title, '#'], style='bright_white')

    if not meta_info:
        return banner_text

    meta_content = []
    for meta in meta_info:
        meta_content.append(os.linesep)
        tokens = []
        if meta.key:
            tokens.append(meta.key)
        if meta.value:
            tokens.append(meta.value)
        if len(tokens) == 0:
            continue
        meta_text_content = ' '.join(tokens)
        meta_text = Text(str.center(meta_text_content, banner_width))
        meta_content.append(meta_text)
        if meta.key:
            meta_text.highlight_words([meta.key], style='bright_cyan bold')
        if meta.value:
            meta_text.highlight_words([meta.value], style='bright_green')

    return Text.assemble(banner_text, *meta_content)
