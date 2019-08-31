import pytest

from pwclient import shell


def test_no_args(capsys):
    with pytest.raises(SystemExit):
        shell.main([])

    captured = capsys.readouterr()

    assert 'usage: pwclient [-h]' in captured.out
    assert captured.err == ''


def test_help(capsys):
    with pytest.raises(SystemExit):
        shell.main(['-h'])

    captured = capsys.readouterr()

    assert 'usage: pwclient [-h]' in captured.out
    assert captured.err == ''
