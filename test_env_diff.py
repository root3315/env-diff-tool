#!/usr/bin/env python3
"""Unit tests for env-diff-tool environment parsing."""

import os
import tempfile
import unittest
from env_diff import (
    parse_env_file,
    parse_env_string,
    compare_envs,
    filter_env_vars,
    merge_envs,
)


class TestParseEnvString(unittest.TestCase):
    """Tests for parse_env_string function."""

    def test_empty_string(self):
        result = parse_env_string("")
        self.assertEqual(result, {})

    def test_whitespace_only(self):
        result = parse_env_string("   \n  \n  ")
        self.assertEqual(result, {})

    def test_single_variable(self):
        result = parse_env_string("FOO=bar")
        self.assertEqual(result, {"FOO": "bar"})

    def test_multiple_variables(self):
        result = parse_env_string("FOO=bar\nBAZ=qux")
        self.assertEqual(result, {"FOO": "bar", "BAZ": "qux"})

    def test_ignores_comments(self):
        result = parse_env_string("# comment\nFOO=bar\n# another comment")
        self.assertEqual(result, {"FOO": "bar"})

    def test_ignores_empty_lines(self):
        result = parse_env_string("FOO=bar\n\nBAZ=qux\n")
        self.assertEqual(result, {"FOO": "bar", "BAZ": "qux"})

    def test_ignores_lines_without_equals(self):
        result = parse_env_string("FOO=bar\nINVALID\nBAZ=qux")
        self.assertEqual(result, {"FOO": "bar", "BAZ": "qux"})

    def test_strips_whitespace_from_key(self):
        result = parse_env_string("  FOO  =bar")
        self.assertEqual(result, {"FOO": "bar"})

    def test_strips_whitespace_from_value(self):
        result = parse_env_string("FOO=  bar  ")
        self.assertEqual(result, {"FOO": "bar"})

    def test_preserves_equals_in_value(self):
        result = parse_env_string("URL=http://example.com?a=1&b=2")
        self.assertEqual(result, {"URL": "http://example.com?a=1&b=2"})

    def test_empty_value(self):
        result = parse_env_string("FOO=")
        self.assertEqual(result, {"FOO": ""})

    def test_value_with_spaces(self):
        result = parse_env_string("FOO=hello world")
        self.assertEqual(result, {"FOO": "hello world"})


