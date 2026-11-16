"""Human-readable trainer identity without exposing internal profile keys."""
from pokeldn import console_trainer

LANGUAGE_LABELS = {
    1: 'JA', 2: 'EN', 3: 'FR', 4: 'IT', 5: 'DE', 7: 'ES',
    8: 'KO', 9: 'ZH-S', 10: 'ZH-T', 11: 'ES-LA',
}


def trainer_details(game: str, profile: dict) -> str:
    """Display IDs follow the game; stored IDs remain the original 16-bit pair."""
    tid, sid = console_trainer.shown(game, int(profile['tid']), int(profile['sid']))
    language = profile.get('language')
    return f'ID {tid} · SID {sid} · {LANGUAGE_LABELS.get(language, str(language or "?"))}'


def trainer_label(game: str, profile: dict) -> str:
    return f"{profile.get('ot') or 'Sin nombre'} · {trainer_details(game, profile)}"
