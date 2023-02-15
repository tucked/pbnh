# Without this file, __package__ will be "" (i.e. the directory the test module is in)
# instead of "tests" (i.e. the repo root). Since pbnh does not actually get installed,
# that means `import pbnh` will raise an ImportError! See the Pytest docs for more info:
# https://docs.pytest.org/en/stable/explanation/goodpractices.html
