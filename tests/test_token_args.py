#! /usr/bin/env python3

""" This module tests the token_args module """

from typing import Any
import unittest
from unittest.mock import MagicMock
from gears.token_args import (
    ArgumentAlreadyDefined,
    tokenize_string,
    Argument,
    ParsedArgs,
    TokenArgParser,
    MissingMandatoryArgument,
    MissingValues
)


class TestTokenizeString(unittest.TestCase):
    """ Tests the tokenize_string function """

    def test_tokenize_string(self):
        """ Tests the tokenize_string function """
        self.assertEqual(tokenize_string(''), [])
        self.assertEqual(tokenize_string('a'), ['a'])
        self.assertEqual(tokenize_string('a b c'), ['a', 'b', 'c'])
        self.assertEqual(tokenize_string('a "b c"'), ['a', 'b c'])
        self.assertEqual(tokenize_string('a "b c" d'), ['a', 'b c', 'd'])
        self.assertEqual(tokenize_string('a "b c" d. e'), ['a', 'b c', 'd', 'e'])
        self.assertEqual(tokenize_string('a "b c" d. e-f'), ['a', 'b c', 'd', 'e', 'f'])


class TestParseArgs(unittest.TestCase):
    """ Tests the ParsedArg class. We need to check representations only """

    def helper(self, parsed_arg: ParsedArgs, res: dict):
        """ Helper function to test representations """
        self.assertEqual(str(parsed_arg), str(res))
        self.assertEqual(parsed_arg.dict(), res)

    def test(self):
        """ Tests the ParsedArgs class """
        parsed_args = ParsedArgs()
        self.helper(parsed_args, {})

        setattr(parsed_args, 'a', 1)
        self.helper(parsed_args, {'a': 1})


