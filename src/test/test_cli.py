"""
Unit tests for src/core/files/cli.py

Standard library only, PLUS click's own testing utilities
(click.testing.CliRunner / click.testing.CliRunner.isolation). click is
not a "new" third-party dependency introduced by the tests -- cli.py
itself already requires click to run at all, so anyone able to import
cli.py already has click installed. No other third-party package is
imported anywhere in this file.

Path setup mirrors test_series.py / test_library.py: this file lives in
src/test/files, cli.py lives in src/core/files, so that directory is
added to sys.path before importing.
"""
import io
import os
import sys
import json
import unittest
from contextlib import redirect_stdout, redirect_stderr
from unittest.mock import patch, mock_open, MagicMock, call

import click
from click.testing import CliRunner

CORE_FILES_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "core")
)
if CORE_FILES_DIR not in sys.path:
    sys.path.insert(0, CORE_FILES_DIR)

import cli as cli_module  # noqa: E402
from cli import (  # noqa: E402
    mask_path,
    unmask_path,
    load_default_profile,
    set_default_profile,
)
from series import Series, Status  # noqa: E402
from library import Library  # noqa: E402
from api import Api  # noqa: E402


def make_store(**overrides):
    store = {
        "id": 1,
        "name": "Breaking Bad",
        "num_seasons": 3,
        "num_episodes": 10,
        "stopped_at": [1, 5],
        "descr": "<p>a show</p>",
        "platform": "streaming",
        "premiered": "2020",
        "ended": None,
        "tags": ["drama"],
    }
    store.update(overrides)
    return store


# ---------------------------------------------------------------------------
# mask_path / unmask_path
# ---------------------------------------------------------------------------

class TestMaskPath(unittest.TestCase):
    """mask_path(): pure string transform."""

    def test_mask_path_wraps_name_with_storage_dir_and_json_extension(self):
        self.assertEqual(mask_path("myshow"), "../storage/myshow.json")

    def test_mask_path_with_empty_name(self):
        self.assertEqual(mask_path(""), "../storage/.json")


class TestUnmaskPath(unittest.TestCase):
    """unmask_path(): reverses mask_path()."""

    def test_unmask_path_strips_prefix_and_extension(self):
        self.assertEqual(unmask_path("../storage/myshow.json"), "myshow")

    def test_unmask_path_round_trips_with_mask_path(self):
        name = "another_profile"
        self.assertEqual(unmask_path(mask_path(name)), name)


# ---------------------------------------------------------------------------
# load_default_profile / set_default_profile
# ---------------------------------------------------------------------------

class TestLoadDefaultProfile(unittest.TestCase):
    """load_default_profile(): success branch, FileNotFoundError branch,
    JSONDecodeError branch, and the 'key missing' case (which returns
    None via dict.get rather than raising)."""

    @patch("builtins.open", new_callable=mock_open,
           read_data=json.dumps({"path": "../storage/myshow.json"}))
    def test_returns_path_when_config_present(self, mock_file):
        result = load_default_profile()
        self.assertEqual(result, "../storage/myshow.json")

    @patch("builtins.open", side_effect=FileNotFoundError)
    def test_missing_config_file_returns_empty_string(self, mock_file):
        result = load_default_profile()
        self.assertEqual(result, "")

    @patch("builtins.open", new_callable=mock_open, read_data="not valid json{{{")
    def test_corrupt_json_returns_empty_string(self, mock_file):
        result = load_default_profile()
        self.assertEqual(result, "")

    @patch("builtins.open", new_callable=mock_open, read_data=json.dumps({}))
    def test_missing_path_key_returns_none(self, mock_file):
        # data.get("path") on a dict with no "path" key returns None
        # rather than raising -- exercised separately from the "" case.
        result = load_default_profile()
        self.assertIsNone(result)


