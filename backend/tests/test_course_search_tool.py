import sys
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from search_tools import CourseSearchTool
from vector_store import SearchResults


class FakeVectorStore:
    def __init__(self, results):
        self.results = results
        self.search_calls = []

    def search(self, **kwargs):
        self.search_calls.append(kwargs)
        return self.results

    def get_lesson_link(self, course_title, lesson_number):
        return f"https://example.test/{course_title}/{lesson_number}"


class CourseSearchToolTests(unittest.TestCase):
    def test_execute_formats_results_with_sources_and_deduplicates(self):
        results = SearchResults(
            documents=["first chunk", "second chunk", "third chunk"],
            metadata=[
                {"course_title": "Course A", "lesson_number": 1},
                {"course_title": "Course A", "lesson_number": 1},
                {"course_title": "Course A", "lesson_number": 2},
            ],
            distances=[0.1, 0.2, 0.3],
        )
        store = FakeVectorStore(results)
        tool = CourseSearchTool(store)

        output = tool.execute("chunk", course_name="Course A", lesson_number=1)

        self.assertEqual(
            store.search_calls,
            [{"query": "chunk", "course_name": "Course A", "lesson_number": 1}],
        )
        self.assertIn("[Course A - Lesson 1]\nfirst chunk", output)
        self.assertIn("[Course A - Lesson 1]\nsecond chunk", output)
        self.assertIn("[Course A - Lesson 2]\nthird chunk", output)
        self.assertEqual(
            tool.last_sources,
            [
                '<a href="https://example.test/Course A/1" target="_blank" '
                'rel="noopener noreferrer">Course A - Lesson 1</a>',
                '<a href="https://example.test/Course A/2" target="_blank" '
                'rel="noopener noreferrer">Course A - Lesson 2</a>',
            ],
        )

    def test_execute_returns_search_error(self):
        tool = CourseSearchTool(FakeVectorStore(SearchResults.empty("No course found")))

        self.assertEqual(tool.execute("anything"), "No course found")
        self.assertEqual(tool.last_sources, [])

    def test_execute_returns_empty_result_message_with_filters(self):
        results = SearchResults(documents=[], metadata=[], distances=[])
        tool = CourseSearchTool(FakeVectorStore(results))

        output = tool.execute("missing", course_name="Course A", lesson_number=3)

        self.assertEqual(
            output,
            "No relevant content found in course 'Course A' in lesson 3.",
        )
        self.assertEqual(tool.last_sources, [])


if __name__ == "__main__":
    unittest.main()
