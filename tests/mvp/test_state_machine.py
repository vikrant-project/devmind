from devmind.core.state_machine import StateMachine, State
def test_transitions(tmp_path):
    sm = StateMachine(tmp_path, "s_test")
    sm.enter(State.UNDERSTAND); sm.enter(State.PLAN); sm.enter(State.BUILD)
    assert State.UNDERSTAND.value in sm.record.completed_states
    assert sm.current == State.BUILD
def test_resume(tmp_path):
    sm = StateMachine(tmp_path, "s_test")
    sm.enter(State.UNDERSTAND); sm.enter(State.PLAN); sm.enter(State.BUILD)
    sm2 = StateMachine(tmp_path, "s_test")
    assert sm2.current == State.BUILD
    assert sm2.resume_target() == State.BUILD
