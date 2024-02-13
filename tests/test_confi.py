#! /usr/bin/env python3

""" Tests for the configuration loader utility """

import unittest
import os

from unittest.mock import patch, call

from gears.confi import Confi


class TestConfi(unittest.TestCase):
    """ Tests for the configuration loader utility """

    def setUp(self):
        self.config_loader = Confi()

    def test_register_conf_stub(self):
        """ Tests for the register_conf_stub method """
        with self.subTest("Valid jsonpath"):
            path = "$.test"
            schema_def = {"type": "object"}
            self.config_loader.register_conf_stub("a", path, schema_def)
            self.assertEqual(self.config_loader.stubs["a"], (path, schema_def))

        with self.subTest("Invalid jsonpath"):
            path = "set set"
            schema_def = {"type": "object"}
            with self.assertRaises(ValueError):
                self.config_loader.register_conf_stub("a", path, schema_def)

    def test_validate(self):
        """ Tests for the validate method """
        path = "$.test"
        schema_def = {"type": "object"}
        self.config_loader.register_conf_stub("class", path, schema_def)
        with self.subTest("Valid configuration"):
            self.config_loader.conf_values = {"test": {"key": "value"}}
            self.assertIsNone(self.config_loader.validate())
        with self.subTest("Invalid configuration"):
            self.config_loader.conf_values = {"test": "not_an_object"}
            with self.assertRaises(ValueError):
                self.config_loader.validate()
        with self.subTest("Invalid jsonpath"):
            self.config_loader.stubs["class"] = ("set set", schema_def)
            with self.assertRaises(ValueError):
                self.config_loader.validate()

    def test_load_env_var(self):
        """ Tests for the load_env_var method """
        with self.subTest("Valid environment variable"):
            os.environ["NO_SUCH_ENV_VAR"] = "val"
            self.assertEqual(Confi.load_env_var("NO_SUCH_ENV_VAR"), "val")
        with self.subTest("Invalid environment variable"):
            with self.assertRaises(KeyError):
                Confi.load_env_var("INVALID_ENV_VAR")

    def test_load_file(self):
        """ Tests for the load_file method """
        with patch("builtins.open") as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = "file_content"
            self.assertEqual(Confi.load_file("file_path"), "file_content")

    def test_load_json(self):
        """ Tests for the load_json method """
        self.assertEqual(Confi.load_json('{"key": "value"}'), {"key": "value"})

    def test_load_yaml(self):
        """ Tests for the load_yaml method """
        self.assertEqual(Confi.load_yaml("key: value"), {"key": "value"})

    # def test_needs_preload(self):
    #     """ Tests for the needs_preload method """
    #     with self.subTest("Empty config"):
    #         self.assertFalse(self.config_loader.needs_preload({}))
    #     with self.subTest("Preload not needed"):
    #         self.assertFalse(self.config_loader.needs_preload({
    #             "key": "value",
    #             "key2": ["value2"],
    #             "key3": {"key4": "value3"}
    #         }))
    #     with self.subTest("Preload needed - env"):
    #         self.assertTrue(self.config_loader.needs_preload({
    #             "key": "env://HELLO",
    #         }))
    #     with self.subTest("Preload needed - file"):
    #         self.assertTrue(self.config_loader.needs_preload({
    #             "key2": "file://file"
    #         }))
    #     with self.subTest("Preload needed - file - absolute path"):
    #         self.assertTrue(self.config_loader.needs_preload({
    #             "key2": "file://file"
    #         }))
    #     with self.subTest("Preload needed - json"):
    #         self.assertTrue(self.config_loader.needs_preload({
    #             "key3": "json://json"
    #         }))
    #     with self.subTest("Preload needed - yaml"):
    #         self.assertTrue(self.config_loader.needs_preload({
    #             "key4": "yaml://yaml"
    #         }))
    #     with self.subTest("Preload needed - nested"):
    #         self.assertTrue(self.config_loader.needs_preload({
    #             "rec": {"key5": "yaml://yaml"}
    #         }))
    #     with self.subTest("Preload needed - nested in list"):
    #         self.assertTrue(self.config_loader.needs_preload({
    #             "rec": ["item", "yaml://yaml"]
    #         }))
    #     with self.subTest("Preload for int"):
    #         self.assertFalse(self.config_loader.needs_preload({
    #             "key": 1
    #         }))
    #     with self.subTest("Preload for float"):
    #         self.assertFalse(self.config_loader.needs_preload({
    #             "key": 1.0
    #         }))

    def test_process_value(self):
        """ Tests for the process_value method """
        os.environ["HELLO"] = "value"
        with self.subTest("Process string"):
            self.assertEqual(Confi.process_value("env://HELLO"), "value")
        with self.subTest("Process dict"):
            self.assertEqual(Confi.process_value({"key": "env://HELLO"}), {"key": "value"})
        with self.subTest("Process list"):
            self.assertEqual(Confi.process_value(["env://HELLO"]), ["value"])
        with patch("builtins.open") as mock_open:
            mock_open.return_value.__enter__.return_value.read.side_effect = [
                "file_content",
                '{"key": "value"}',
                "key: value",
                '{"key": "yaml://test123"}',
                'file://file',
                'val1'
            ]
            with self.subTest("Process file"):
                self.assertEqual(Confi.process_value("file://file"), "file_content")
            with self.subTest("Process json"):
                self.assertEqual(Confi.process_value("json://json"), {"key": "value"})
            with self.subTest("Process yaml"):
                self.assertEqual(Confi.process_value("yaml://yaml"), {"key": "value"})
            with self.subTest("Process nested"):
                self.assertEqual(
                    Confi.process_value({"key": "yaml://yaml"}),
                    {"key": {"key": "val1"}}
                )
            # pylint: disable=unnecessary-dunder-call
            mock_open.assert_has_calls([
                call("file", "r", encoding="utf-8"),
                call().__enter__(),
                call().__enter__().read(),
                call().__exit__(None, None, None),
                call("json", "r", encoding="utf-8"),
                call().__enter__(),
                call().__enter__().read(),
                call().__exit__(None, None, None),
                call("yaml", "r", encoding="utf-8"),
                call().__enter__(),
                call().__enter__().read(),
                call().__exit__(None, None, None),
                call("yaml", "r", encoding="utf-8"),
                call().__enter__(),
                call().__enter__().read(),
                call().__exit__(None, None, None),
                call("test123", "r", encoding="utf-8"),
                call().__enter__(),
                call().__enter__().read(),
                call().__exit__(None, None, None),
                call("file", "r", encoding="utf-8"),
                call().__enter__(),
                call().__enter__().read(),
                call().__exit__(None, None, None),
            ])

    def test_preload_values(self):
        """ Tests for the preload_values method """
        with patch("gears.confi.Confi.load_yaml") as mock_load_yaml, \
                patch("gears.confi.Confi.process_value", return_value={"key": "value"}):
            mock_load_yaml.return_value = {"key": "yaml://yaml"}
            self.config_loader.load_values("conf")
            self.assertEqual(self.config_loader.conf_values, {"key": "value"})


if __name__ == '__main__':  # pragma: no cover
    unittest.main(verbosity=2)
