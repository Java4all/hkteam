from crisis.llm.errors import is_llm_timeout


def test_is_llm_timeout_message():
    assert is_llm_timeout(Exception("Request timed out."))


def test_is_llm_timeout_type_name():
    class APITimeoutError(Exception):
        pass

    assert is_llm_timeout(APITimeoutError("deadline exceeded"))
