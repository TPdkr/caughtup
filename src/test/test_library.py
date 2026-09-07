import io
import os
import sys
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

CORE_FILES_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "core")
)
if CORE_FILES_DIR not in sys.path:
    sys.path.insert(0, CORE_FILES_DIR)

from library import Library  # noqa: E402
from series import Series, Status  # noqa: E402
from api import Api  # noqa: E402


def make_store(**overrides):
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


def make_data_file(path, series_stores):
    with open(path, "w") as f:
        json.dump({"series": series_stores}, f)


class TestLibraryInit(unittest.TestCase):
    """__init__: covers the 'no path given' branch (no load attempted),
    the 'path given, load succeeds' branch, and the 'path given, load
    fails' branch (raises FileNotFoundError)."""

    def test_no_path_does_not_load_and_series_is_empty(self):
        lib = Library()
        self.assertEqual(lib.path, "")
        self.assertEqual(lib.series, [])

    def test_valid_path_loads_series(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "data.json")
            make_data_file(path, [make_store(id=1), make_store(id=2)])
            lib = Library(path)
            self.assertEqual(len(lib.series), 2)
            self.assertIsInstance(lib.series[0], Series)

    def test_missing_file_raises_file_not_found_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "does_not_exist.json")
            with self.assertRaises(FileNotFoundError):
                Library(path)


class TestLoad(unittest.TestCase):
    """load(): success branch (returns 0, populates series) and the
    except FileNotFoundError branch (prints message, returns -1)."""

    def test_load_success_returns_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "data.json")
            make_data_file(path, [make_store(id=1)])
            lib = Library()
            lib.set_path(path)
            code = lib.load()
            self.assertEqual(code, 0)
            self.assertEqual(len(lib.series), 1)

    def test_load_missing_file_returns_negative_one_and_prints(self):
        lib = Library()
        lib.set_path("/nonexistent/path/data.json")
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = lib.load()
        self.assertEqual(code, -1)
        self.assertIn("was not found", buf.getvalue())


class TestSave(unittest.TestCase):
    """save(): empty-path branch (-1, prints), the successful write
    branch (0, valid JSON on disk), and the except FileNotFoundError
    branch (writing to a directory that doesn't exist)."""

    def test_save_with_no_path_returns_negative_one(self):
        lib = Library()
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = lib.save()
        self.assertEqual(code, -1)
        self.assertIn("path not specidied", buf.getvalue())

    def test_save_writes_valid_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "out.json")
            lib = Library()
            lib.set_path(path)
            lib.series.append(Series(make_store(id=1)))
            lib.series.append(Series(make_store(id=2)))
            code = lib.save()
            self.assertEqual(code, 0)
            with open(path) as f:
                data = json.load(f)
            self.assertEqual(len(data["series"]), 2)
            self.assertEqual(data["series"][0]["id"], 1)

    def test_save_to_nonexistent_directory_returns_negative_one(self):
        lib = Library()
        lib.set_path("/this/dir/does/not/exist/out.json")
        code = lib.save()
        self.assertEqual(code, -1)


class TestSetPath(unittest.TestCase):
    """set_path(): simple setter."""

    def test_set_path_updates_path_attribute(self):
        lib = Library()
        lib.set_path("/some/new/path.json")
        self.assertEqual(lib.path, "/some/new/path.json")


class TestCheckForUpdatesAll(unittest.TestCase):
    """check_for_updates_all(): covers id_list empty (checks everything),
    and id_list non-empty with both a matching and a non-matching id."""

    def _lib_with_series(self):
        lib = Library()
        lib.series = [
            Series(make_store(id=1, num_seasons=3, num_episodes=10, tags=[])),
            Series(make_store(id=2, num_seasons=3, num_episodes=10, tags=[])),
        ]
        return lib

    @patch.object(Api, "get_data")
    def test_empty_id_list_checks_all_series(self, mock_get_data):
        mock_get_data.return_value = {"num_seasons": 3, "num_episodes": 10, "tags": []}
        lib = self._lib_with_series()
        lib.check_for_updates_all()
        self.assertEqual(mock_get_data.call_count, 2)

    @patch.object(Api, "get_data")
    def test_id_list_only_checks_matching_series(self, mock_get_data):
        mock_get_data.return_value = {"num_seasons": 3, "num_episodes": 10, "tags": []}
        lib = self._lib_with_series()
        lib.check_for_updates_all(id_list=[2])
        mock_get_data.assert_called_once_with(2)


