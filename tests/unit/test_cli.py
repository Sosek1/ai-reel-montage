import pytest

from ai_reel_montage.cli import main


def test_version_flag_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--version"]) == 0
    assert capsys.readouterr().out.strip() != ""
