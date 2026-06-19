import inspect

from typing import Any


class DriverParamsMixin:
    """Mixin that captures __init__ parameters in _params for introspection.

    When a class hierarchy inherits from this mixin, all keyword arguments that
    match parameter names in the class hierarchy's __init__ signatures are
    captured in the _params dict. This enables introspection of how driver
    instances were configured.

    The _driver attribute is automatically set to either:
      - The value of the 'driver' kwarg if provided, OR
      - The fully-qualified class name (module.ClassName) as default

    Behavior:
      - Walks the MRO to collect all __init__ parameter names from classes
        appearing before DriverParamsMixin in the hierarchy
      - Captures kwargs matching those parameter names in _params dict
      - Only keyword arguments are captured (positional args are not tracked)
      - Kwargs not matching any parameter name in the hierarchy are silently dropped

    Usage:
        class Base(DriverParamsMixin):
            def __init__(self, b1: str, b2: int, **kwargs: Any) -> None:
                super().__init__(**kwargs)
                self.b1 = b1
                self.b2 = b2

        class Child(Base):
            def __init__(self, b1: str, b2: int, c1: str, c2: float, **kwargs: Any) -> None:
                super().__init__(b1=b1, b2=b2, **kwargs)
                self.c1 = c1
                self.c2 = c2

        # All kwargs matching hierarchy parameter names are captured
        child = Child(b1="v1", b2=42, c1="cv1", c2=3.14)
        assert child.get_params() == {"b1": "v1", "b2": 42, "c1": "cv1", "c2": 3.14}

        # Extra kwargs not in any signature are dropped
        child = Child(b1="v1", b2=42, c1="cv1", c2=3.14, unknown="dropped")
        assert child.get_params() == {"b1": "v1", "b2": 42, "c1": "cv1", "c2": 3.14}

        # Custom driver name
        child = Child(b1="v1", b2=42, c1="cv1", c2=3.14, driver="custom.Driver")
        assert child.get_driver() == "custom.Driver"
    """

    _params: dict[str, Any]
    _driver: str

    def __new__(cls: type, *args: Any, **kwargs: Any) -> DriverParamsMixin:
        instance = super().__new__(cls)

        # Find the direct parent class that is not DriverParamsMixin
        parents = []
        for i, base in enumerate(cls.__mro__):
            if i < len(cls.__mro__) - 1 and cls.__mro__[i + 1] is DriverParamsMixin:
                break
            parents.append(cls.__mro__[i])

        # Only capture driver params if we have a parent (i.e., cls is not the base)
        # Get parameters defined by the *direct parent* class
        driver_param_names: set[str] = set()
        for parent in parents:
            try:
                sig = inspect.signature(parent.__init__)
                driver_param_names.update({p for p in sig.parameters.keys() if p != "self"})
            except ValueError, TypeError:
                pass

        # Driver params = any kwarg NOT in direct parent
        driver_params = {k: v for k, v in kwargs.items() if k in driver_param_names}

        # Store driver params on the instance before __init__ runs
        instance._params = driver_params
        instance._driver = kwargs.get("driver") or f"{cls.__module__}.{cls.__name__}"

        return instance

    def __init__(self, **kwargs: Any) -> None:
        """Consume kwargs to prevent them from reaching object.__init__()."""
        pass

    def get_driver(self) -> str:
        return self._driver

    def get_params(self) -> dict[str, Any]:
        return self._params
