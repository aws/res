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

"""
DynamoDB Local Server for Unit Tests
"""

from ideasdk.shell import ShellInvoker, StreamInvocationProcess
from ideatestutils import IdeaTestProps

import hashlib
import os
import requests
import shutil
import pathlib
from threading import Thread
from typing import Optional

DYNAMODB_LOCAL_PACKAGE_URL = 'https://s3.us-west-2.amazonaws.com/dynamodb-local/'
DYNAMODB_LOCAL_PACKAGE_FILE= 'dynamodb_local_2023-06-09.zip'
DYNAMODB_LOCAL_PACKAGE_SHA_256_URL = 'https://s3.us-west-2.amazonaws.com/dynamodb-local/'
DYNAMODB_LOCAL_PACKAGE_SHA_256_FILE = 'dynamodb_local_2023-06-09.zip.sha256'

class DynamoDBLocal:
    """
    Manage DynamoDBLocal server for unit tests.
    * handles ddb local installation
    * exposes start and stop methods to manage server life-cycle based on unit test scope
    """

    def __init__(self, db_name: str = 'default', port: int = 9000, reset: bool = False, cleanup: bool = False):
        """
        :param port: the port on which ddb local can be accessible. ddb endpoint url will be: http://localhost:9000
        :param reset: the ddb_dir will be deleted prior to starting
        :param cleanup: the ddb_dir will be deleted after stopping
        """
        self.db_name = db_name
        self.port = port
        self.reset = reset
        self.cleanup = cleanup
        self.shell = ShellInvoker()
        self.props = IdeaTestProps()

        if self.db_name == '':
            self.db_name = 'default'

        base_db_dir = self.props.get_test_dir('ddb')
        self.db_dir = os.path.join(base_db_dir, self.db_name)

        self.process: Optional[StreamInvocationProcess] = None

        if not self.check_and_install():
            raise Exception("Unable to validate or install DynamoDB Local.")

        #  Mark ddb_local thread as daemonic
        #  This helps avoid codebuild execution hanging on local_ddb thread running in the background
        self.loop = Thread(
            target=self._run_ddb_local,
            name='ddb-local',
            daemon=True
        )

    def get_ddb_local_download_dir(self) -> str:
        idea_user_home_dir = self.props.get_idea_user_home_dir()
        downloads_dir = os.path.join(idea_user_home_dir, 'downloads')
        os.makedirs(downloads_dir, exist_ok=True)
        return downloads_dir

    def get_ddb_local_zip_file(self) -> str:
        return os.path.join(self.get_ddb_local_download_dir(), DYNAMODB_LOCAL_PACKAGE_FILE)

    def get_ddb_local_zip_sha256_file(self) -> str:
        return os.path.join(self.get_ddb_local_download_dir(), DYNAMODB_LOCAL_PACKAGE_SHA_256_FILE)

    def get_ddb_local_lib_dir(self) -> str:
        idea_user_home_dir = self.props.get_idea_user_home_dir()
        lib_dir = os.path.join(idea_user_home_dir, 'lib')
        return os.path.join(lib_dir, 'dynamodb-local')

    def get_ddb_local_jar_file(self) -> str:
        return os.path.join(self.get_ddb_local_lib_dir(), 'DynamoDBLocal.jar')

    def get_ddb_local_java_libs_dir(self) -> str:
        return os.path.join(self.get_ddb_local_lib_dir(), 'DynamoDBLocal_lib')

    def check_and_install(self) -> bool:
        """
        download and install ddb local in ~/.idea/lib/dynamodb-local
        """
        # TODO: May want to consider always pulling down the file, this just makes is faster locally

        # check pre-requisites
        print(f"Checking which version of java")
        which_java = self.shell.invoke(['which', 'java'])
        if which_java.returncode != 0:
            print('DynamoDB local cannot be initialized. Java Runtime Environment (JRE) is required.')
            return False
        print('java installed')

        # Check to see if DDB local is installed, exit if already installed
        ddb_local_jar_file = self.get_ddb_local_jar_file()
        if os.path.isfile(ddb_local_jar_file):
            print("DynamoDB already installed to local file system.")
            return True

        # Download DDB Local tar.gz file if not present
        if self.download_ddb_local() is not True:
            return False

        if self.validate_ddb_local_sha256() is not True:
            return False

        # Install directory exists, but DDB Local jar file missing
        # In this situation remove the directory and all contents
        ddb_local_lib_dir = self.get_ddb_local_lib_dir()
        if os.path.isdir(ddb_local_lib_dir):
            shutil.rmtree(ddb_local_lib_dir)

        os.makedirs(str(pathlib.Path(ddb_local_lib_dir).parent), exist_ok=True)

        print('Unpacking DDB local ...')
        shutil.unpack_archive(self.get_ddb_local_zip_file(), self.get_ddb_local_lib_dir(), 'zip')

        return True

    def download_ddb_local(self) -> bool:
        ddb_local_zip_sha256_file = self.get_ddb_local_zip_sha256_file()
        if not os.path.isfile(ddb_local_zip_sha256_file):
            print(f'Downloading DDB SHA256: {DYNAMODB_LOCAL_PACKAGE_SHA_256_URL + DYNAMODB_LOCAL_PACKAGE_SHA_256_FILE} ...')
            request = requests.get(DYNAMODB_LOCAL_PACKAGE_SHA_256_URL + DYNAMODB_LOCAL_PACKAGE_SHA_256_FILE)
            with open(ddb_local_zip_sha256_file, 'wb') as f:
                f.write(request.content)

        ddb_local_zip_file = self.get_ddb_local_zip_file()
        if not os.path.isfile(ddb_local_zip_file):
            print(f'Downloading DDB local: {DYNAMODB_LOCAL_PACKAGE_URL + DYNAMODB_LOCAL_PACKAGE_FILE} ...')
            request = requests.get(DYNAMODB_LOCAL_PACKAGE_URL + DYNAMODB_LOCAL_PACKAGE_FILE)
            with open(ddb_local_zip_file, 'wb') as f:
                f.write(request.content)

        return True

    def validate_ddb_local_sha256(self):
        ddb_local_zip_sha256_file = self.get_ddb_local_zip_sha256_file()
        sha256 = ''
        with open(ddb_local_zip_sha256_file, 'r') as f:
            sha256 = ((f.readline()).split())[0]

        ddb_local_zip_file = self.get_ddb_local_zip_file()
        hash_sha256 = hashlib.sha256()
        with open(ddb_local_zip_file, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)

        if hash_sha256.hexdigest() != sha256:
            return False

        return True

    def _run_ddb_local(self):
        cmd = [
            'java',
            f'-Djava.library.path={self.get_ddb_local_java_libs_dir()}',
            '-jar',
            self.get_ddb_local_jar_file(),
            '-port',
            f'{self.port}',
            f'-dbPath',
            self.db_dir,
            '-sharedDb'
        ]
        print(' '.join(cmd))
        self.process = self.shell.invoke_stream(
            cmd=cmd,
            callback=lambda line: print(line, end='')
        )

        print(f'DynamoDB local started. endpoint url: http://localhost:{self.port}')

        try:
            self.process.start_streaming()
        except KeyboardInterrupt:
            self.process.send_stop_signal()
            self.process.wait()

        print(f'DDB local stopped.')

    def start(self):
        if self.reset and os.path.isdir(self.db_dir):
            print(f'reset db dir: {self.db_dir}')
            shutil.rmtree(self.db_dir)

        os.makedirs(self.db_dir, exist_ok=True)

        print('Starting DDB local ...')
        self.loop.start()

    def stop(self):
        print('Stopping DDB local ...')
        if self.process is not None:
            self.process.send_stop_signal()

        if self.cleanup and os.path.isdir(self.db_dir):
            print(f'clean-up db dir: {self.db_dir}')
            shutil.rmtree(self.db_dir)


if __name__ == '__main__':
    db = DynamoDBLocal(
        db_name='cluster-manager',
        reset=True
    )

    import time

    db.start()
    time.sleep(10)
    db.stop()
