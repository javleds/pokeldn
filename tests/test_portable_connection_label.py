from types import SimpleNamespace
import pytest
from tests.test_portable_team_view import view


@pytest.mark.parametrize('code,role,expected', [
    ('000', 'host', ['Anfitrión', '000']),
    ('00000000', 'join', ['Unirse', '0000-0000']),
    ('000000', 'host', ['Anfitrión', '000-000']),
    ('0000', 'host', ['Anfitrión', '0000']),
    ('00123', 'host', ['Anfitrión', '00-123']),
    ('', 'host', ['Anfitrión', 'Sin código']),
])
def test_connection_code_preserves_space_and_leading_zeros(code, role, expected):
    ui = view()
    ui.model.tools = {'host': SimpleNamespace(fields=[SimpleNamespace(kind='code', key='--code')])}
    ui.model.code, ui.model.role = code, role
    ui.model.busy = True
    ui.refresh(update=False)
    assert [text.value for text in ui.connection.content.controls] == expected
    assert ui.model.code == code
    assert ui.connection.height == 40
    assert ui.connection.disabled
    assert expected[-1] in ui.connection.tooltip


def test_games_without_code_only_show_role():
    ui = view()
    assert [text.value for text in ui.connection.content.controls] == ['Anfitrión']
