import pytest
from app.models.position import Position


def test_valid_position():
    position = Position(x=3, y=5)

    assert position.x == 3
    assert position.y == 5


def test_negative_position_rejected():
    with pytest.raises(ValueError):
        Position(x=-1, y=5)