import asyncio
from copy import deepcopy
import pytest
from tests.test_portable_team import team


@pytest.mark.parametrize('requested,expected', [
    ([None, '145', None, None], [None, 145, None, None]),
    (['33'], [33, None, None, None]),
    ([0, '145', None, '0'], [0, 145, None, 0]),
    ([None, None, None, None], [None, None, None, None]),
    (['33', '145', '55', '56'], [33, 145, 55, 56]),
])
def test_generation_keeps_automatic_slot_intent_without_mutating_draft(team, requested, expected):
    team.add(0)
    team.edit(0, 'species', 7)
    team.edit(0, 'moves', requested, option=True)
    original = deepcopy(team.slots[0])
    asyncio.run(team.validate(0))
    assert team.service.calls[-1][2].get('move_slots') == expected
    assert team.slots[0] == original
    assert team.can_start