class TestSetDefaultProfile(unittest.TestCase):
    """set_default_profile(): writes {"path": path} as JSON."""

    def test_writes_expected_json_payload(self):
        m = mock_open()
        with patch("builtins.open", m):
            set_default_profile("myshow")
        written = "".join(c.args[0] for c in m().write.call_args_list)
        self.assertEqual(json.loads(written), {"path": "myshow"})


# ---------------------------------------------------------------------------
# load_profile()
# ---------------------------------------------------------------------------

class TestLoadProfile(unittest.TestCase):
    """load_profile(): the 'create new profile' branch, the 'load
    default, no default set' branch, the 'load default, default set'
    branch, and the FileNotFoundError-retry loop."""

    @patch("cli.click.prompt")
    @patch("cli.click.confirm")
    def test_create_new_profile_branch(self, mock_confirm, mock_prompt):
        mock_confirm.return_value = True
        mock_prompt.return_value = "newshow"
        lib = load_profile_under_test = cli_module.load_profile()
        self.assertIsInstance(lib, Library)
        self.assertEqual(lib.path, "../storage/newshow.json")
        mock_prompt.assert_called_once_with("Enter new profile name")

    @patch("cli.Library")
    @patch("cli.load_default_profile")
    @patch("cli.click.prompt")
    @patch("cli.click.confirm")
    def test_load_existing_profile_no_default_set(
        self, mock_confirm, mock_prompt, mock_load_default, MockLibrary
    ):
        mock_confirm.return_value = False
        mock_load_default.return_value = ""
        mock_prompt.return_value = "myshow"
        mock_lib_instance = MagicMock()
        MockLibrary.return_value = mock_lib_instance

        result = cli_module.load_profile()

        mock_prompt.assert_called_once_with("Enter profile name")
        MockLibrary.assert_called_once_with(path="../storage/myshow.json")
        self.assertIs(result, mock_lib_instance)

    @patch("cli.Library")
    @patch("cli.load_default_profile")
    @patch("cli.click.prompt")
    @patch("cli.click.confirm")
    def test_load_existing_profile_with_default_set(
        self, mock_confirm, mock_prompt, mock_load_default, MockLibrary
    ):
        mock_confirm.return_value = False
        mock_load_default.return_value = "../storage/existing.json"
        mock_prompt.return_value = "../storage/existing.json"
        mock_lib_instance = MagicMock()
        MockLibrary.return_value = mock_lib_instance

        cli_module.load_profile()

        mock_prompt.assert_called_once_with(
            "(ENTER for default) Enter profile name",
            default="../storage/existing.json",
        )

    @patch("cli.Library")
    @patch("cli.load_default_profile")
    @patch("cli.click.prompt")
    @patch("cli.click.confirm")
    def test_file_not_found_retries_until_success(
        self, mock_confirm, mock_prompt, mock_load_default, MockLibrary
    ):
        mock_confirm.return_value = False
        mock_load_default.return_value = ""
        mock_prompt.side_effect = ["badpath", "goodpath"]
        mock_lib_instance = MagicMock()
        MockLibrary.side_effect = [FileNotFoundError("nope"), mock_lib_instance]

        result = cli_module.load_profile()

        self.assertEqual(MockLibrary.call_count, 2)
        self.assertIs(result, mock_lib_instance)


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------

class TestMain(unittest.TestCase):
    """main(): wires load_profile() straight into user_loop()."""

    @patch("cli.user_loop")
    @patch("cli.load_profile")
    def test_main_calls_load_profile_then_user_loop(self, mock_load_profile, mock_user_loop):
        mock_load_profile.return_value = "the-profile"
        cli_module.main()
        mock_load_profile.assert_called_once_with()
        mock_user_loop.assert_called_once_with("the-profile")


# ---------------------------------------------------------------------------
# user_loop()
# ---------------------------------------------------------------------------

