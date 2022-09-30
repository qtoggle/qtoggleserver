from typing import Any, Union


PortValue = Union[int, float, bool]
NullablePortValue = Union[int, float, bool, None]
PortValueChoices = list[dict[str, Union[str, int, float]]]

Attribute = Union[int, float, bool, str, list[dict]]
Attributes = dict[str, Attribute]

AttributeDefinition = dict[str, Any]
AttributeDefinitions = dict[str, AttributeDefinition]

GenericJSONDict = dict[str, Any]
GenericJSONList = list[dict[str, Any]]