class TestArgument(unittest.TestCase):
    """ Tests the Arguments class """

    def test_bool_args(self):
        """ Tests if argument is correctly configured if boolean """

        with self.subTest("Boolean argument"):
            arg = Argument(
                arg='arg',
                boolean=True,
                help='This is a boolean argument'
            )
            self.assertEqual(arg.arg, 'arg')
            self.assertEqual(arg.arg_type, bool)
            self.assertEqual(arg.default, False)
            self.assertEqual(arg.help, 'This is a boolean argument')
            self.assertTrue(arg.convert_value([]))

        with self.subTest("Implicit boolean argument"):
            arg = Argument(
                arg='arg',
                arg_type=bool,
                help='This is a boolean argument'
            )
            self.assertEqual(arg.arg, 'arg')
            self.assertEqual(arg.arg_type, bool)
            self.assertEqual(arg.default, False)
            self.assertEqual(arg.help, 'This is a boolean argument')

        with self.subTest("Boolean arguments can't have default value"):
            with self.assertRaises(ValueError):
                Argument(
                    arg='arg',
                    arg_type=bool,
                    default='False',
                    help='This is a boolean argument'
                )

        with self.subTest("Booleans can't be mandatory"):
            with self.assertRaises(ValueError):
                Argument(
                    arg='arg',
                    arg_type=bool,
                    optional=False,
                    help='This is a boolean argument'
                )

    # pylint: disable=too-many-statements
    def test_default_parsing(self):
        """ Tests if argument is correctly configured if not boolean """

        with self.subTest("Default should match argument type"):
            with self.assertRaises(ValueError):
                Argument(
                    arg='arg',
                    arg_type=int,
                    default='False',
                    help="Int can't be false"
                )

        with self.subTest("Argument with default value"):
            arg = Argument(
                arg='arg',
                arg_type=int,
                default=1,
                help='This is an argument'
            )
            self.assertEqual(arg.arg, 'arg')
            self.assertEqual(arg.arg_type, int)
            self.assertEqual(arg.default, 1)
            self.assertEqual(arg.help, 'This is an argument')
            self.assertEqual(arg.convert_value(['2']), 2)

        with self.subTest("Mandatory argument"):
            arg = Argument(
                arg='arg',
                arg_type=int,
                optional=False,
                help='This is an argument'
            )
            self.assertEqual(arg.arg, 'arg')
            self.assertEqual(arg.arg_type, int)
            self.assertEqual(arg.default, None)
            self.assertEqual(arg.help, 'This is an argument')
            with self.assertRaises(ValueError):
                arg.convert_value([])

        with self.subTest("Argument with no default value"):
            arg = Argument(
                arg='arg',
                arg_type=int,
                help='This is an argument'
            )
            self.assertEqual(arg.arg, 'arg')
            self.assertEqual(arg.arg_type, int)
            self.assertEqual(arg.default, None)
            self.assertEqual(arg.help, 'This is an argument')
            with self.assertRaises(ValueError):
                arg.convert_value([])

        with self.subTest("Argument with default value and no type"):
            with self.subTest("Int"):
                arg = Argument(
                    arg='arg',
                    default=1,
                    help='This is an argument'
                )
                self.assertEqual(arg.arg, 'arg')
                self.assertEqual(arg.default, 1)
                self.assertEqual(arg.arg_type, int)
                self.assertEqual(arg.help, 'This is an argument')
                self.assertEqual(arg.convert_value(['2']), 2)
            with self.subTest("String"):
                arg = Argument(
                    arg='arg',
                    default='1',
                    help='This is an argument'
                )
                self.assertEqual(arg.arg, 'arg')
                self.assertEqual(arg.default, '1')
                self.assertEqual(arg.arg_type, str)
                self.assertEqual(arg.help, 'This is an argument')
                self.assertEqual(arg.convert_value(['2']), '2')

        with self.subTest("Argument with no default value and no type"):
            arg = Argument(
                arg='arg',
                help='This is an argument'
            )
            self.assertEqual(arg.arg, 'arg')
            self.assertEqual(arg.arg_type, None)
            self.assertEqual(arg.default, None)
            self.assertEqual(arg.help, 'This is an argument')
            self.assertEqual(arg.convert_value(['2']), ['2'])

        with self.subTest("Parsing arg, kw_arg to list"):
            arg = Argument(
                arg='arg',
                help='This is an argument',
                arg_type=list
            )
            self.assertEqual(arg.convert_value(['2']), ['2'])

        with self.subTest("Parsing arg, kw_arg to dict"):
            arg = Argument(
                arg='arg',
                help='This is an argument',
                arg_type=dict
            )
            self.assertEqual(arg.convert_value(['2=4']), {'2': '4'})
            self.assertEqual(arg.convert_value('2=4'), {'2': '4'})

    def test_generate_help(self):
        """ Tests if help is correctly generated """
        with self.subTest("Boolean argument"):
            arg = Argument(
                arg='arg',
                boolean=True,
                help='This is a boolean argument'
            )
            self.assertEqual(arg.generate_help(), '[arg]{bool}: This is a boolean argument')
        with self.subTest("Argument with default value"):
            arg = Argument(
                arg='arg',
                arg_type=int,
                default=1,
                help='This is an argument'
            )
            self.assertEqual(
                arg.generate_help(), '[arg]{int}: This is an argument [params(1,1)] (default: 1)'
            )
        with self.subTest("Mandatory argument"):
            arg = Argument(
                arg='arg',
                arg_type=int,
                optional=False,
                help='This is an argument'
            )
            self.assertEqual(
                arg.generate_help(), 'arg{int}: This is an argument [params(1,1)]'
            )
        with self.subTest("Argument with no default value"):
            arg = Argument(
                arg='arg',
                arg_type=int,
                help='This is an argument'
            )
            self.assertEqual(arg.generate_help(), '[arg]{int}: This is an argument [params(1,1)]')
        with self.subTest("Argument with default value and no type"):
            with self.subTest("Int"):
                arg = Argument(
                    arg='arg',
                    default=1,
                    help='This is an argument'
                )
                self.assertEqual(
                    arg.generate_help(),
                    '[arg]{int}: This is an argument [params(1,1)] (default: 1)'
                )
            with self.subTest("String"):
                arg = Argument(
                    arg='arg',
                    default='1',
                    help='This is an argument'
                )
                self.assertEqual(
                    arg.generate_help(),
                    '[arg]{str}: This is an argument [params(1,1)] (default: 1)'
                )
        with self.subTest("Argument with no default value and no type"):
            arg = Argument(
                arg='arg',
                help='This is an argument'
            )
            self.assertEqual(arg.generate_help(), '[arg]: This is an argument [params(1,1)]')

    def test_convert_value_validations(self):
        """ Tests if convert_value correctly validates the input """
        with self.subTest("Boolean argument"):
            arg = Argument(
                arg='arg',
                boolean=True,
                help='This is a boolean argument'
            )
            with self.assertRaises(ValueError):
                arg.convert_value(['a'])
            with self.assertRaises(ValueError):
                arg.convert_value(['1', '2'])

        with self.subTest("Argument with default value"):
            arg = Argument(
                arg='arg',
                arg_type=int,
                default=1,
                help='This is an argument'
            )
            with self.assertRaises(ValueError):
                arg.convert_value(['a'])
            with self.assertRaises(ValueError):
                arg.convert_value(['1', '2'])

        with self.subTest("Mandatory argument"):
            arg = Argument(
                arg='arg',
                arg_type=int,
                optional=False,
                help='This is an argument'
            )
            with self.assertRaises(ValueError):
                arg.convert_value([])
            with self.assertRaises(ValueError):
                arg.convert_value(['1', '2'])

        with self.subTest("Argument with no default value"):
            arg = Argument(
                arg='arg',
                arg_type=int,
                help='This is an argument'
            )
            with self.assertRaises(ValueError):
                arg.convert_value([])
            with self.assertRaises(ValueError):
                arg.convert_value(['1', '2'])

        with self.subTest("Argument with default value and no type"):
            with self.subTest("Int"):
                arg = Argument(
                    arg='arg',
                    default=1,
                    help='This is an argument'
                )
                with self.assertRaises(ValueError):
                    arg.convert_value(['a'])
                with self.assertRaises(ValueError):
                    arg.convert_value(['1', '2'])
            with self.subTest("String"):
                arg = Argument(
                    arg='arg',
                    default='1',
                    help='This is an argument'
                )
                with self.assertRaises(ValueError):
                    arg.convert_value(['1', '2'])

        with self.subTest("Test supplied validation func"):
            with self.subTest("Return value"):
                arg = Argument(
                    arg='arg',
                    arg_type=int,
                    help='This is an argument',
                    validate_fn=lambda _: False
                )
                with self.assertRaises(ValueError):
                    arg.convert_value(['-1'])
            with self.subTest("Return value"):
                def raise_error(_):
                    raise RuntimeError
                arg = Argument(
                    arg='arg',
                    arg_type=int,
                    help='This is an argument',
                    validate_fn=raise_error
                )
                with self.assertRaises(ValueError):
                    arg.convert_value(['-1'])
        with self.subTest("Argument with no default value and no type"):
            arg = Argument(
                arg='arg',
                help='This is an argument'
            )
            with self.assertRaises(ValueError):
                arg.convert_value(['1', '2'])


