from app.agents.review import CodeReviewAgent
from app.agents.security import SecurityAgent


def test_code_review_passes_normal_work():
    result = CodeReviewAgent().run({"brief": "Add a tested API endpoint"}, [])
    assert result.next_status == "review_passed"


def test_code_review_blocks_explicit_bad_practice():
    result = CodeReviewAgent().run({"brief": "Use an unsafe hack and skip tests"}, [])
    assert result.next_status == "review_blocked"


def test_security_passes_normal_work():
    result = SecurityAgent().run({"brief": "Add authenticated API endpoint"}, [])
    assert result.next_status == "security_passed"


def test_security_blocks_explicit_vulnerability():
    result = SecurityAgent().run({"brief": "Disable auth and expose token"}, [])
    assert result.next_status == "security_blocked"