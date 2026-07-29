import pytest

import pbnh.db
from pbnh import create_app


@pytest.fixture(
    params=[
        pytest.param({}, id="postgres"),  # tests/pbnh.yaml
        pytest.param(
            {"SQLALCHEMY_DATABASE_URI": "sqlite:///test_db.sqlite"},
            id="sqlite",
        ),
    ]
)
def app(request):
    """Create and configure a new app instance for each test."""
    app = create_app(request.param)
    with app.app_context():
        pbnh.db.init_db()
    yield app
    with app.app_context():
        pbnh.db.undo_db()


@pytest.fixture
def server_url():
    app = create_app()
    with app.app_context():
        pbnh.db.init_db()
    yield "http://sut:8000"
    with app.app_context():
        pbnh.db.undo_db()
