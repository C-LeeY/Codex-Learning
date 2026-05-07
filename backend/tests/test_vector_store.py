import sys
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from models import Course, CourseChunk, Lesson
from vector_store import VectorStore


class FakeCollection:
    def __init__(self, ids_by_get=None):
        self.ids_by_get = ids_by_get or []
        self.get_calls = []
        self.delete_calls = []
        self.add_calls = []

    def get(self, **kwargs):
        self.get_calls.append(kwargs)
        return {"ids": list(self.ids_by_get)}

    def delete(self, **kwargs):
        self.delete_calls.append(kwargs)

    def add(self, **kwargs):
        self.add_calls.append(kwargs)


class VectorStoreUpsertTests(unittest.TestCase):
    def test_upsert_course_deletes_existing_catalog_and_content_then_adds_fresh_data(self):
        catalog = FakeCollection(ids_by_get=["Course A"])
        content = FakeCollection(ids_by_get=["Course_A_0", "Course_A_1"])
        store = object.__new__(VectorStore)
        store.course_catalog = catalog
        store.course_content = content

        course = Course(
            title="Course A",
            course_link="https://example.test/course-a",
            instructor="Instructor",
            lessons=[
                Lesson(
                    lesson_number=1,
                    title="Intro",
                    lesson_link="https://example.test/course-a/1",
                )
            ],
        )
        chunks = [
            CourseChunk(
                content="fresh content",
                course_title="Course A",
                lesson_number=1,
                chunk_index=0,
            )
        ]

        store.upsert_course(course, chunks)

        self.assertEqual(catalog.get_calls, [{"ids": ["Course A"]}])
        self.assertEqual(content.get_calls, [{"where": {"course_title": "Course A"}}])
        self.assertEqual(catalog.delete_calls, [{"ids": ["Course A"]}])
        self.assertEqual(content.delete_calls, [{"ids": ["Course_A_0", "Course_A_1"]}])
        self.assertEqual(catalog.add_calls[0]["ids"], ["Course A"])
        self.assertEqual(
            catalog.add_calls[0]["metadatas"][0]["course_link"],
            "https://example.test/course-a",
        )
        self.assertEqual(content.add_calls[0]["documents"], ["fresh content"])
        self.assertEqual(content.add_calls[0]["ids"], ["Course_A_0"])


if __name__ == "__main__":
    unittest.main()