class TestTokenArgParser(unittest.TestCase):
    """ Tests the TokenArgParser class """

    def test_usage(self):
        """ Tests the usage of the class """
        with self.subTest("No arguments"):
            parser = TokenArgParser([])
            self.assertEqual(parser.usage(), 'Usage:\n')
        with self.subTest("With arguments"):
            parser = TokenArgParser([
                Argument(
                    arg='arg',
                    arg_type=int,
                    help='This is an argument'
                )
            ])
            self.assertEqual(
                parser.usage(), 'Usage:\n [arg]{int}: This is an argument [params(1,1)]\n'
            )

    def test_add_argument(self):
        """ Tests add_argument method """

        with self.subTest("Standard argument"):
            parser = TokenArgParser([])
            arg = Argument(arg='arg')
            parser.add_argument(arg)
            self.assertEqual(parser.arguments, {arg.arg: arg})
            self.assertEqual(parser.mandatory_args_names, [])
            self.assertEqual(parser.default_args_names, [])

        with self.subTest("Add existing argument"):
            parser = TokenArgParser([])
            arg = Argument(arg='arg')
            second_arg = Argument(arg='arg')
            parser.add_argument(arg)
            with self.assertRaises(ArgumentAlreadyDefined):
                parser.add_argument(second_arg)
            self.assertDictEqual(parser.arguments, {arg.arg: arg})
            self.assertEqual(parser.mandatory_args_names, [])
            self.assertEqual(parser.default_args_names, [])

        with self.subTest("Add mandatory argument"):
            parser = TokenArgParser([])
            arg = Argument(arg='arg', optional=False)
            parser.add_argument(arg)
            self.assertEqual(parser.arguments, {arg.arg: arg})
            self.assertEqual(parser.mandatory_args_names, [arg.arg])
            self.assertEqual(parser.default_args_names, [])

        with self.subTest("Add default argument"):
            parser = TokenArgParser([])
            arg = Argument(arg='arg', default=1)
            parser.add_argument(arg)
            self.assertEqual(parser.arguments, {arg.arg: arg})
            self.assertEqual(parser.mandatory_args_names, [])
            self.assertEqual(parser.default_args_names, [arg.arg])

    def test_is_arg(self):
        """ Tests is_argument method """
        parser = TokenArgParser([])
        arg = Argument(arg='arg')
        parser.add_argument(arg)
        self.assertTrue(parser.is_arg('arg'))
        self.assertFalse(parser.is_arg('arg2'))

    def test_add_param_to_container(self):
        """ Tests add_param_to_container method """
        mock_logger = MagicMock()
        parser = TokenArgParser([Argument(arg='arg')], logger=mock_logger)
        container = ParsedArgs()
        with self.subTest("Add arg to container"):
            parser.add_param_to_container(container, 'arg', ["1"])
            self.assert_container_params(container, 'arg', ["1"])
        with self.subTest("Add arg to container"):
            parser.add_param_to_container(container, 'arg', ["3"])
            self.assert_container_params(container, 'arg', ["1"])
            mock_logger.warning.assert_called_once_with(
                'Argument %s is already set. Skipping value %s', 'arg', ['3']
            )

    def assert_container_params(self, container: ParsedArgs, name: str, val: Any) -> None:
        """ Helper function to check container params """
        self.assertTrue(hasattr(container, name))
        self.assertEqual(getattr(container, name), val)

    def test_example(self):
        """ This test case is an example usage """
        # pylint: disable=line-too-long
        arg_string = "A person has name John, student, and is of age 25. He has an address at place 1. His phone 123"
        parser = TokenArgParser(
            [
                Argument("name", optional=False, help="Name of the person"),
                Argument("age", arg_type=int, help="Age of the person"),
                Argument("student", arg_type=bool),
                Argument("address", help="Address of the person", max_values=3),
                Argument("cool", optional=True, default="and the gang"),
                Argument(
                    "phone",
                    help="Phone number of the person",
                    max_values=2, optional=False
                ),
            ]
        )
        print(parser.usage())
        parsed = parser.parse(arg_string)
        self.assert_container_params(parsed, 'name', ['John'])  # Mandatory arg
        self.assert_container_params(parsed, 'student', True)
        self.assert_container_params(parsed, 'age', 25)
        self.assert_container_params(
            parsed, 'address', ['at', 'place', '1']
        )  # Multiple params for arg
        self.assert_container_params(parsed, 'phone', ['123'])  # Mandatory value
        self.assert_container_params(parsed, 'cool', 'and the gang')  # Default value

        with self.subTest("Phone was added as tel, so it's not detected"):
            with self.assertRaises(MissingMandatoryArgument):
                parser.parse("A person has age 25. He has an address at place 1. His tel 123")

        with self.subTest("There is no phone number"):
            with self.assertRaises(MissingValues):
                parser.parse("A person has age 25. He has an address at place 1. His phone")

        with self.subTest(
            "During argument parsing there is exception that was not handled within arg"
        ):
            mock_arg = MagicMock()
            mock_arg.arg = 'arg'
            mock_arg.convert_value.side_effect = Exception
            mock_arg.max_values = 1
            mock_arg.min_values = 1
            mock_logger = MagicMock()
            parser = TokenArgParser([mock_arg], logger=mock_logger)
            parser.parse("arg 123")
            mock_logger.error.assert_called_once()
