from enum import Enum


class ControllerState(str, Enum):
    INIT = "INIT"
    PLAN = "PLAN"
    EXECUTE = "EXECUTE"
    VALIDATE = "VALIDATE"
    COMMIT = "COMMIT"
    ARCHIVE = "ARCHIVE"
    FAILED = "FAILED"


class DeterministicFSM:
    _transitions: dict[ControllerState, tuple[ControllerState, ...]] = {
        ControllerState.INIT: (ControllerState.PLAN,),
        ControllerState.PLAN: (ControllerState.EXECUTE,),
        ControllerState.EXECUTE: (ControllerState.VALIDATE,),
        ControllerState.VALIDATE: (ControllerState.COMMIT,),
        ControllerState.COMMIT: (ControllerState.ARCHIVE,),
        ControllerState.ARCHIVE: (),
        ControllerState.FAILED: (),
    }

    def __init__(self) -> None:
        self.current_state = ControllerState.INIT

    def can_transition(self, target_state: ControllerState) -> bool:
        if target_state == ControllerState.FAILED:
            return self.current_state not in (ControllerState.ARCHIVE, ControllerState.FAILED)
        return target_state in self._transitions[self.current_state]

    def transition(self, target_state: ControllerState) -> ControllerState:
        if not self.can_transition(target_state):
            raise ValueError(
                f"Invalid transition: {self.current_state.value} -> {target_state.value}"
            )
        self.current_state = target_state
        return self.current_state
