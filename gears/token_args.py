#! /usr/bin/env python3

"""
Argparser based on tokens from strings
"""

import re
import logging
from dataclasses import dataclass
from typing import Any, Callable


def tokenize_string(input_string: str) -> list[str]:
    """ Function will split a string to 'tokenized' words """
    # This regular expression pattern matches either a word (\\w+)
    # or a quoted string (either single or double quotes)
    pattern = r'\b\w+\b|"[^"]*"|\'[^\']*\''
    matches = re.findall(pattern, input_string)
    # Remove the quotes from the matched strings and split on unescaped spaces
    return [re.sub(r'^["\']|["\']$', '', match) for match in matches]


class TokenParserException(Exception):
    """ Base exception for TokenParser """


class MissingMandatoryArgument(TokenParserException):
    """ Missing mandatory argument """


class ArgumentAlreadyDefined(TokenParserException):
    """ Argument already defined """


class MissingValues(TokenParserException):
    """ Missing values """


# pylint: disable=too-few-public-methods
class ParsedArgs:
    """ Class is a container for parsed arguments """

    def __str__(self) -> str:
        return f"{self.__dict__}"

    def dict(self) -> dict:
        """ Convert to dict """
        return self.__dict__


# pylint: disable=too-many-instance-attributes
@dataclass
class Argument:
    """ Argument representation """

    arg: str
    optional: bool = True
    default: Any | None = None
    arg_type: type | None = None
    help: str | None = None
    min_values: int = 1
    max_values: int = 1
    boolean: bool = False
    validate_fn: Callable[[Any], bool] = lambda _: True

    def __post_init__(self) -> None:
        if self.arg_type is not None and self.arg_type == bool:
            self.boolean = True
        if self.boolean:
            self.arg_type = bool
        self._validate_default()
        if self.boolean:
            self._conf_for_bool()
            return
        if self.arg_type is None and self.default is not None:
            self.arg_type = type(self.default)

    def _conf_for_bool(self) -> None:
        """ Configure argument for boolean """
        self.arg_type = bool
        self.boolean = True
        self.arg_type = bool
        self.default = False
        self.optional = True
        self.min_values = 0
        self.max_values = 0

    def _validate_default(self) -> None:
        """ Validate default value """
        if self.boolean and self.default is not None:
            raise ValueError("Boolean argument can't have default value")
        if self.boolean and not self.optional:
            raise ValueError("Boolean argument can't be mandatory")
        if self.arg_type is not None and self.default is not None:
            if not isinstance(self.default, self.arg_type):
                raise ValueError(
                    "Type mismatch for default value"
                    f"Expected {self.arg_type} got {type(self.default)}"
                )

    def convert_value(
        self,
        values: str | list[str],
    ) -> Any:
        """
        Convert value(s) to the desired type.
        If arg is repeatable, value must be list. method will be recursivelly called for all items.
        If value is list of strings, all args will be split to args and kw_args.
        If value is string, it will be split to args and kw_args.
        Method produces either a single object or if it's repeatable list of objects.
        """
        def split_values_to_args(item: str) -> tuple[list, dict]:
            """ Split items to args and kw_args """
            args: list = []
            kw_args: dict = {}
            if "=" in item:
                key, val = item.split("=", 1)
                kw_args[key] = val
            else:
                args.append(item)
            return args, kw_args

        def validate() -> None:
            """ Validate value """
            # pylint: disable=broad-except
            try:
                if not self.validate_fn(values):
                    raise ValueError(f"Value {values} is invalid ({self.validate_fn})")
            except Exception as exc:
                raise ValueError(f"Validation failed for {values}. {exc}") from exc
            len_values: int = 1 if isinstance(values, str) else len(values)
            if len_values > self.max_values or len_values < self.min_values:
                adj: str = "few" if len_values < self.min_values else "many"
                raise ValueError(
                    f"Too {adj} values for {self.arg}. Expected {self.max_values} got {len_values}"
                )

        if len(values) == 0 and self.boolean:
            return True
        validate()
        args = []
        kw_args = {}
        if self.arg_type is None:
            return values
        if isinstance(values, list):
            for item in values:
                item_args, item_kw_args = split_values_to_args(item)
                args.extend(item_args)
                kw_args.update(item_kw_args)
            return self.arg_type(*args, **kw_args)
        args, kw_args = split_values_to_args(values)
        return self.arg_type(*args, **kw_args)

    def generate_help(self) -> str:
        """ Generate help string """
        help_str = f"{self.arg}"
        if self.optional:
            help_str = f"[{help_str}]"
        if self.arg_type is not None:
            help_str = f"{help_str}{{{self.arg_type.__name__}}}"
        if self.help is not None:
            help_str = f"{help_str}: {self.help}"
        if self.max_values > 0:
            help_str = f"{help_str} [params({self.min_values},{self.max_values})]"
        if self.default is not None and not self.boolean:
            help_str = f"{help_str} (default: {self.default})"
        return help_str


