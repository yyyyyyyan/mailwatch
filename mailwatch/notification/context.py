import json
import re
import tomllib
from collections.abc import Mapping
from configparser import ConfigParser
from configparser import ParsingError
from pathlib import Path
from string import ascii_letters


class Context(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for key in list(self.keys()):
            self[key] = super().pop(key)

    def __setitem__(self, key, value):
        if isinstance(value, Mapping) and not isinstance(value, self.__class__):
            self[key] = self.__class__(**value)
        else:
            super().__setitem__(self.__class__._convert_key(key), value)

    def __getitem__(self, key):
        return super().__getitem__(self.__class__._convert_key(key))

    def __delitem__(self, key):
        return super().__delitem__(self.__class__._convert_key(key))

    def __contains__(self, key):
        return super().__contains__(self.__class__._convert_key(key))

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            for key, value in self.items():
                attr = re.sub(r"\W", "_", self.__class__._convert_key(key))
                if attr[0] not in ascii_letters + "_":
                    attr = "_" + attr
                if self.__class__._convert_key(name) == attr:
                    return value
        raise AttributeError(
            f"'{self.__class__.__name__}' object has no attribute or key '{name}'"
        )

    def __or__(self, other):
        return super().__or__(self.__class__(other))

    def __ior__(self, other):
        return super().__ior__(self.__class__(other))

    @staticmethod
    def _convert_key(key):
        return str(key).lower()

    @classmethod
    def from_file(cls, path):
        if not path.is_file():
            raise FileNotFoundError(f"'{path}' is not a valid file")
        try:
            return cls.from_ini(path)
        except ParsingError:
            pass
        try:
            return cls.from_json(path)
        except json.JSONDecodeError:
            pass
        try:
            return cls.from_toml(path)
        except tomllib.TOMLDecodeError:
            raise ValueError(f"'{path}' is not a valid config file") from None

    @classmethod
    def from_ini(cls, path):
        config = ConfigParser()
        config.read(path)
        return cls(config)

    @classmethod
    def from_json(cls, path, load_func=json.load):
        with path.open("rb") as file:
            return cls(load_func(file))

    @classmethod
    def from_toml(cls, path):
        return cls.from_json(path, tomllib.load)

    def pop(self, key, *args, **kwargs):
        return super().pop(self.__class__._convert_key(key), *args, **kwargs)

    def get(self, key, *args, **kwargs):
        return super().get(self.__class__._convert_key(key), *args, **kwargs)

    def setdefault(self, key, *args, **kwargs):
        return super().setdefault(self.__class__._convert_key(key), *args, **kwargs)

    def update(self, E=None, **F):  # noqa: N803
        super().update(self.__class__(E))
        super().update(self.__class__(**F))


class ContextVar:
    SEPARATOR = ":"

    def __init__(self, ctx_str):
        try:
            self.key, self.value = ctx_str.split(self.SEPARATOR, 1)
        except ValueError as err:
            raise ValueError(
                f"'{ctx_str}' is not a valid context variable (not in key{self.SEPARATOR}value format)"
            ) from err


class ContextFile(ContextVar):
    def __init__(self, ctx_str):
        super().__init__(ctx_str)
        self.value = Path(self.value).resolve()