class TestParseEnvFile(unittest.TestCase):
    """Tests for parse_env_file function."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def create_temp_file(self, content):
        path = os.path.join(self.temp_dir, "test.env")
        with open(path, "w") as f:
            f.write(content)
        return path

    def test_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            parse_env_file("/nonexistent/path/.env")

    def test_simple_variables(self):
        path = self.create_temp_file("FOO=bar\nBAZ=qux")
        result = parse_env_file(path)
        self.assertEqual(result, {"FOO": "bar", "BAZ": "qux"})

    def test_ignores_comments(self):
        path = self.create_temp_file("# comment\nFOO=bar\n# another")
        result = parse_env_file(path)
        self.assertEqual(result, {"FOO": "bar"})

    def test_ignores_empty_lines(self):
        path = self.create_temp_file("FOO=bar\n\nBAZ=qux\n")
        result = parse_env_file(path)
        self.assertEqual(result, {"FOO": "bar", "BAZ": "qux"})

    def test_single_quoted_value(self):
        path = self.create_temp_file("FOO='bar'")
        result = parse_env_file(path)
        self.assertEqual(result, {"FOO": "bar"})

    def test_double_quoted_value(self):
        path = self.create_temp_file('FOO="bar"')
        result = parse_env_file(path)
        self.assertEqual(result, {"FOO": "bar"})

    def test_single_quoted_value_with_spaces(self):
        path = self.create_temp_file("FOO='hello world'")
        result = parse_env_file(path)
        self.assertEqual(result, {"FOO": "hello world"})

    def test_double_quoted_value_with_spaces(self):
        path = self.create_temp_file('FOO="hello world"')
        result = parse_env_file(path)
        self.assertEqual(result, {"FOO": "hello world"})

    def test_multiline_value_double_quotes(self):
        content = 'FOO="line1\nline2\nline3"'
        path = self.create_temp_file(content)
        result = parse_env_file(path)
        self.assertEqual(result, {"FOO": "line1\nline2\nline3"})

    def test_multiline_value_single_quotes(self):
        content = "FOO='line1\nline2\nline3'"
        path = self.create_temp_file(content)
        result = parse_env_file(path)
        self.assertEqual(result, {"FOO": "line1\nline2\nline3"})

    def test_multiline_value_separate_lines(self):
        content = '''FOO="
line1
line2
line3"
'''
        path = self.create_temp_file(content)
        result = parse_env_file(path)
        self.assertEqual(result, {"FOO": "\nline1\nline2\nline3"})

    def test_empty_value(self):
        path = self.create_temp_file("FOO=")
        result = parse_env_file(path)
        self.assertEqual(result, {"FOO": ""})

    def test_value_with_equals_sign(self):
        path = self.create_temp_file("URL=http://example.com?a=1")
        result = parse_env_file(path)
        self.assertEqual(result, {"URL": "http://example.com?a=1"})

    def test_preserves_order(self):
        path = self.create_temp_file("C=3\nA=1\nB=2")
        result = parse_env_file(path)
        keys = list(result.keys())
        self.assertEqual(keys, ["C", "A", "B"])


class TestCompareEnvs(unittest.TestCase):
    """Tests for compare_envs function."""

    def test_identical_envs(self):
        env1 = {"FOO": "bar", "BAZ": "qux"}
        env2 = {"FOO": "bar", "BAZ": "qux"}
        diff = compare_envs(env1, env2)
        self.assertEqual(diff["only_in_first"], {})
        self.assertEqual(diff["only_in_second"], {})
        self.assertEqual(diff["modified"], {})
        self.assertEqual(diff["unchanged"], ["BAZ", "FOO"])

    def test_only_in_first(self):
        env1 = {"FOO": "bar", "ONLY1": "a"}
        env2 = {"FOO": "bar"}
        diff = compare_envs(env1, env2)
        self.assertEqual(diff["only_in_first"], {"ONLY1": "a"})
        self.assertEqual(diff["only_in_second"], {})

    def test_only_in_second(self):
        env1 = {"FOO": "bar"}
        env2 = {"FOO": "bar", "ONLY2": "b"}
        diff = compare_envs(env1, env2)
        self.assertEqual(diff["only_in_first"], {})
        self.assertEqual(diff["only_in_second"], {"ONLY2": "b"})

    def test_modified_values(self):
        env1 = {"FOO": "bar"}
        env2 = {"FOO": "changed"}
        diff = compare_envs(env1, env2)
        self.assertEqual(diff["modified"]["FOO"]["old"], "bar")
        self.assertEqual(diff["modified"]["FOO"]["new"], "changed")

    def test_complex_diff(self):
        env1 = {"A": "1", "B": "2", "C": "3"}
        env2 = {"B": "changed", "C": "3", "D": "4"}
        diff = compare_envs(env1, env2)
        self.assertEqual(diff["only_in_first"], {"A": "1"})
        self.assertEqual(diff["only_in_second"], {"D": "4"})
        self.assertEqual(diff["modified"]["B"]["old"], "2")
        self.assertEqual(diff["modified"]["B"]["new"], "changed")
        self.assertEqual(diff["unchanged"], ["C"])


class TestFilterEnvVars(unittest.TestCase):
    """Tests for filter_env_vars function."""

    def test_no_filter(self):
        env = {"FOO": "bar", "BAZ": "qux"}
        result = filter_env_vars(env)
        self.assertEqual(result, env)

    def test_include_pattern(self):
        env = {"DB_HOST": "localhost", "DB_PORT": "5432", "APP_NAME": "test"}
        result = filter_env_vars(env, pattern="DB_")
        self.assertEqual(result, {"DB_HOST": "localhost", "DB_PORT": "5432"})

    def test_exclude_pattern(self):
        env = {"DB_HOST": "localhost", "DB_PASSWORD": "secret", "APP_NAME": "test"}
        result = filter_env_vars(env, exclude_pattern="PASSWORD")
        self.assertEqual(result, {"DB_HOST": "localhost", "APP_NAME": "test"})

    def test_include_and_exclude(self):
        env = {"DB_HOST": "localhost", "DB_PASSWORD": "secret", "APP_NAME": "test"}
        result = filter_env_vars(env, pattern="DB_", exclude_pattern="PASSWORD")
        self.assertEqual(result, {"DB_HOST": "localhost"})


class TestMergeEnvs(unittest.TestCase):
    """Tests for merge_envs function."""

    def test_merge_empty_first(self):
        env1 = {}
        env2 = {"FOO": "bar"}
        result = merge_envs(env1, env2)
        self.assertEqual(result, {"FOO": "bar"})

    def test_merge_empty_second(self):
        env1 = {"FOO": "bar"}
        env2 = {}
        result = merge_envs(env1, env2)
        self.assertEqual(result, {"FOO": "bar"})

    def test_merge_prefers_second(self):
        env1 = {"FOO": "bar", "A": "1"}
        env2 = {"FOO": "changed", "B": "2"}
        result = merge_envs(env1, env2, prefer_second=True)
        self.assertEqual(result["FOO"], "changed")
        self.assertEqual(result["A"], "1")
        self.assertEqual(result["B"], "2")

    def test_merge_prefers_first(self):
        env1 = {"FOO": "bar", "A": "1"}
        env2 = {"FOO": "changed", "B": "2"}
        result = merge_envs(env1, env2, prefer_second=False)
        self.assertEqual(result["FOO"], "bar")
        self.assertEqual(result["A"], "1")
        self.assertEqual(result["B"], "2")


if __name__ == "__main__":
    unittest.main()