class TestUserLoop(unittest.TestCase):
    """user_loop(): exit immediately, a ClickException raised by a
    subcommand (caught and shown), a click.exceptions.Exit raised by a
    subcommand (silently absorbed), and a subcommand completing
    normally -- and in every case profile.save() runs once at the end."""

    @patch("cli.click.prompt")
    def test_exit_immediately_saves_profile(self, mock_prompt):
        mock_prompt.return_value = "exit"
        profile = MagicMock()
        profile.path = "../storage/x.json"
        buf = io.StringIO()
        with redirect_stdout(buf):
            cli_module.user_loop(profile)
        profile.save.assert_called_once_with()
        self.assertIn("Changes saved into ../storage/x.json.", buf.getvalue())

    @patch.object(cli_module.cli, "main")
    @patch("cli.click.prompt")
    def test_click_exception_is_caught_and_shown(self, mock_prompt, mock_cli_main):
        mock_prompt.side_effect = ["list", "exit"]
        mock_cli_main.side_effect = click.ClickException("boom")
        profile = MagicMock()
        profile.path = "../storage/x.json"
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            cli_module.user_loop(profile)
        self.assertIn("boom", out.getvalue() + err.getvalue())
        profile.save.assert_called_once_with()

    @patch.object(cli_module.cli, "main")
    @patch("cli.click.prompt")
    def test_click_exit_exception_is_absorbed_silently(self, mock_prompt, mock_cli_main):
        mock_prompt.side_effect = ["list", "exit"]
        mock_cli_main.side_effect = click.exceptions.Exit(0)
        profile = MagicMock()
        profile.path = "../storage/x.json"
        buf = io.StringIO()
        with redirect_stdout(buf):
            cli_module.user_loop(profile)  # must not raise
        profile.save.assert_called_once_with()

    @patch.object(cli_module.cli, "main")
    @patch("cli.click.prompt")
    def test_subcommand_completes_normally(self, mock_prompt, mock_cli_main):
        mock_prompt.side_effect = ["update-all", "exit"]
        mock_cli_main.return_value = None
        profile = MagicMock()
        profile.path = "../storage/x.json"
        buf = io.StringIO()
        with redirect_stdout(buf):
            cli_module.user_loop(profile)
        mock_cli_main.assert_called_once_with(
            args=["update-all"], obj=profile, standalone_mode=False
        )
        profile.save.assert_called_once_with()


# ---------------------------------------------------------------------------
# @cli.command "list"
# ---------------------------------------------------------------------------

class TestListSeriesCommand(unittest.TestCase):
    """list_series: no matches, matches displayed + skip menu (-1),
    and matches displayed + selecting an index enters series_menu."""

    def setUp(self):
        self.runner = CliRunner()

    def test_no_matches_prints_message(self):
        profile = MagicMock()
        profile.get_with.return_value = []
        result = self.runner.invoke(
            cli_module.cli, ["list"], obj=profile, input="\n\nn\n\n"
        )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("No series found.", result.output)

    def test_matches_are_sorted_and_displayed_then_skip_index(self):
        older = Series(make_store(id=1, name="Older Show", premiered="2010"))
        newer = Series(make_store(id=2, name="Newer Show", premiered="2022"))
        profile = MagicMock()
        profile.get_with.return_value = [older, newer]
        # tag="" (skip), updated confirm -> "n", keyword="" (skip), index="-1"
        result = self.runner.invoke(
            cli_module.cli, ["list"], obj=profile, input="\nn\n\n-1\n"
        )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Newer Show", result.output)
        self.assertIn("Older Show", result.output)
        # newest-first: "Newer Show" must appear before "Older Show"
        self.assertLess(
            result.output.index("Newer Show"), result.output.index("Older Show")
        )

    @patch.object(Api, "get_data")
    def test_selecting_index_enters_series_menu(self, mock_get_data):
        serie = Series(make_store(id=1, name="Breaking Bad"))
        profile = MagicMock()
        profile.get_with.return_value = [serie]
        # tag/updated/keyword skipped, pick index 0, then "back" out of the menu
        result = self.runner.invoke(
            cli_module.cli, ["list"], obj=profile, input="\nn\n\n0\nback\n"
        )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("BREAKING BAD", result.output)  # series_menu header


