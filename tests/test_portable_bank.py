"""The portable archive exports original bytes, never regenerated Pokémon."""
import base64
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path

import pytest

from gui.portable_bank import PortableBank
from pokeldn import pokemon


def info(species="Magikarp", **extra):
    return dict(species=species, species_id=129, level=5, legal=True,
                nickname="Splash", **extra)


OWNER = dict(ot="José", tid=12, sid=34, gender=0, language=7, version=4, egg=False)


@pytest.fixture
def library(tmp_path):
    return PortableBank(tmp_path / "bank")


@pytest.mark.parametrize("game", ["frlg", "lgpe", "swsh", "bdsp", "pla", "sv", "za"])
def test_json_preserves_every_byte_in_all_native_formats(library, game):
    original = bytes((index % 256 for index in range(pokemon.RECORD_SIZES[game][-1])))
    entry = library.deposit(game, original, info(), OWNER)
    exported = json.loads(library.export([entry["id"]]))
    assert isinstance(exported, list) and len(exported) == 1
    record = exported[0]
    assert record["type"] == "pokeldn-portable-pokemon" and record["schema"] == 1
    assert record["game"] == game
    assert record["format"] == pokemon.EXTENSIONS[game]
    assert base64.b64decode(record["original_base64"], validate=True) == original
    assert record["sha256"] == hashlib.sha256(original).hexdigest()
    assert record["metadata"]["trainer"] == OWNER
    assert record["metadata"]["nickname"] == "Splash"
    assert "path" not in record and str(library.root) not in library.export().decode()
    assert library.data(entry["id"]) == original


def test_deduplication_is_by_bytes_and_never_overwrites_original_metadata(library):
    original = bytes(80)
    first = library.deposit("frlg", original, info(), OWNER)
    second = library.deposit("frlg", original, info("Fake replacement"), dict(OWNER, ot="OTHER"))
    assert first["id"] == second["id"]
    assert len(library.list()) == 1
    assert second["species"] == "Magikarp" and second["trainer"]["ot"] == "José"


def test_concurrent_reception_of_same_original_is_single_entry(library):
    with ThreadPoolExecutor(max_workers=4) as workers:
        rows = list(workers.map(lambda _: library.deposit("frlg", bytes(80), info(), OWNER), range(8)))
    assert len({row["id"] for row in rows}) == 1
    assert len(library.list()) == 1


def test_filter_matches_names_and_trainer_fields_without_service_calls(library):
    first = library.deposit("frlg", bytes(80), info(), OWNER)
    second = library.deposit("sv", bytes(328), info("Pikachu"), dict(OWNER, ot="ASH"))
    assert [row["id"] for row in library.list(query="josé")] == [first["id"]]
    assert [row["id"] for row in library.list(query="pikachu", game="sv")] == [second["id"]]
    assert library.list(query="pikachu", game="frlg") == []
    assert library.list(query="Splash")
    assert library.list(query="34")
    assert len(json.loads(library.export())) == 2


def test_illegal_received_original_can_be_archived_but_not_mislabeled(library):
    details = info()
    details["legal"] = False
    entry = library.deposit("frlg", bytes(80), details, OWNER)
    assert entry["legal"] is False
    assert json.loads(library.export())[0]["metadata"]["legal"] is False


def test_external_mutation_blocks_read_export_and_dedup(library):
    entry = library.deposit("frlg", bytes(80), info(), OWNER)
    Path(entry["path"]).write_bytes(b"x" * 80)
    for action in (
        lambda: library.data(entry["id"]),
        lambda: library.export(),
        lambda: library.deposit("frlg", bytes(80), info(), OWNER),
    ):
        with pytest.raises(ValueError, match="cambió"):
            action()


def test_explicit_deletion_has_no_hidden_backfill(library, tmp_path):
    original = tmp_path / "received.pk3"
    original.write_bytes(bytes(80))
    first = library.deposit("frlg", original.read_bytes(), info(), OWNER)
    library.delete(first["id"])
    assert library.list() == []
    assert original.read_bytes() == bytes(80)
    assert json.loads(library.export()) == []
    assert PortableBank(library.root).list() == []
    with pytest.raises(ValueError, match="ya no"):
        library.export([first["id"]])


def test_bulk_delete_only_removes_bank_records(library):
    library.deposit("frlg", bytes(80), info(), OWNER)
    library.deposit("sv", bytes(328), info(), OWNER)
    unrelated = library.root / "notes.txt"
    unrelated.write_text("keep")
    assert library.delete_all() == 2
    assert library.list() == []
    assert unrelated.read_text() == "keep"


@pytest.mark.parametrize("game,data", [("other", bytes(80)), ("frlg", bytes(328)), ("sv", b"")])
def test_wrong_record_shape_never_creates_files(library, game, data):
    with pytest.raises(ValueError):
        library.deposit(game, data, info(), OWNER)
    assert not library.root.exists()


def test_deletion_does_not_accept_a_filesystem_path(library, tmp_path):
    outside = tmp_path / "secret.pk3"
    outside.write_bytes(bytes(80))
    with pytest.raises(ValueError, match="ya no"):
        library.delete(str(outside))
    assert outside.exists()


def test_enrich_updates_display_without_changing_original_identity(library):
    original = bytes(80)
    placeholder = dict(species="Sin analizar", species_id=0, level=0, legal=False)
    first = library.deposit("frlg", original, placeholder, {})
    row = library.enrich(first["id"], info(), OWNER)
    assert row["species"] == "Magikarp" and row["nickname"] == "Splash"
    assert row["trainer"] == OWNER and row["version"] == 4
    assert row["legal"] is True
    assert (row["id"], row["sha256"], row["created"], row["game"], row["path"]) == (
        first["id"], first["sha256"], first["created"], first["game"], first["path"])
    assert library.data(row["id"]) == original


def test_enrich_cannot_override_game_hash_path_or_created(library):
    original = bytes(80)
    first = library.deposit("frlg", original, info(), OWNER)
    details = info(game="sv", sha256="changed", path="../../file", created=0)
    row = library.enrich(first["id"], details, dict(OWNER, path="/private", game="sv"))
    assert row["game"] == "frlg" and row["sha256"] == first["sha256"]
    assert row["path"] == first["path"] and row["created"] == first["created"]
    assert "path" not in row["trainer"] and "game" not in row["trainer"]
    assert library.data(row["id"]) == original


def test_enrich_rejects_tampered_file_before_changing_metadata(library):
    first = library.deposit("frlg", bytes(80), info(), OWNER)
    Path(first["path"]).write_bytes(b"x" * 80)
    metadata = Path(first["path"]).with_suffix(".json")
    previous = metadata.read_bytes()
    with pytest.raises(ValueError, match="cambió"):
        library.enrich(first["id"], info("Pikachu"), OWNER)
    assert metadata.read_bytes() == previous
