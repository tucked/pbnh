import pbnh.run


def test_run():
    """Ensure the entry point works."""
    assert hasattr(pbnh.run, "app")