# ---------------------------------------------------------------------------
# @cli.command "add"
# ---------------------------------------------------------------------------

class TestAddSeriesCommand(unittest.TestCase):
    """add_series: no search results, skip index (-1), and choosing a
    result adds it to the profile."""

    def setUp(self):
        self.runner = CliRunner()

    @patch.object(Api, "search")
    def test_no_search_results_prints_message(self, mock_search):
        mock_search.return_value = []
        profile = MagicMock()
        result = self.runner.invoke(
            cli_module.cli, ["add"], obj=profile, input="some query\n"
        )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("No series found.", result.output)
        profile.add_series.assert_not_called()

    @patch.object(Api, "search")
    def test_skip_index_does_not_add(self, mock_search):
        mock_search.return_value = [make_store(id=1, name="Some Show")]
        profile = MagicMock()
        result = self.runner.invoke(
            cli_module.cli, ["add"], obj=profile, input="some query\n-1\n"
        )
        self.assertEqual(result.exit_code, 0)
        profile.add_series.assert_not_called()

    @patch.object(Api, "search")
    def test_selecting_result_adds_series(self, mock_search):
        mock_search.return_value = [
            make_store(id=1, name="Show A"),
            make_store(id=2, name="Show B"),
        ]
        profile = MagicMock()
        result = self.runner.invoke(
            cli_module.cli, ["add"], obj=profile, input="some query\n1\n"
        )
        self.assertEqual(result.exit_code, 0)
        profile.add_series.assert_called_once()
        added = profile.add_series.call_args.args[0]
        self.assertEqual(added.name, "Show B")


# ---------------------------------------------------------------------------
# @cli.command "set-profile"
# ---------------------------------------------------------------------------

class TestSetProfileCommand(unittest.TestCase):
    def setUp(self):
        self.runner = CliRunner()

    @patch("cli.set_default_profile")
    def test_sets_default_profile_from_current_path(self, mock_set_default):
        profile = MagicMock()
        profile.path = "../storage/myshow.json"
        result = self.runner.invoke(cli_module.cli, ["set-profile"], obj=profile)
        self.assertEqual(result.exit_code, 0)
        mock_set_default.assert_called_once_with("myshow")


# ---------------------------------------------------------------------------
# @cli.command "set-path"
# ---------------------------------------------------------------------------

class TestSetPathCommand(unittest.TestCase):
    def setUp(self):
        self.runner = CliRunner()

    def test_sets_new_masked_path_on_profile(self):
        profile = MagicMock()
        result = self.runner.invoke(
            cli_module.cli, ["set-path"], obj=profile, input="newshow\n"
        )
        self.assertEqual(result.exit_code, 0)
        profile.set_path.assert_called_once_with("../storage/newshow.json")


# ---------------------------------------------------------------------------
# @cli.command "update-all" / "clear-updated" / "caught-up-all" / "get-tags"
# ---------------------------------------------------------------------------

class TestSimpleDelegatingCommands(unittest.TestCase):
    """Each of these just calls one Library method and prints a status
    line; verified independently."""

    def setUp(self):
        self.runner = CliRunner()

    def test_update_all_calls_check_for_updates_all(self):
        profile = MagicMock()
        result = self.runner.invoke(cli_module.cli, ["update-all"], obj=profile)
        self.assertEqual(result.exit_code, 0)
        profile.check_for_updates_all.assert_called_once_with()
        self.assertIn("Updates completed", result.output)

    def test_clear_updated_calls_clear_updated(self):
        profile = MagicMock()
        result = self.runner.invoke(cli_module.cli, ["clear-updated"], obj=profile)
        self.assertEqual(result.exit_code, 0)
        profile.clear_updated.assert_called_once_with()

    def test_caught_up_all_calls_all_caught_up_all(self):
        profile = MagicMock()
        result = self.runner.invoke(cli_module.cli, ["caught-up-all"], obj=profile)
        self.assertEqual(result.exit_code, 0)
        profile.all_caught_up_all.assert_called_once_with()

    def test_get_tags_prints_tags(self):
        profile = MagicMock()
        profile.get_tags.return_value = ["drama", "comedy"]
        result = self.runner.invoke(cli_module.cli, ["get-tags"], obj=profile)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("drama", result.output)
        self.assertIn("comedy", result.output)


