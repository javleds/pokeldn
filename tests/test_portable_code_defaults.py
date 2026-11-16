"""Only required portable connection codes gain a zero-filled default."""
from types import SimpleNamespace

import pytest

from gui.portable_team import Team, TeamStore, default_connection_code, local_tools
from pokeldn.app import command
from pokeldn.app.catalog import Field
from pokeldn.app.settings import Settings


def make_team(tmp_path, game, *, saved=None):
    store = TeamStore(game, tmp_path / game)
    if saved is not None:
        store.save(dict(slots=[None] * 6, **saved))
    setup = SimpleNamespace(settings=Settings(), busy=False, checking=False,
                            session_busy=False, active_team=None)
    return Team(game, setup, store=store)


@pytest.mark.parametrize('game,expected', [
    ('frlg', ''), ('lgpe', '000'), ('swsh', ''), ('bdsp', ''),
    ('pla', '00000000'), ('sv', ''), ('za', '00000000'),
])
def test_new_and_old_empty_drafts_get_required_code_defaults(tmp_path, game, expected):
    assert make_team(tmp_path, game).code == expected
    assert make_team(tmp_path, game, saved={'code': ''}).code == expected


@pytest.mark.parametrize('game', ['frlg', 'lgpe', 'swsh', 'bdsp', 'pla', 'sv', 'za'])
def test_configuring_each_role_uses_only_required_defaults(tmp_path, game):
    team = make_team(tmp_path, game)
    for role, tool in local_tools(game).items():
        team.configure(role, team.version, '000' if game == 'lgpe' else '')
        expected = default_connection_code(game, tool)
        assert team.code == expected
        for field in tool.fields:
            if field.kind in ('code', 'linkcode'):
                wire_value = ','.join(team.code) if field.kind == 'linkcode' else team.code
                assert not command.code_error(field, wire_value, game)


@pytest.mark.parametrize('game,code', [
    ('lgpe', '123'), ('pla', '12345678'), ('za', '87654321'),
    ('sv', '12345678'), ('swsh', '87654321'), ('bdsp', '12345678'),
])
def test_saved_and_configured_codes_are_preserved(tmp_path, game, code):
    team = make_team(tmp_path, game, saved={'code': code})
    assert team.code == code
    team.configure(team.role, team.version, code)
    assert team.code == code


def test_invalid_saved_required_code_remains_visible(tmp_path):
    assert make_team(tmp_path, 'pla', saved={'code': 'bad'}).code == 'bad'


def test_default_obeys_catalog_length_and_requirement():
    def tool(**values):
        return SimpleNamespace(fields=[Field('--code', 'Code', 'code', **values)])
    assert default_connection_code('sv', tool(required=True, length=4)) == '0000'
    assert default_connection_code('sv', tool(default='12345678')) == '00000000'
    assert default_connection_code('sv', tool()) == ''
    assert default_connection_code('frlg', SimpleNamespace(fields=[])) == ''
