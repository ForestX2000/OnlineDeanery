import unittest

from fastapi import HTTPException

from backend.api import request_status_for_exception, request_status_for_result
from backend.models import ApiResponse, Document, Verification


def analyzed_document(verification: Verification) -> ApiResponse:
    return ApiResponse(
        conversation_id="history-test",
        answer="Проверка завершена",
        sources=[],
        document=Document(type="study_certificate", fields={}, coordinates=[]),
        verification=verification,
    )


class RequestHistoryStatusTests(unittest.TestCase):
    def test_incomplete_document_is_an_error(self):
        result = analyzed_document(Verification(
            status="incomplete", missing_fields=["signature"], issues=["Подпись отсутствует."]
        ))
        self.assertEqual(request_status_for_result(result), "failed")

    def test_complete_document_is_resolved(self):
        result = analyzed_document(Verification(status="complete", missing_fields=[], issues=[]))
        self.assertEqual(request_status_for_result(result), "resolved")

    def test_timeouts_have_a_separate_status(self):
        self.assertEqual(request_status_for_exception(HTTPException(504, "timeout")), "timeout")


if __name__ == "__main__":
    unittest.main()
