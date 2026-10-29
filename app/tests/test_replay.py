import pytest

from app.services.replay_service import active_replays, ReplayController, get_replay


def test_controller_dictionary():
    run_id = "M2_50_healthy_1_0"
    replay_controller = ReplayController()

    # Registering the controller
    active_replays[run_id] = replay_controller
    result = get_replay(run_id)

    assert result is replay_controller

def test_controller_unknown_id_dictionary():

    invalid_id = "tralala"
    run_id = "test"
    replay_controller = ReplayController()
    active_replays[run_id] = replay_controller

    with pytest.raises(ValueError):
        get_replay(invalid_id)


