import pytest

import pbnh.db
from pbnh import create_app


@pytest.fixture
def override_config():
    """Get config that should be set for all tests."""
    return {"DEBUG": True, "TESTING": True}


@pytest.fixture(
    params=[
        pytest.param("postgresql://postgres:postgres@db:5432/pastedb", id="postgres"),
        pytest.param("sqlite:///test_db.sqlite", id="sqlite"),
    ]
)
def app(override_config, request):
    """Create and configure a new app instance for each test."""
    app = create_app({**override_config, "SQLALCHEMY_DATABASE_URI": request.param})
    with app.app_context():
        pbnh.db.init_db()
    yield app
    with app.app_context():
        pbnh.db.undo_db()