class TestAllCaughtUpAll(unittest.TestCase):
    """all_caught_up_all(): covers id_list empty (all marked), id_list
    with a matching id, and id_list with a non-matching id left alone."""

    def _lib_with_series(self):
        lib = Library()
        lib.series = [
            Series(make_store(id=1, num_seasons=3, num_episodes=10, stopped_at=[0, 0])),
            Series(make_store(id=2, num_seasons=3, num_episodes=10, stopped_at=[0, 0])),
        ]
        return lib

    def test_empty_id_list_marks_all_caught_up(self):
        lib = self._lib_with_series()
        lib.all_caught_up_all()
        for serie in lib.series:
            self.assertEqual(serie.status, Status.CAUGHT_UP)

    def test_id_list_only_marks_matching_series(self):
        lib = self._lib_with_series()
        lib.all_caught_up_all(id_list=[1])
        self.assertEqual(lib.series[0].status, Status.CAUGHT_UP)
        # non-matching series untouched (still HAVENT_STARTED)
        self.assertEqual(lib.series[1].status, Status.HAVENT_STARTED)


class TestResetAll(unittest.TestCase):
    """reset_all(): covers id_list empty (all reset), id_list with a
    matching id, and a non-matching id left alone."""

    def _lib_with_series(self):
        lib = Library()
        lib.series = [
            Series(make_store(id=1, num_seasons=3, num_episodes=10, stopped_at=[2, 4])),
            Series(make_store(id=2, num_seasons=3, num_episodes=10, stopped_at=[2, 4])),
        ]
        return lib

    def test_empty_id_list_resets_all(self):
        lib = self._lib_with_series()
        lib.reset_all()
        for serie in lib.series:
            self.assertEqual(serie.stopped_at, (0, 0))
            self.assertEqual(serie.status, Status.HAVENT_STARTED)

    def test_id_list_only_resets_matching_series(self):
        lib = self._lib_with_series()
        lib.reset_all(id_list=[1])
        self.assertEqual(lib.series[0].stopped_at, (0, 0))
        # non-matching series untouched
        self.assertEqual(lib.series[1].stopped_at, [2, 4])


class TestClearUpdated(unittest.TestCase):
    """clear_updated(): removes the 'updated' tag from every series."""

    def test_clear_updated_removes_tag_from_all(self):
        lib = Library()
        lib.series = [
            Series(make_store(id=1, tags=["comedy", "updated"])),
            Series(make_store(id=2, tags=["updated"])),
        ]
        lib.clear_updated()
        for serie in lib.series:
            self.assertNotIn("updated", serie.tags)
        self.assertIn("comedy", lib.series[0].tags)


class TestAddSeries(unittest.TestCase):
    """add_series(): appends the series and triggers check_for_updates."""

    @patch.object(Api, "get_data")
    def test_add_series_appends_and_checks_for_updates(self, mock_get_data):
        mock_get_data.return_value = {"num_seasons": 3, "num_episodes": 10, "tags": []}
        lib = Library()
        serie = Series(make_store(id=5, num_seasons=3, num_episodes=10, tags=[]))
        lib.add_series(serie)
        self.assertIn(serie, lib.series)
        mock_get_data.assert_called_once_with(5)


