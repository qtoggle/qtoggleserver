
class ConfigurableMixin:
    @classmethod
    def configure(cls, **kwargs) -> None:
        for name, value in kwargs.items():
            conf_method = getattr(cls, f'configure_{name.lower()}', None)
            if conf_method:
                conf_method(value)

            else:
                setattr(cls, name.upper(), value)
