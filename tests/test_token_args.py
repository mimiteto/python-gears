#! /usr/bin/env python3

""" This module tests the token_args module """

import unittest
from gears.token_args import (
    tokenize_string,
    Argument,
    ParsedArgs
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
