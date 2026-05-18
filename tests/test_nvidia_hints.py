from crisis.llm.nvidia_health import nvidia_model_enablement_hint


def test_function_id_404_hint():
    err = (
        "Error code: 404 - {'status': 404, 'detail': "
        "\"Function id 'cd89bd68-13e3-47a9-861e-9a62e6e14b05' version 'null'\"}"
    )
    hint = nvidia_model_enablement_hint(err, model="mistralai/mistral-7b-instruct-v0.3")
    assert hint is not None
    assert "build.nvidia.com" in hint
