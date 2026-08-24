"""pytest-factoryboy helpers for list-valued fixture parametrization."""

from pytest_factoryboy import LazyFixture


class LazyFixtureList(LazyFixture):
    """Resolves to a list of fixture values. Use in @pytest.mark.parametrize for post_generation fields.

    Example:
        @pytest.mark.parametrize("game__files", [LazyFixtureList("game_file")])
        def test_with_file(game): ...
    """

    def __init__(self, *fixtures: str):
        self._fixtures = fixtures
        self.args = list(fixtures)

    def evaluate(self, request):
        return [request.getfixturevalue(f) for f in self._fixtures]
