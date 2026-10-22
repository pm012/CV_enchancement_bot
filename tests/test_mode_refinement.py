import asyncio
import unittest
from types import SimpleNamespace

from modes.base import BotMode
from modes.resume_review import ResumeReviewMode


class RecordingLlm:
    def __init__(self):
        self.prompt = None
        self.payload = None
        self.answer = "Revised output"
        self.calls = 0

    async def send_question(self, prompt, payload):
        self.calls += 1
        self.prompt = prompt
        self.payload = payload
        return self.answer


class ModeRefinementTests(unittest.TestCase):
    def test_refinement_includes_saved_sources_and_all_corrections(self):
        llm = RecordingLlm()
        mode = BotMode(llm)
        context = SimpleNamespace(
            user_data={
                "cv_text": "Engineer, 2020-2024",
                "vacancy_text": "Python developer",
                "last_result": "Timeline error: future dates",
            }
        )

        result = asyncio.run(mode.refine(context, ["Dates are in the past.", "Keep it concise."]))

        self.assertEqual(result, "Revised output")
        self.assertIn("CURRENT DATE (UTC):", llm.payload)
        self.assertIn("Engineer, 2020-2024", llm.payload)
        self.assertIn("Python developer", llm.payload)
        self.assertIn("Timeline error: future dates", llm.payload)
        self.assertIn("1. Dates are in the past.", llm.payload)
        self.assertIn("2. Keep it concise.", llm.payload)
        self.assertIn("treat these as updates to the source", llm.payload)
        self.assertIn("candidate-confirmed facts", llm.prompt)
        self.assertIn("do not continue calling them missing or undocumented", llm.prompt)

    def test_tailored_resume_uses_corrections_and_rejects_empty_response(self):
        llm = RecordingLlm()
        mode = ResumeReviewMode(llm)
        context = SimpleNamespace(
            user_data={
                "cv_text": "Engineer",
                "vacancy_text": "Python developer",
                "last_result": "Revised audit",
                "mode_adjustments": ["Timeline dates are in the past."],
            }
        )

        result = asyncio.run(mode.generate_tailored_resume(context))

        self.assertEqual(result, "Revised output")
        self.assertIn("Timeline dates are in the past.", llm.payload)
        self.assertIn("LATEST AUDIT AND USER-REVISED RESULT", llm.payload)

        context.user_data.pop("tailored_resume_cache")
        context.user_data.pop("tailored_resume_cache_key")
        llm.answer = "⚠️ Model returned empty response."
        with self.assertRaises(RuntimeError):
            asyncio.run(mode.generate_tailored_resume(context))

    def test_tailored_resume_is_cached_until_source_or_adjustments_change(self):
        llm = RecordingLlm()
        mode = ResumeReviewMode(llm)
        context = SimpleNamespace(
            user_data={
                "cv_text": "Engineer",
                "vacancy_text": "Python developer",
                "last_result": "Audit",
                "mode_adjustments": [],
            }
        )

        first = asyncio.run(mode.generate_tailored_resume(context))
        second = asyncio.run(mode.generate_tailored_resume(context))
        self.assertEqual(first, second)
        self.assertEqual(llm.calls, 1)

        context.user_data["mode_adjustments"].append(
            "Candidate used Prometheus and Grafana."
        )
        asyncio.run(mode.generate_tailored_resume(context))
        self.assertEqual(llm.calls, 2)


if __name__ == "__main__":
    unittest.main()
