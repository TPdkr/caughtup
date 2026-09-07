import io
import os
import sys
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

CORE_FILES_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "core")
)
if CORE_FILES_DIR not in sys.path:
    sys.path.insert(0, CORE_FILES_DIR)

from series import Series, Status  # noqa: E402
from api import Api  # noqa: E402


def make_store(**overrides):
    """Full, valid store dict; individual fields can be overridden."""
    store = {
        "id": 1,
        "name": "Test Show",
        "num_seasons": 3,
        "num_episodes": 10,
        "stopped_at": [1, 5],
        "descr": "a show",
        "platform": "streaming",
        "premiered": "2020",
        "ended": None,
        "tags": ["comedy"],
    }
    store.update(overrides)
    return store


class TestSeriesInit(unittest.TestCase):
    """__init__: for each key, covers both the 'present in store' branch
    and every 'missing from store' fallback branch, plus the implicit
    call to check_status()."""

    def test_full_store_sets_all_attributes_from_store(self):
        store = make_store()
        s = Series(store)
        for key in ["id", "name", "num_seasons", "num_episodes", "descr",
                    "platform", "premiered", "ended", "tags"]:
            self.assertEqual(getattr(s, key), store[key])
        # stored as a list (kept as-is from store)
        self.assertEqual(s.stopped_at, [1, 5])

    def test_missing_tags_defaults_to_empty_list(self):
        store = make_store()
        del store["tags"]
        s = Series(store)
        self.assertEqual(s.tags, [])

    def test_missing_num_seasons_defaults_to_zero(self):
        store = make_store()
        del store["num_seasons"]
        s = Series(store)
        self.assertEqual(s.num_seasons, 0)

    def test_missing_num_episodes_defaults_to_zero(self):
        store = make_store()
        del store["num_episodes"]
        s = Series(store)
        self.assertEqual(s.num_episodes, 0)

    def test_missing_stopped_at_defaults_to_zero_zero(self):
        store = make_store()
        del store["stopped_at"]
        s = Series(store)
        self.assertEqual(s.stopped_at, [0, 0])

    def test_missing_other_key_defaults_to_none(self):
        store = make_store()
        del store["descr"]
        s = Series(store)
        self.assertIsNone(s.descr)

    def test_init_calls_check_status_haventstarted(self):
        store = make_store(stopped_at=[0, 0])
        s = Series(store)
        self.assertEqual(s.status, Status.HAVENT_STARTED)


class TestCheckStatus(unittest.TestCase):
    """check_status: every branch of both the sanitizing 'if's and the
    status if/elif/else, including both halves of the elif's `or`."""

    def test_stopped_at_episode_none_is_sanitized_to_zero(self):
        store = make_store(stopped_at=[1, None], num_seasons=3, num_episodes=10)
        s = Series(store)
        self.assertEqual(s.stopped_at[1], 0)

    def test_stopped_at_episode_string_null_is_sanitized_to_zero(self):
        store = make_store(stopped_at=[1, "null"], num_seasons=3, num_episodes=10)
        s = Series(store)
        self.assertEqual(s.stopped_at[1], 0)

    def test_num_episodes_none_is_sanitized_to_zero(self):
        store = make_store(num_episodes=None, stopped_at=[1, 0], num_seasons=3)
        s = Series(store)
        self.assertEqual(s.num_episodes, 0)

    def test_num_episodes_string_null_is_sanitized_to_zero(self):
        store = make_store(num_episodes="null", stopped_at=[1, 0], num_seasons=3)
        s = Series(store)
        self.assertEqual(s.num_episodes, 0)

    def test_status_havent_started_when_stopped_at_zero_zero(self):
        store = make_store(stopped_at=[0, 0], num_seasons=3, num_episodes=10)
        s = Series(store)
        self.assertEqual(s.status, Status.HAVENT_STARTED)

    def test_status_in_progress_when_only_season_condition_true(self):
        # stopped_at[0] < num_seasons -> True, stopped_at[1] < num_episodes -> False
        store = make_store(stopped_at=[1, 10], num_seasons=3, num_episodes=10)
        s = Series(store)
        self.assertEqual(s.status, Status.IN_PROGRESS)

    def test_status_in_progress_when_only_episode_condition_true(self):
        # stopped_at[0] < num_seasons -> False, stopped_at[1] < num_episodes -> True
        store = make_store(stopped_at=[3, 2], num_seasons=3, num_episodes=10)
        s = Series(store)
        self.assertEqual(s.status, Status.IN_PROGRESS)

    def test_status_in_progress_when_both_conditions_true(self):
        store = make_store(stopped_at=[1, 2], num_seasons=3, num_episodes=10)
        s = Series(store)
        self.assertEqual(s.status, Status.IN_PROGRESS)

    def test_status_caught_up_when_both_conditions_false(self):
        # stopped_at != [0,0], and neither comparison is true
        store = make_store(stopped_at=[3, 10], num_seasons=3, num_episodes=10)
        s = Series(store)
        self.assertEqual(s.status, Status.CAUGHT_UP)


