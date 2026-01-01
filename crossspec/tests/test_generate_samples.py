from pathlib import Path


def test_generate_samples_runs():
    script = Path(__file__).resolve().parents[2] / "samples" / "generate_samples.py"
    assert script.exists(), "generate_samples.py should exist"

    namespace = {"__name__": "__main__", "__file__": str(script)}
    try:
        exec(script.read_text(encoding="utf-8"), namespace)
    except SystemExit:
        pass

    input_dir = script.parent / "input"
    assert input_dir.exists()
    assert (input_dir / "mail" / "mail1.eml").exists()
