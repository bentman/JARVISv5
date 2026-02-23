from scripts.integration.replay_baseline import run_replay_baseline_once


def test_replay_baseline_same_input_twice_pipeline_artifacts_match() -> None:
    result = run_replay_baseline_once()

    assert bool(result.get("passed", False)), (
        f"Replay baseline mismatch: reason={result.get('reason', '')}; "
        f"run_1_events={result.get('run_1_events', '')}; "
        f"run_2_events={result.get('run_2_events', '')}"
    )
