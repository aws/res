#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
import abc
import json
import typing
from dataclasses import asdict, dataclass, field, fields
from enum import Enum
from typing import Any, ClassVar, Generator, List, Optional, Type, TypeVar, Union

import aws_cdk
from constructs import Construct


class Key(str, Enum):
    """
    Enum providing a place to define the CfnParameter ids that will
    be shown to the customer. This is subclassed by category for
    organizational purposes in their respective modules.
    """

    pass


@dataclass(frozen=True)
class Attributes:
    """
    Attributes for specifying CfnParameter resources. See
    https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.CfnParameter.html#initializer
    for descriptions.
    """

    id: Key
    description: Optional[str] = None
    type: Optional[str] = None
    allowed_pattern: Optional[str] = None
    allowed_values: Optional[list[str]] = None
    constraint_description: Optional[str] = None
    no_echo: Optional[bool] = None


B = TypeVar("B", bound="Base")


@dataclass
class Base(abc.ABC):
    """
    Serves as a base that provides the ability to define parameters with specified
    attributes for generating CfnParameter resources as well as marshaling them to
    and from the CDK context similar to how struct tags are used in Go.

    When defining parameters, attributes are supplied to dictate how the resulting
    CfnParameter will be generated. The parameters match directly to those accepted
    by CfnParameter.

    Example:
        name: str = Base.parameter(Attributes(id=Key.NAME))

    All inheriting classes also need to decorated with dataclasses.dataclass
    """

    _attributes_key: ClassVar[str] = "res.parameters"
    _generated: bool = False
    _parameters: dict[Key, aws_cdk.CfnParameter] = field(default_factory=dict)

    def generate(self, scope: Construct) -> None:
        """
        Create the CfnParameter resources within a specified scope. This also
        builds an internal map for parameter lookup for later use when the values
        are needed.
        """
        if self._generated:
            return
        for f, attributes in self._fields():
            self._parameters[attributes.id] = aws_cdk.CfnParameter(
                scope, default=self._default(f), **asdict(attributes)
            )
        self._generated = True

    def _default(self, f: Any) -> Any:
        value = getattr(self, f.name)
        if isinstance(value, list):
            value = ",".join(value)  # CFN wants a string for List defaults
        return value

    def get(self, key: Key) -> aws_cdk.CfnParameter:
        """
        Get the generated CfnParameter associated with a particular Key.
        """
        if not self._generated:
            raise KeyError("parameters not generated yet")
        if key not in self._parameters:
            raise KeyError("key not found in parameters")
        return self._parameters[key]

    def get_str(self, key: Key) -> str:
        """
        Get the generated CfnParameter associated with a particular Key as a string.
        """
        return self.get(key).value_as_string

    def get_num(self, key: Key) -> Union[int, float]:
        """
        Get the generated CfnParameter associated with a particular Key as a number.
        """
        return self.get(key).value_as_number

    def to_context(self) -> dict[str, Any]:
        """
        Create a dictionary that maps a parameter's Key to its json-dumped
        value. This can be used to pass context into cdk.
        """
        result: dict[str, Any] = {}
        for f, attributes in self._fields():
            value = getattr(self, f.name)
            if value is not None:
                result[attributes.id] = json.dumps(value)
        return result

    @classmethod
    def from_context(cls: Type[B], scope: Construct) -> B:
        """
        Instantiate an object with the values set based on the scope's context.
        """
        params = {}

        for f, attributes in cls._fields():
            value = scope.node.try_get_context(attributes.id)
            if value:
                params[f.name] = json.loads(value)

        return cls(**params)

    @classmethod
    def parameter(cls, attributes: Attributes) -> Any:
        """
        Defines a parameter based on attributes that will have a CfnParameter
        resource created when `generate()` is called.
        """
        return field(default=None, metadata={cls._attributes_key: attributes})

    @classmethod
    def _fields(cls) -> Generator[tuple[Any, Attributes], None, None]:
        for f in fields(cls):
            attributes = cls._get_attributes(f)
            if attributes is not None:
                yield f, attributes

    @classmethod
    def _get_attributes(cls, f: Any) -> Optional[Attributes]:
        if (
            f.metadata
            and cls._attributes_key in f.metadata
            and isinstance(f.metadata[cls._attributes_key], Attributes)
        ):
            return typing.cast(Attributes, f.metadata[cls._attributes_key])
        return None
