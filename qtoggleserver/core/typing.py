from typing import Any


type PortValue = int | float | bool
type NullablePortValue = int | float | bool | None
type PortValueChoices = list[dict[str, str | int | float]]

type Attribute = int | float | bool | str | list[dict] | None
type Attributes = dict[str, Attribute]

type AttributeDefinition = dict[str, Any]
type AttributeDefinitions = dict[str, AttributeDefinition]

type GenericJSONDict = dict[str, Any]
type GenericJSONList = list[dict[str, Any]]
