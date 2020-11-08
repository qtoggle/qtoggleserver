
from typing import Any, Dict, List, Union


PortValue = Union[int, float, bool]
NullablePortValue = Union[int, float, bool, None]
PortValueChoices = List[Dict[str, Union[str, int, float]]]

Attribute = Union[int, float, bool, str, List[dict]]
Attributes = Dict[str, Attribute]

AttributeDefinition = Dict[str, Any]
AttributeDefinitions = Dict[str, AttributeDefinition]

GenericJSONDict = Dict[str, Any]
GenericJSONList = List[Dict[str, Any]]
