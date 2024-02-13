#! /usr/bin/env python3
""" Tests for the configuration loader utility """

import os
import json

from typing import Any

from jsonschema import Draft7Validator, exceptions
from ruamel.yaml import YAML
from jsonpath_ng import parse
from jsonpath_ng.exceptions import JsonPathParserError


class Confi:
    """ Configuration loader utility """

    prefixes: list[str] = ['env://', 'file://', 'json://', 'yaml://']

    def __init__(self) -> None:
        self.conf_values: dict[str, Any] = {}
        self.stubs: dict[Any, tuple[str, Any]] = {}

    def validate(self, values: dict[str, Any] | None = None):
        """ Validate the configuration against the schema """
        def get_val(conf: dict[str, Any], path: str) -> Any:
            try:
                return parse(path).find(conf)[0].value
            except (IndexError, JsonPathParserError) as exc:
                raise ValueError(f"Invalid jsonpath: {path}") from exc

        def validate_stub(conf: dict[str, Any], schema_def: Any) -> None:
            validator = Draft7Validator(schema_def)
            try:
                validator.validate(conf)
            except exceptions.ValidationError as err:
                raise ValueError(f"Invalid configuration: {err}") from err

        if not values:
            values = self.conf_values
        for stub in self.stubs.values():
            path, schema_def = stub
            validate_stub(get_val(values, path), schema_def)

    def register_conf_stub(self, stub_id: Any, path: str, schema_def: Any):
        """ Register a stub for the given jsonpath """
        try:
            parse(path)
        except JsonPathParserError as err:
            raise ValueError(
                f"Invalid jsonpath: {err}, ({stub_id=}, {path=}, {schema_def=})"
            ) from err
        self.stubs[stub_id] = (path, schema_def)

    @staticmethod
    def load_env_var(value: str) -> str:
        """Load the value from the environment variable"""
        return str(os.environ[value])

    @staticmethod
    def load_file(value: str) -> str:
        """Loads content of the file passed"""
        with open(value, 'r', encoding='utf-8') as file:
            return file.read()

    @staticmethod
    def load_json(value: str) -> dict:
        """Loads dict from a json string"""
        return json.loads(value)

    @staticmethod
    def load_yaml(value: str) -> dict:
        """Loads dict from a yaml string"""
        return YAML(typ='safe').load(value)

    def load_values(self, conf: str):
        """
        Preload the values from the configuration file.
        String should be in yaml format.
        There is a preload util that specifies reading values from
        * env variables - value should start with 'env:'
        * files - value should start with 'file://'
        * json strings - value should start with 'json://'
        * yaml strings - value should start with 'yaml://'
        """
        # conf_values = Confi.load_yaml(conf)
        # # Ignore the linter warning.
        # # It's impossible to end up having anything else than dict
        # # as a return value
        # while Confi.needs_preload(conf_values):  # type: ignore
        #     conf_values = Confi.process_value(Confi.load_yaml(conf_values))  # type: ignore
        # self.conf_values = conf_values  # type: ignore
        self.conf_values = Confi.process_value(Confi.load_yaml(conf))  # type: ignore

    @staticmethod
    def load_str(value: str) -> str | dict | list:
        """
        Util method that loads a value from a string.
        If the value starts with a prefix,
          it calls the respective loading function.
        """
        if value.startswith('env://'):
            return Confi.process_value(
                Confi.load_env_var(value.removeprefix("env://"))
            )
        if value.startswith('file://'):
            return Confi.process_value(
                Confi.load_file(value.removeprefix("file://"))
            )
        if value.startswith('json://'):
            return Confi.process_value(
                Confi.load_json(Confi.load_file(value.removeprefix("json://")))
            )
        if value.startswith('yaml://'):
            return Confi.process_value(
                Confi.load_yaml(Confi.load_file(value.removeprefix("yaml://")))
            )
        return value

    @staticmethod
    def process_value(value: str | dict | list) -> str | dict | list:
        """
        Util method that processes a value.
        If the value is a string, it processes it accordingly.
        If the value is a dict or list,
          it calls the respective processing function.
        """
        if isinstance(value, str):
            return Confi.load_str(value)
        if isinstance(value, dict):
            return {k: Confi.process_value(v) for k, v in value.items()}
        if isinstance(value, list):
            return [Confi.process_value(v) for v in value]
        return value
