from typing import Any, TypeAlias


PortValue: TypeAlias = int | float | bool
NullablePortValue: TypeAlias = int | float | bool | None
PortValueChoices: TypeAlias = list[dict[str, str | int | float]]

Attribute: TypeAlias = int | float | bool | str | list[dict] | None
Attributes: TypeAlias = dict[str, Attribute]

AttributeDefinition: TypeAlias = dict[str, Any]
AttributeDefinitions: TypeAlias = dict[str, AttributeDefinition]

GenericJSONDict: TypeAlias = dict[str, Any]
GenericJSONList: TypeAlias = list[dict[str, Any]]
