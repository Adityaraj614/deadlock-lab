
import pytest

from app.models.obstacle import Obstacle
from app.models.position import Position


def test_obstacle_creation():
    obstacle = Obstacle(
        id="wall_1",
        position=Position(x=3, y=4)
    )

    assert obstacle.id == "wall_1"
    assert obstacle.position.x == 3
    assert obstacle.position.y == 4
    assert obstacle.is_dynamic is False


def test_dynamic_obstacle():
    obstacle = Obstacle(
        id="moving_block_1",
        position=Position(x=2, y=2),
        is_dynamic=True
    )

    assert obstacle.is_dynamic is True


def test_empty_obstacle_id_rejected():
    with pytest.raises(ValueError):
        Obstacle(
            id="",
            position=Position(x=1, y=1)
        )
