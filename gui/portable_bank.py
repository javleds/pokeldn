"""Immutable received records for the Raspberry Pi portable facilities."""
import base64
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import threading

from pokeldn import pokemon
from pokeldn.app import bank
from pokeldn.app.paths import DATA

GAMES = frozenset(("frlg", "lgpe", "swsh", "bdsp", "pla", "sv", "za"))
OWNER_FIELDS = ("ot", "tid", "sid", "gender", "language", "version", "egg", "handler")
_LOCK = threading.RLock()


class PortableBank:
    """Use the existing bank record format without its conversion/edit operations."""

    def __init__(self, root=None):
        self.root = Path(root) if root is not None else DATA / "portable" / "bank"

    def _row(self, entry):
        meta = bank._read_meta(entry.path)
        game = meta.get("game", entry.game)
        if game not in GAMES:
            raise ValueError("Juego del banco no compatible.")
        return {
            "id": entry.id, "path": entry.path, "game": game,
            "species": str(meta.get("species", "")), "species_id": entry.species_id,
            "nickname": str(meta.get("nickname", "")),
            "trainer": deepcopy(meta.get("owner", {})),
            "version": meta.get("version"), "sha256": meta.get("sha256", ""),
            "legal": entry.legal, "created": entry.created, "summary": entry.summary,
            "shiny": entry.shiny,
        }

    def list(self, query="", game=""):
        if game and game not in GAMES:
            raise ValueError("Juego del banco no compatible.")
        query = query.casefold().strip()
        with _LOCK:
            rows = [self._row(entry) for entry in bank.entries(self.root)]
        return [
            row for row in rows
            if (not game or row["game"] == game)
            and (not query or query in " ".join([
                row["game"], row["species"], row["nickname"],
                *(str(value) for value in row["trainer"].values()),
            ]).casefold())
        ]

    def get(self, entry_id):
        with _LOCK:
            entry = bank.find(entry_id, self.root)
            if entry is None:
                raise ValueError("El Pokémon ya no está en el banco.")
            return self._row(entry)

    def data(self, entry_id):
        with _LOCK:
            entry = bank.find(entry_id, self.root)
            if entry is None:
                raise ValueError("El Pokémon ya no está en el banco.")
            row = self._row(entry)
            content = bank.data(entry)
            if (len(content) not in pokemon.RECORD_SIZES[row["game"]]
                    or hashlib.sha256(content).hexdigest() != row["sha256"]):
                raise ValueError("El archivo original del banco cambió o está incompleto.")
            return content

    def deposit(self, game, data, info, owner):
        if game not in GAMES or not isinstance(data, bytes) or len(data) not in pokemon.RECORD_SIZES[game]:
            raise ValueError("El registro recibido no tiene el formato de este juego.")
        owner = {key: deepcopy(owner[key]) for key in OWNER_FIELDS if key in owner}
        digest = hashlib.sha256(data).hexdigest()
        with _LOCK:
            existing = next((row for row in self.list() if row["sha256"] == digest), None)
            if existing:
                # Detect tampering instead of silently claiming a healthy duplicate.
                self.data(existing["id"])
                return existing
            # _keep preserves the supplied content. Unlike bank.edit/offer, it never
            # serializes PKHeX's reply or applies HOME/handler transformations.
            entry = bank._keep(game, data, info, self.root, "",
                               nickname=str(info.get("nickname", "")), owner=owner,
                               version=owner.get("version"), portable_original=True)
            return self._row(entry)

    def enrich(self, entry_id, info, owner):
        """Update parsed display details without replacing the archived original."""
        with _LOCK:
            self.data(entry_id)
            entry = bank.find(entry_id, self.root)
            meta = bank._read_meta(entry.path)
            # Use the canonical names when the caller is the Spanish display service,
            # matching bank._keep. Only explicit display fields may change.
            details = {**info, **info.get("canonical", {})}
            updated_owner = {key: deepcopy(owner[key]) for key in OWNER_FIELDS if key in owner}
            meta.update(
                species=str(details.get("species", meta.get("species", ""))),
                species_id=int(details.get("species_id", meta.get("species_id", 0))),
                nickname=str(details.get("nickname", meta.get("nickname", ""))),
                shiny=bool(details.get("shiny", meta.get("shiny", False))),
                legal=details.get("legal") is True,
                summary=pokemon.summary(details),
                owner=updated_owner,
                version=updated_owner.get("version"),
            )
            bank._write_meta(entry.path, meta)
            return self.get(entry_id)

    def export(self, ids=None):
        with _LOCK:
            selected = self.list() if ids is None else [self.get(entry_id) for entry_id in dict.fromkeys(ids)]
            records = []
            for row in selected:
                content = self.data(row["id"])
                records.append({
                    "schema": 1, "type": "pokeldn-portable-pokemon",
                    "game": row["game"], "format": pokemon.EXTENSIONS[row["game"]],
                    "original_base64": base64.b64encode(content).decode("ascii"),
                    "sha256": hashlib.sha256(content).hexdigest(),
                    "metadata": {key: deepcopy(row[key]) for key in (
                        "species", "species_id", "nickname", "trainer", "version",
                        "legal", "created", "summary", "shiny")},
                })
            return json.dumps(records, ensure_ascii=False, indent=2).encode("utf-8")

    def delete(self, entry_id):
        with _LOCK:
            self.get(entry_id)
            bank.remove(entry_id, self.root)

    def delete_all(self):
        with _LOCK:
            rows = self.list()
            for row in rows:
                bank.remove(row["id"], self.root)
            return len(rows)