# ---------------------------------------------------------------------------
# @cli.command "reset-all"
# ---------------------------------------------------------------------------

class TestResetAllCommand(unittest.TestCase):
    """reset-all: confirm=True runs reset_all() and prints 'Done.',
    confirm=False skips it and prints 'Cancelled.'."""

    def setUp(self):
        self.runner = CliRunner()

    def test_confirmed_resets_all(self):
        profile = MagicMock()
        result = self.runner.invoke(
            cli_module.cli, ["reset-all"], obj=profile, input="y\n"
        )
        self.assertEqual(result.exit_code, 0)
        profile.reset_all.assert_called_once_with()
        self.assertIn("Done.", result.output)

    def test_declined_does_not_reset(self):
        profile = MagicMock()
        result = self.runner.invoke(
            cli_module.cli, ["reset-all"], obj=profile, input="n\n"
        )
        self.assertEqual(result.exit_code, 0)
        profile.reset_all.assert_not_called()
        self.assertIn("Cancelled.", result.output)


# ---------------------------------------------------------------------------
# series_menu() -- not a click command, called directly by list_series.
# Driven with direct click.* patches so every branch (including the
# click.Choice-unreachable-in-real-use "else" branch) can be exercised.
# ---------------------------------------------------------------------------

class TestSeriesMenu(unittest.TestCase):

    def _serie(self, **overrides):
        return Series(make_store(**overrides))

    @patch("cli.click.prompt")
    def test_back_returns_immediately(self, mock_prompt):
        mock_prompt.return_value = "back"
        profile = MagicMock()
        serie = self._serie()
        buf = io.StringIO()
        with redirect_stdout(buf):
            cli_module.series_menu(profile, serie)
        self.assertIn("BREAKING BAD", buf.getvalue())
        profile.remove_series.assert_not_called()

    @patch("cli.click.confirm")
    @patch("cli.click.prompt")
    def test_remove_confirmed_removes_series_and_returns(self, mock_prompt, mock_confirm):
        mock_prompt.return_value = "remove"
        mock_confirm.return_value = True
        profile = MagicMock()
        serie = self._serie(id=42)
        buf = io.StringIO()
        with redirect_stdout(buf):
            cli_module.series_menu(profile, serie)
        profile.remove_series.assert_called_once_with(42)
        self.assertIn("Removed", buf.getvalue())

    @patch("cli.click.confirm")
    @patch("cli.click.prompt")
    def test_remove_declined_keeps_series_and_returns(self, mock_prompt, mock_confirm):
        mock_prompt.return_value = "remove"
        mock_confirm.return_value = False
        profile = MagicMock()
        serie = self._serie()
        buf = io.StringIO()
        with redirect_stdout(buf):
            cli_module.series_menu(profile, serie)
        profile.remove_series.assert_not_called()

    @patch("cli.click.prompt")
    def test_add_tag_then_back(self, mock_prompt):
        mock_prompt.side_effect = ["add-tag", "newtag", "back"]
        profile = MagicMock()
        serie = self._serie(tags=[])
        buf = io.StringIO()
        with redirect_stdout(buf):
            cli_module.series_menu(profile, serie)
        self.assertIn("newtag", serie.tags)
        self.assertIn("Tagged", buf.getvalue())

    @patch("cli.click.prompt")
    def test_remove_tag_then_back(self, mock_prompt):
        mock_prompt.side_effect = ["remove-tag", "drama", "back"]
        profile = MagicMock()
        serie = self._serie(tags=["drama"])
        buf = io.StringIO()
        with redirect_stdout(buf):
            cli_module.series_menu(profile, serie)
        self.assertNotIn("drama", serie.tags)
        self.assertIn("Removed tag", buf.getvalue())

    @patch("cli.click.prompt")
    def test_set_stopped_at_then_back(self, mock_prompt):
        mock_prompt.side_effect = ["set-stopped-at", 2, 6, "back"]
        profile = MagicMock()
        serie = self._serie(num_seasons=3, num_episodes=10, stopped_at=[0, 0])
        buf = io.StringIO()
        with redirect_stdout(buf):
            cli_module.series_menu(profile, serie)
        self.assertEqual(serie.stopped_at, [2, 6])
        self.assertIn("Updated stopped_at to 2 6", buf.getvalue())

    @patch("cli.click.prompt")
    def test_caught_up_then_back(self, mock_prompt):
        mock_prompt.side_effect = ["caught-up", "back"]
        profile = MagicMock()
        serie = self._serie(num_seasons=3, num_episodes=10, stopped_at=[0, 0])
        with redirect_stdout(io.StringIO()):
            cli_module.series_menu(profile, serie)
        self.assertEqual(serie.status, Status.CAUGHT_UP)

    @patch("cli.click.prompt")
    def test_reset_then_back(self, mock_prompt):
        mock_prompt.side_effect = ["reset", "back"]
        profile = MagicMock()
        serie = self._serie(stopped_at=[2, 4])
        with redirect_stdout(io.StringIO()):
            cli_module.series_menu(profile, serie)
        self.assertEqual(serie.stopped_at, (0, 0))
        self.assertEqual(serie.status, Status.HAVENT_STARTED)

    @patch.object(Api, "get_data")
    @patch("cli.click.prompt")
    def test_check_for_updates_then_back(self, mock_prompt, mock_get_data):
        mock_prompt.side_effect = ["check-for-updates", "back"]
        mock_get_data.return_value = {
            "num_seasons": 4, "num_episodes": 10, "tags": [],
        }
        profile = MagicMock()
        serie = self._serie(num_seasons=3, num_episodes=10, tags=[])
        with redirect_stdout(io.StringIO()):
            cli_module.series_menu(profile, serie)
        self.assertEqual(serie.num_seasons, 4)
        mock_get_data.assert_called_once_with(serie.id)

    @patch("cli.click.prompt")
    def test_unrecognized_action_prints_message(self, mock_prompt):
        # click.Choice would normally reject any value outside ACTIONS;
        # mocking click.prompt itself bypasses that validation so the
        # dead-in-real-usage "else" branch can still be exercised.
        mock_prompt.side_effect = ["not-a-real-action", "back"]
        profile = MagicMock()
        serie = self._serie()
        buf = io.StringIO()
        with redirect_stdout(buf):
            cli_module.series_menu(profile, serie)
        self.assertIn("Unrecognized action", buf.getvalue())

    @patch("cli.click.prompt")
    def test_status_style_watching_for_in_progress(self, mock_prompt):
        mock_prompt.return_value = "back"
        profile = MagicMock()
        serie = self._serie(num_seasons=3, num_episodes=10, stopped_at=[1, 2])
        buf = io.StringIO()
        with redirect_stdout(buf):
            cli_module.series_menu(profile, serie)
        self.assertIn("WATCHING", buf.getvalue())

    @patch("cli.click.prompt")
    def test_status_style_not_started_for_havent_started(self, mock_prompt):
        mock_prompt.return_value = "back"
        profile = MagicMock()
        serie = self._serie(stopped_at=[0, 0])
        buf = io.StringIO()
        with redirect_stdout(buf):
            cli_module.series_menu(profile, serie)
        self.assertIn("NOT STARTED", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
