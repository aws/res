#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
import subprocess
from res.utils import table_utils, logging_utils

logger = logging_utils.get_logger("bootstrap")

def set_proxy():
    logger.info(f"Starting idea_proxy configuration ")
    idea_https_proxy = os.environ.get('IDEA_HTTPS_PROXY')
    proxy_content = f"""#Export proxy settings
export HTTPS_PROXY={idea_https_proxy}
export https_proxy={idea_https_proxy}
export NO_PROXY={os.environ.get('IDEA_NO_PROXY', '')}
export no_proxy={os.environ.get('IDEA_NO_PROXY', '')}"""

    try:
        with open('/etc/profile.d/proxy.sh', 'w') as f:
            f.write(proxy_content)

        os.environ['HTTPS_PROXY'] = idea_https_proxy
        os.environ['https_proxy'] = idea_https_proxy

        idea_no_proxy = os.environ.get('IDEA_NO_PROXY', '')
        os.environ['NO_PROXY'] = idea_no_proxy
        os.environ['no_proxy'] = idea_no_proxy

        subprocess.run(['bash', '-c', 'source /etc/profile.d/proxy.sh'], check=True)
        logger.info(f"Successfully configured proxy")
    except Exception as e:
        logger.error(f"Error setting proxy environment: {e}")
