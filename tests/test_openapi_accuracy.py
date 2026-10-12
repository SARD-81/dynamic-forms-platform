import pytest
from drf_spectacular.generators import SchemaGenerator


@pytest.mark.django_db
def test_auth_contracts_and_process_steps_have_precise_openapi_shapes():
    schema = SchemaGenerator().get_schema(request=None, public=True)
    components = schema["components"]["schemas"]
    login = schema["paths"]["/api/v1/accounts/login/"]["post"]
    assert login["requestBody"]["content"]["application/json"]["schema"]["$ref"].endswith("/Login")
    assert login["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/AccountResponse"
    )
    assert "user" in components["AccountResponse"]["properties"]
    assert "csrf_token" in components["CSRFToken"]["properties"]
    steps = components["ParticipantProcessRunDetail"]["properties"]["steps"]
    assert steps["type"] == "array"
    assert steps["items"]["$ref"].endswith("/ParticipantStepRun")
    assert components["ParticipantProcessRunDetail"]["properties"]["resume_token"]["nullable"]
    assert "FormParticipantUnlock" in components
    assert "ProcessParticipantUnlock" in components
