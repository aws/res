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

from typing import Optional, Dict, List
import crypt

class LdapUtils:


    @staticmethod
    def get_string_value(key: str, ldap_object: Dict) -> Optional[str]:
        """
        utility method to extract string value from ldap object
        """
        value_list = Utils.get_value_as_list(key, ldap_object)
        if Utils.is_empty(value_list):
            return None
        value_bytes = value_list[0]
        return Utils.from_bytes(value_bytes)

    @staticmethod
    def get_string_list(key: str, ldap_object: Dict) -> Optional[List[str]]:
        """
        utility method to extract string list value from ldap object
        """
        value_list = Utils.get_value_as_list(key, ldap_object)
        if Utils.is_empty(value_list):
            return None
        result = []
        for value_bytes in value_list:
            result.append(Utils.from_bytes(value_bytes))
        return result

    @staticmethod
    def get_int_value(key: str, ldap_object: Dict) -> Optional[int]:
        """
        utility method to extract string list value from ldap object
        """
        value_list = Utils.get_value_as_list(key, ldap_object)
        if Utils.is_empty(value_list):
            return None
        value_bytes = value_list[0]
        return Utils.get_as_int(Utils.from_bytes(value_bytes))

    @staticmethod
    def get_int_list(key: str, ldap_object: Dict) -> Optional[List[int]]:
        """
        utility method to extract int list value from ldap object
        """
        value_list = Utils.get_value_as_list(key, ldap_object)
        if Utils.is_empty(value_list):
            return None
        result = []
        for value_bytes in value_list:
            value = Utils.from_bytes(value_bytes)
            int_value = Utils.get_as_int(value)
            if int_value is None:
                continue
            result.append(int_value)
        return result

    @staticmethod
    def encrypt_password(password: str) -> str:
        """
        utility method to encrypt user password
        used during: create user, change password, respond to auth challenge flows
        :return: encrypted user password suitable for OpenLDAP userPassword attribute
        """
        crypt_string = crypt.crypt(word=password, salt=crypt.mksalt(method=crypt.METHOD_SHA512, rounds=10_000))
        return f'{{CRYPT}}{crypt_string}'
