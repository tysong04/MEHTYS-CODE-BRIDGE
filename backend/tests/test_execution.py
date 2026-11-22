from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_python_execution_success():
    res = client.post(
        "/api/execute",
        json={"language": "python", "code": "print('MTCB_TEST_OK')"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "MTCB_TEST_OK" in data["stdout"]
    assert data["timed_out"] is False


def test_python_execution_with_stdin():
    code = """
import sys
line = sys.stdin.read().strip()
print(f"ECHO:{line}")
"""
    res = client.post(
        "/api/execute",
        json={"language": "python", "code": code, "stdin": "HelloWorld"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "ECHO:HelloWorld" in data["stdout"]


def test_python_execution_timeout():
    res = client.post(
        "/api/execute",
        json={"language": "python", "code": "while True:\n    pass"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is False
    assert data["timed_out"] is True
    assert data["status"] == "Timeout"
