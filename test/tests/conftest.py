import pytest

import os

@pytest.hookimpl()
def pytest_sessionfinish(session):
    compose_file = os.path.join(str(session.path), "tests", "docker-compose.yml.generated")
    os.remove(compose_file)
    print(f"\nDeleted temporary file {compose_file} sucessfully")