class TestPrint(unittest.TestCase):
    """print(): verifies every key is written to stdout."""

    def test_print_outputs_every_key(self):
        s = Series(make_store())
        buf = io.StringIO()
        with redirect_stdout(buf):
            s.print()
        output = buf.getvalue()
        for key in Series.keys:
            self.assertIn(f"{key}:", output)


class TestReset(unittest.TestCase):
    """reset(): sets stopped_at back to (0,0) and status to HAVENT_STARTED."""

    def test_reset_clears_progress(self):
        s = Series(make_store(stopped_at=[2, 4]))
        self.assertEqual(s.status, Status.IN_PROGRESS)
        s.reset()
        self.assertEqual(s.stopped_at, (0, 0))
        self.assertEqual(s.status, Status.HAVENT_STARTED)


class TestSetStoppedAt(unittest.TestCase):
    """set_stopped_at(): sets the value and recomputes status (both
    branches exercised via differing spot values)."""

    def test_set_stopped_at_updates_value_and_recomputes_status_in_progress(self):
        s = Series(make_store(stopped_at=[0, 0], num_seasons=3, num_episodes=10))
        s.set_stopped_at([1, 2])
        self.assertEqual(s.stopped_at, [1, 2])
        self.assertEqual(s.status, Status.IN_PROGRESS)

    def test_set_stopped_at_updates_value_and_recomputes_status_caught_up(self):
        s = Series(make_store(stopped_at=[0, 0], num_seasons=3, num_episodes=10))
        s.set_stopped_at([3, 10])
        self.assertEqual(s.stopped_at, [3, 10])
        self.assertEqual(s.status, Status.CAUGHT_UP)


class TestAllCaughtUp(unittest.TestCase):
    """all_caught_up(): covers both the num_episodes != None branch and
    the num_episodes is None branch."""

    def test_all_caught_up_with_numeric_episodes(self):
        s = Series(make_store(num_seasons=3, num_episodes=10, stopped_at=[0, 0]))
        s.all_caught_up()
        self.assertEqual(s.stopped_at, [3, 10])
        self.assertEqual(s.status, Status.CAUGHT_UP)

    def test_all_caught_up_with_none_episodes(self):
        s = Series(make_store(num_seasons=3, num_episodes=None, stopped_at=[0, 0]))
        # constructor's check_status() would normally sanitize num_episodes to 0,
        # so re-force None to exercise the `else` branch of all_caught_up itself.
        s.num_episodes = None
        s.all_caught_up()
        self.assertEqual(s.stopped_at, [3, 0])
        self.assertEqual(s.status, Status.CAUGHT_UP)


class TestAddTag(unittest.TestCase):
    """add_tag(): tag already present (-1) vs. not present (0, appended)."""

    def test_add_tag_new_returns_zero_and_appends(self):
        s = Series(make_store(tags=["comedy"]))
        result = s.add_tag("drama")
        self.assertEqual(result, 0)
        self.assertIn("drama", s.tags)

    def test_add_tag_existing_returns_negative_one_and_does_not_duplicate(self):
        s = Series(make_store(tags=["comedy"]))
        result = s.add_tag("comedy")
        self.assertEqual(result, -1)
        self.assertEqual(s.tags.count("comedy"), 1)