class TokenArgParser:
    """
    Token based argument parser.
    When results are parsed it produces ParsedArgs object.
    Each argument name is an attribute of ParsedArgs object.
    If parsing fails it raises an exception, that is printable to end user.
    """

    def __init__(
        self,
        args: list[Argument],
        drop_tkns: list[str] | None = None,
        logger: logging.Logger | None = None
    ) -> None:
        self._log = logger or logging.getLogger("TokenArgParser")
        self._tokens: dict[str, Argument] = {}
        self._mandatory_token_names: list[str] = []
        self._default_val_token_names: list[str] = []
        for arg in args:
            self.add_argument(arg)
        self._drop_tkns = drop_tkns or []

    def add_argument(self, arg: Argument) -> None:
        """ Add argument """
        name = arg.arg
        if name in self._tokens:
            raise ArgumentAlreadyDefined(
                f"Argument {name}({arg}) is already defined"
            )
        self._tokens[name] = arg
        if not arg.optional:
            self._mandatory_token_names.append(name)
        if arg.default is not None:
            self._default_val_token_names.append(name)

    def _check_mandatory_args(self, parsed_args: ParsedArgs) -> None:
        """ Check if all mandatory arguments are present """
        missed_args_exceptions = []
        for arg_name in self._mandatory_token_names:
            if not hasattr(parsed_args, arg_name):
                missed_args_exceptions.append(
                    f"{arg_name} - {self._tokens[arg_name].generate_help()}"
                )
        if missed_args_exceptions:
            raise MissingMandatoryArgument(
                f"Arguments {missed_args_exceptions} are mandatory",
            )

    def _drop_tokens(self, tokens: list[str]) -> list[str]:
        """ Drop tokens from parsable string """
        return [tkn for tkn in tokens if tkn not in self._drop_tkns]

    def is_arg(self, token: str) -> bool:
        """ Check if token is an argument """
        return token in self._tokens

    def _load_arg_params(self, arg: Argument, tokens: list[str]) -> tuple[Any, int]:
        """ Parse argument and return the val and count of read tokens """
        arg_params: list[Any] = []
        idx: int = 0
        for idx, token in enumerate(tokens):
            if self.is_arg(token):
                break
            if idx >= arg.max_values:
                break
            arg_params.append(token)
        if len(arg_params) < arg.min_values:
            raise MissingValues(
                f"Argument {arg.arg} requires at least {arg.min_values} values"
            )
        return arg_params, idx

    def add_param_to_container(
        self, container: ParsedArgs, arg_name: str, arg_params: list[str]
    ) -> ParsedArgs:
        """ Add parameter to container """
        arg: Argument = self._tokens[arg_name]
        val = arg.convert_value(arg_params)
        if arg_name not in container.dict():
            setattr(
                container,
                arg_name,
                val
            )
            return container
        self._log.warning(
            "Argument %s is already set. Skipping value %s",
            arg_name,
            arg_params
        )
        return container

    def _set_default_values(self, container: ParsedArgs) -> None:
        """ Set default values to container """
        for arg_name in self._default_val_token_names:
            if arg_name not in container.dict():
                setattr(
                    container,
                    arg_name,
                    self._tokens[arg_name].default
                )

    def _parse(self, tokens: list[str]) -> dict[str, list[str]]:
        """ Parse tokens from list to dict of args with params """
        parsed_args: dict[str, list[str]] = {}
        offset: int = 0
        cap: int = len(tokens)
        while offset < cap:
            if self.is_arg(tokens[offset]):
                arg_name: str = tokens[offset]
                offset += 1
                passed_tokens: list[str] = [] if offset >= cap else tokens[offset:]
                parsed_args[arg_name], count = self._load_arg_params(
                    self._tokens[arg_name], passed_tokens
                )
                offset += count
                continue
            self._log.warning(f"Unknown token {tokens[offset]}")
            offset += 1
        return parsed_args

    def parse(
        self, input_string: str, tokenizer: Callable[[str], list[str]] = tokenize_string
    ) -> ParsedArgs:
        """ Parse input string """
        parsed_args: dict[str, list[str]] = self._parse(self._drop_tokens(tokenizer(input_string)))
        container = ParsedArgs()
        for arg_name, arg_params in parsed_args.items():
            arg: Argument = self._tokens[arg_name]
            # pylint: disable=broad-except
            try:
                container = self.add_param_to_container(container, arg_name, arg_params)
            except Exception as exc:
                self._log.error(
                    "Failed to parse %s: %s. Help: %s. Actual err: %s",
                    arg_name,
                    arg_params,
                    arg.generate_help(),
                    exc
                )
                continue
        self._set_default_values(container)
        self._check_mandatory_args(container)
        return container

    def usage(self) -> str:
        """ Generate usage string """
        usage_str = "Usage:\n"
        for arg in self._tokens.values():
            usage_str = f"{usage_str} {arg.generate_help()}\n"
        return usage_str


# if __name__ == "__main__":
#     # Test the function
#     print(tokenize_string("a new set of words"))  # ["a", "new", "set", "of", "words"]
#     print(tokenize_string("a new 'set of' words"))  # ["a", "new", "set of", "words"]
#     print(tokenize_string("a new set\' of words"))  # ["a", "new", "set of", "words"]
#     print(tokenize_string('a new "set of" words'))  # ["a", "new", "set of", "words"]
#
#     parser = TokenArgParser(
#         [
#             Argument("name", optional=False, help="Name of the person"),
#             Argument("age", arg_type=int, help="Age of the person"),
#             Argument("student", arg_type=bool),
#             Argument("address", help="Address of the person", max_values=3),
#             Argument("cool", optional=True, default="and the gang"),
#             Argument(
#                 "phone",
#                 help="Phone number of the person",
#                 max_values=2, optional=False
#             ),
#         ]
#     )
#     print(parser.usage())
#     arguments = parser.parse(
#         "A person has name John, student, and is of age 25. He has an address at place 1. His phone 123"
#     )
#     print(f"{arguments}")
