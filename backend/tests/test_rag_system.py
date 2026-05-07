import re
import sys
import unittest
import os
import tempfile
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

from config import config
from models import Course, CourseChunk
from rag_system import RAGSystem


class FakeToolManager:
    def __init__(self):
        self.executed = []
        self.reset_count = 0
        self.sources = ["source-one"]

    def get_tool_definitions(self):
        return [{"name": "search_course_content"}, {"name": "get_course_outline"}]

    def execute_tool(self, tool_name, **kwargs):
        self.executed.append((tool_name, kwargs))
        self.sources = ["outline-source"]
        return "outline response"

    def get_last_sources(self):
        return list(self.sources)

    def reset_sources(self):
        self.reset_count += 1
        self.sources = []


class FakeAIGenerator:
    def __init__(self):
        self.calls = []

    def generate_response(self, **kwargs):
        self.calls.append(kwargs)
        return "generated response"


class FakeSessionManager:
    def __init__(self):
        self.history_requests = []
        self.exchanges = []

    def get_conversation_history(self, session_id):
        self.history_requests.append(session_id)
        return "previous conversation"

    def add_exchange(self, session_id, query, response):
        self.exchanges.append((session_id, query, response))


def make_rag_with_fakes():
    rag = object.__new__(RAGSystem)
    rag.tool_manager = FakeToolManager()
    rag.ai_generator = FakeAIGenerator()
    rag.session_manager = FakeSessionManager()
    return rag


class FakeDocumentProcessor:
    def __init__(self, courses_by_path):
        self.courses_by_path = courses_by_path

    def process_course_document(self, file_path):
        return self.courses_by_path[Path(file_path).name]


class FakeVectorStore:
    def __init__(self, existing_titles):
        self.existing_titles = list(existing_titles)
        self.upsert_calls = []
        self.cleared = False

    def get_existing_course_titles(self):
        return list(self.existing_titles)

    def upsert_course(self, course, chunks):
        self.upsert_calls.append((course.title, len(chunks)))
        if course.title not in self.existing_titles:
            self.existing_titles.append(course.title)

    def clear_all_data(self):
        self.cleared = True
        self.existing_titles = []


class RAGSystemQueryTests(unittest.TestCase):
    def test_content_query_uses_ai_generator_with_course_tools_and_returns_sources(self):
        rag = make_rag_with_fakes()

        answer, sources = rag.query("How does tool use work?", session_id="session-1")

        self.assertEqual(answer, "generated response")
        self.assertEqual(sources, ["source-one"])
        self.assertEqual(rag.tool_manager.executed, [])
        self.assertEqual(rag.tool_manager.reset_count, 1)
        call = rag.ai_generator.calls[0]
        self.assertEqual(call["query"], "Answer this question about course materials: How does tool use work?")
        self.assertEqual(call["conversation_history"], "previous conversation")
        self.assertEqual(
            call["tools"],
            [{"name": "search_course_content"}, {"name": "get_course_outline"}],
        )
        self.assertIs(call["tool_manager"], rag.tool_manager)
        self.assertEqual(
            rag.session_manager.exchanges,
            [("session-1", "How does tool use work?", "generated response")],
        )

    def test_outline_query_bypasses_ai_generator_and_calls_outline_tool(self):
        rag = make_rag_with_fakes()
        query = 'What is the outline of the "Building Towards Computer Use with Anthropic" course?'

        answer, sources = rag.query(query, session_id="session-2")

        self.assertEqual(answer, "outline response")
        self.assertEqual(sources, ["outline-source"])
        self.assertEqual(rag.ai_generator.calls, [])
        self.assertEqual(
            rag.tool_manager.executed,
            [("get_course_outline", {"course_name": query})],
        )
        self.assertEqual(rag.tool_manager.reset_count, 1)

    def test_current_system_outline_uses_course_link_from_current_docs(self):
        doc_text = (REPO_DIR / "docs" / "course1_script.txt").read_text(encoding="utf-8")
        expected_link = re.search(r"^Course Link:\s*(.+)$", doc_text, re.MULTILINE).group(1)

        original_cwd = Path.cwd()
        try:
            os.chdir(BACKEND_DIR)
            rag = RAGSystem(config)
            rag.add_course_folder(str(REPO_DIR / "docs"), clear_existing=False)
            answer, sources = rag.query(
                'What is the outline of the "MBuilding Towards Computer Use with Anthropic" course?'
            )
        finally:
            os.chdir(original_cwd)

        self.assertIn("Course Title: Building Towards Computer Use with Anthropic", answer)
        self.assertIn(f"Course Link: {expected_link}", answer)
        self.assertEqual(len(sources), 1)
        self.assertIn(expected_link, sources[0])


class RAGSystemCourseLoadingTests(unittest.TestCase):
    def test_add_course_folder_refreshes_existing_courses_and_adds_new_courses(self):
        existing_course = Course(title="Existing Course", course_link="https://old.example")
        new_course = Course(title="New Course", course_link="https://new.example")
        existing_chunks = [
            CourseChunk(
                content="existing content",
                course_title=existing_course.title,
                lesson_number=1,
                chunk_index=0,
            )
        ]
        new_chunks = [
            CourseChunk(
                content="new content",
                course_title=new_course.title,
                lesson_number=1,
                chunk_index=0,
            ),
            CourseChunk(
                content="more new content",
                course_title=new_course.title,
                lesson_number=2,
                chunk_index=1,
            ),
        ]

        with tempfile.TemporaryDirectory() as folder:
            Path(folder, "existing.txt").write_text("existing", encoding="utf-8")
            Path(folder, "new.txt").write_text("new", encoding="utf-8")

            rag = object.__new__(RAGSystem)
            rag.vector_store = FakeVectorStore(existing_titles=["Existing Course"])
            rag.document_processor = FakeDocumentProcessor({
                "existing.txt": (existing_course, existing_chunks),
                "new.txt": (new_course, new_chunks),
            })

            total_courses, total_chunks = rag.add_course_folder(folder)

        self.assertEqual(total_courses, 2)
        self.assertEqual(total_chunks, 3)
        self.assertEqual(
            rag.vector_store.upsert_calls,
            [("Existing Course", 1), ("New Course", 2)],
        )


if __name__ == "__main__":
    unittest.main()
