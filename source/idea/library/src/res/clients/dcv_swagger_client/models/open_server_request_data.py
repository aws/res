# coding: utf-8

"""
    DCV Session Manager

    DCV Session Manager API  # noqa: E501

    OpenAPI spec version: 2021.3
    
    Generated by: https://github.com/swagger-api/swagger-codegen.git
"""

import pprint
import re  # noqa: F401

import six

class OpenServerRequestData(object):
    """NOTE: This class is auto generated by the swagger code generator program.

    Do not edit the class manually.
    """
    """
    Attributes:
      swagger_types (dict): The key is attribute name
                            and the value is attribute type.
      attribute_map (dict): The key is attribute name
                            and the value is json key in definition.
    """
    swagger_types = {
        'server_id': 'str'
    }

    attribute_map = {
        'server_id': 'ServerId'
    }

    def __init__(self, server_id=None):  # noqa: E501
        """OpenServerRequestData - a model defined in Swagger"""  # noqa: E501
        self._server_id = None
        self.discriminator = None
        if server_id is not None:
            self.server_id = server_id

    @property
    def server_id(self):
        """Gets the server_id of this OpenServerRequestData.  # noqa: E501

        The server id  # noqa: E501

        :return: The server_id of this OpenServerRequestData.  # noqa: E501
        :rtype: str
        """
        return self._server_id

    @server_id.setter
    def server_id(self, server_id):
        """Sets the server_id of this OpenServerRequestData.

        The server id  # noqa: E501

        :param server_id: The server_id of this OpenServerRequestData.  # noqa: E501
        :type: str
        """

        self._server_id = server_id

    def to_dict(self):
        """Returns the model properties as a dict"""
        result = {}

        for attr, _ in six.iteritems(self.swagger_types):
            value = getattr(self, attr)
            if isinstance(value, list):
                result[attr] = list(map(
                    lambda x: x.to_dict() if hasattr(x, "to_dict") else x,
                    value
                ))
            elif hasattr(value, "to_dict"):
                result[attr] = value.to_dict()
            elif isinstance(value, dict):
                result[attr] = dict(map(
                    lambda item: (item[0], item[1].to_dict())
                    if hasattr(item[1], "to_dict") else item,
                    value.items()
                ))
            else:
                result[attr] = value
        if issubclass(OpenServerRequestData, dict):
            for key, value in self.items():
                result[key] = value

        return result

    def to_str(self):
        """Returns the string representation of the model"""
        return pprint.pformat(self.to_dict())

    def __repr__(self):
        """For `print` and `pprint`"""
        return self.to_str()

    def __eq__(self, other):
        """Returns true if both objects are equal"""
        if not isinstance(other, OpenServerRequestData):
            return False

        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        """Returns true if both objects are not equal"""
        return not self == other
