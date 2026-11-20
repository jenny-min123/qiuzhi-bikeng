"""主体分离核验接口（F-06 文本入口）。"""

from __future__ import annotations

from fastapi import APIRouter

from ..schemas import SubjectCheckRequest, SubjectCheckResponse
from ..tools.subject_check import subject_check

router = APIRouter(tags=["subject"])


@router.post("/subject-check", response_model=SubjectCheckResponse)
def subject_check_endpoint(payload: SubjectCheckRequest) -> SubjectCheckResponse:
    result = subject_check(payload.text, payload.recruiter_company)
    return SubjectCheckResponse(**result)
