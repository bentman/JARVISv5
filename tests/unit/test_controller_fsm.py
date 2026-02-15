import pytest

from backend.controller.fsm import ControllerState, DeterministicFSM


def test_fsm_happy_path_transitions() -> None:
    fsm = DeterministicFSM()
    assert fsm.current_state == ControllerState.INIT

    fsm.transition(ControllerState.PLAN)
    fsm.transition(ControllerState.EXECUTE)
    fsm.transition(ControllerState.VALIDATE)
    fsm.transition(ControllerState.COMMIT)
    fsm.transition(ControllerState.ARCHIVE)

    assert fsm.current_state == ControllerState.ARCHIVE


def test_fsm_rejects_invalid_transition() -> None:
    fsm = DeterministicFSM()
    with pytest.raises(ValueError):
        fsm.transition(ControllerState.EXECUTE)