class TestRemoveTag(unittest.TestCase):
    """remove_tag(): tag present (0, removed) vs. not present (-1)."""

    def test_remove_tag_existing_returns_zero_and_removes(self):
        s = Series(make_store(tags=["comedy", "drama"]))
        result = s.remove_tag("drama")
        self.assertEqual(result, 0)
        self.assertNotIn("drama", s.tags)

    def test_remove_tag_missing_returns_negative_one(self):
        s = Series(make_store(tags=["comedy"]))
        result = s.remove_tag("drama")
        self.assertEqual(result, -1)
        self.assertEqual(s.tags, ["comedy"])


class TestCheckForUpdates(unittest.TestCase):
    """check_for_updates(): mocks Api.get_data to cover both the
    'no new data' and 'new season/episode' branches, the tag-union
    logic, and that 'updated' is only added when something increased."""

    @patch.object(Api, "get_data")
    def test_no_change_does_not_add_updated_tag(self, mock_get_data):
        s = Series(make_store(num_seasons=3, num_episodes=10, tags=["comedy"]))
        mock_get_data.return_value = {
            "num_seasons": 3, "num_episodes": 10, "tags": ["comedy"],
        }
        buf = io.StringIO()
        with redirect_stdout(buf):
            s.check_for_updates()
        mock_get_data.assert_called_once_with(s.id)
        self.assertNotIn("updated", s.tags)
        self.assertEqual(buf.getvalue(), "")

    @patch.object(Api, "get_data")
    def test_new_season_adds_updated_tag_and_prints(self, mock_get_data):
        s = Series(make_store(num_seasons=3, num_episodes=10, tags=["comedy"]))
        mock_get_data.return_value = {
            "num_seasons": 4, "num_episodes": 10, "tags": ["comedy"],
        }
        buf = io.StringIO()
        with redirect_stdout(buf):
            s.check_for_updates()
        self.assertEqual(s.num_seasons, 4)
        self.assertIn("updated", s.tags)
        self.assertIn("Registered updates", buf.getvalue())

    @patch.object(Api, "get_data")
    def test_new_episode_adds_updated_tag(self, mock_get_data):
        s = Series(make_store(num_seasons=3, num_episodes=10, tags=["comedy"]))
        mock_get_data.return_value = {
            "num_seasons": 3, "num_episodes": 11, "tags": ["comedy"],
        }
        buf = io.StringIO()
        with redirect_stdout(buf):
            s.check_for_updates()
        self.assertEqual(s.num_episodes, 11)
        self.assertIn("updated", s.tags)

    @patch.object(Api, "get_data")
    def test_tags_are_unioned_from_old_and_new(self, mock_get_data):
        s = Series(make_store(num_seasons=3, num_episodes=10, tags=["comedy"]))
        mock_get_data.return_value = {
            "num_seasons": 3, "num_episodes": 10, "tags": ["drama"],
        }
        with redirect_stdout(io.StringIO()):
            s.check_for_updates()
        self.assertEqual(set(s.tags), {"comedy", "drama"})


class TestToDict(unittest.TestCase):
    """to_dict(): every key round-trips, and status is stored as its
    underlying int value rather than the Enum member."""

    def test_to_dict_contains_all_keys_with_status_as_value(self):
        s = Series(make_store(stopped_at=[0, 0]))
        d = s.to_dict()
        for key in Series.keys:
            self.assertIn(key, d)
        self.assertEqual(d["status"], Status.HAVENT_STARTED.value)
        self.assertEqual(d["name"], "Test Show")

    def test_to_dict_round_trips_through_series_constructor(self):
        s = Series(make_store(stopped_at=[1, 2], num_seasons=3, num_episodes=10))
        d = s.to_dict()
        s2 = Series(d)
        self.assertEqual(s2.name, s.name)
        self.assertEqual(s2.stopped_at, s.stopped_at)
        # status was serialized as an int and gets recomputed by __init__,
        # rather than deserialized back into an Enum member.
        self.assertEqual(s2.status, s.status)


if __name__ == "__main__":
    unittest.main()