class TestRemoveSeries(unittest.TestCase):
    """remove_series(): removes the matching id and leaves others."""

    def test_remove_series_removes_matching_id_only(self):
        lib = Library()
        lib.series = [
            Series(make_store(id=1)),
            Series(make_store(id=2)),
        ]
        lib.remove_series(1)
        self.assertEqual(len(lib.series), 1)
        self.assertEqual(lib.series[0].id, 2)

    def test_remove_series_with_unknown_id_leaves_list_unchanged(self):
        lib = Library()
        lib.series = [Series(make_store(id=1))]
        lib.remove_series(999)
        self.assertEqual(len(lib.series), 1)


class TestGetTags(unittest.TestCase):
    """get_tags(): returns the deduplicated union of all series' tags,
    including the empty-library case."""

    def test_get_tags_returns_unique_tags_across_series(self):
        lib = Library()
        lib.series = [
            Series(make_store(id=1, tags=["comedy", "drama"])),
            Series(make_store(id=2, tags=["drama", "action"])),
        ]
        self.assertEqual(set(lib.get_tags()), {"comedy", "drama", "action"})

    def test_get_tags_empty_library_returns_empty_list(self):
        lib = Library()
        self.assertEqual(lib.get_tags(), [])


class TestGetWith(unittest.TestCase):
    """get_with(): every filter's match/no-match branch, exercised both
    individually and in combination."""

    def _lib(self):
        lib = Library()
        lib.series = [
            Series(make_store(id=1, name="Breaking Bad", tags=["drama"],
                               num_seasons=3, num_episodes=10, stopped_at=[3, 10])),  # CAUGHT_UP
            Series(make_store(id=2, name="Comedy Show", tags=["comedy", "updated"],
                               num_seasons=3, num_episodes=10, stopped_at=[0, 0])),  # HAVENT_STARTED
        ]
        return lib

    def test_default_filters_return_everything(self):
        lib = self._lib()
        self.assertEqual(len(lib.get_with()), 2)

    def test_keyword_match_is_case_insensitive_substring(self):
        lib = self._lib()
        matches = lib.get_with(key_word="breaking")
        self.assertEqual([s.id for s in matches], [1])

    def test_keyword_no_match_returns_empty(self):
        lib = self._lib()
        self.assertEqual(lib.get_with(key_word="nonexistent"), [])

    def test_tag_match_filters_to_matching_series(self):
        lib = self._lib()
        matches = lib.get_with(tag="comedy")
        self.assertEqual([s.id for s in matches], [2])

    def test_tag_no_match_returns_empty(self):
        lib = self._lib()
        self.assertEqual(lib.get_with(tag="horror"), [])

    def test_updated_true_filters_to_series_with_updated_tag(self):
        lib = self._lib()
        matches = lib.get_with(updated=True)
        self.assertEqual([s.id for s in matches], [2])

    def test_updated_true_with_no_updated_series_returns_empty(self):
        lib = Library()
        lib.series = [Series(make_store(id=1, tags=["drama"]))]
        self.assertEqual(lib.get_with(updated=True), [])

    def test_status_id_match_filters_to_matching_status(self):
        lib = self._lib()
        matches = lib.get_with(status_id=Status.CAUGHT_UP.value)
        self.assertEqual([s.id for s in matches], [1])

    def test_status_id_no_match_returns_empty(self):
        lib = self._lib()
        self.assertEqual(lib.get_with(status_id=Status.IN_PROGRESS.value), [])

    def test_combined_filters_narrow_to_single_match(self):
        lib = self._lib()
        matches = lib.get_with(key_word="Comedy", tag="comedy",
                                status_id=Status.HAVENT_STARTED.value)
        self.assertEqual([s.id for s in matches], [2])

    def test_combined_filters_with_one_mismatch_returns_empty(self):
        lib = self._lib()
        # right keyword, wrong tag -> no match
        matches = lib.get_with(key_word="Comedy", tag="drama")
        self.assertEqual(matches, [])


if __name__ == "__main__":
    unittest.main()
