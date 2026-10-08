#!/usr/bin/env python3
"""Remove tracker-deleted torrents and their data through qBittorrent."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import requests
from dotenv import load_dotenv

DELETE_RULES = (
    (
        "https://aither.cc/announce/",
        "Torrent has been deleted",
    ),
    (
        "https://hdts-announce.ru/",
        "Torrent is not authorized for use on this tracker",
    ),
    (
        "https://trackerprxy.digitalcore.club/",
        "Torrent does not exist on this tracker",
    ),
    (
        "http://ncore.sh:2710/",
        "err: unregistered torrent",
    ),
)


@dataclass(frozen=True)
class Config:
    qbit_url: str
    username: str
    password: str


@dataclass(frozen=True)
class DeleteCandidate:
    torrent_hash: str
    name: str
    tracker_url: str
    message: str


class QBittorrentClient:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.session = requests.Session()

    def login(self) -> None:
        response = self.session.post(
            f"{self.config.qbit_url}/api/v2/auth/login",
            data={
                "username": self.config.username,
                "password": self.config.password,
            },
            timeout=15,
        )
        response.raise_for_status()
        if response.text.strip() != "Ok.":
            raise RuntimeError(
                "A qBittorrent bejelentkezés sikertelen. "
                f"Válasz: {response.text.strip() or '<üres>'}"
            )

    def get_torrents(self) -> list[dict]:
        response = self.session.get(
            f"{self.config.qbit_url}/api/v2/torrents/info",
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def get_trackers(self, torrent_hash: str) -> list[dict]:
        response = self.session.get(
            f"{self.config.qbit_url}/api/v2/torrents/trackers",
            params={"hash": torrent_hash},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def delete_torrent(self, torrent_hash: str) -> None:
        response = self.session.post(
            f"{self.config.qbit_url}/api/v2/torrents/delete",
            data={
                "hashes": torrent_hash,
                "deleteFiles": "true",
            },
            timeout=30,
        )
        response.raise_for_status()


def load_config() -> Config:
    configured_env = os.getenv("QBIT_DELETE_ENV_FILE")
    if configured_env:
        env_path = Path(configured_env).expanduser()
        if not env_path.is_file():
            raise ValueError(f"A konfigurációs fájl nem található: {env_path}")
        load_dotenv(env_path)
    else:
        load_dotenv()

    qbit_url = (os.getenv("QB_URL") or "").strip().rstrip("/")
    username = (os.getenv("QB_USER") or "").strip()
    password = os.getenv("QB_PASS") or ""

    missing = [
        name
        for name, value in (
            ("QB_URL", qbit_url),
            ("QB_USER", username),
            ("QB_PASS", password),
        )
        if not value
    ]
    if missing:
        raise ValueError(
            "Hiányzó konfigurációs érték(ek): " + ", ".join(missing)
        )
    if not qbit_url.startswith(("http://", "https://")):
        raise ValueError("A QB_URL értékének http:// vagy https:// kezdetűnek kell lennie.")

    return Config(qbit_url=qbit_url, username=username, password=password)


def matching_delete_rule(
    tracker_url: str,
    tracker_message: str,
) -> tuple[str, str] | None:
    normalized_message = tracker_message.casefold()
    for expected_url, expected_message in DELETE_RULES:
        if (
            tracker_url.startswith(expected_url)
            and expected_message.casefold() in normalized_message
        ):
            return expected_url, expected_message
    return None


def find_delete_candidates(
    client: QBittorrentClient,
) -> tuple[list[DeleteCandidate], int]:
    torrents = client.get_torrents()
    candidates: list[DeleteCandidate] = []
    tracker_errors = 0

    print(f"Torrentek száma összesen: {len(torrents)}")
    print("Keresés törölt vagy nem engedélyezett torrentek alapján...\n")

    for torrent in torrents:
        torrent_hash = torrent["hash"]
        torrent_name = torrent.get("name", "UNKNOWN")

        try:
            trackers = client.get_trackers(torrent_hash)
        except (requests.RequestException, ValueError) as error:
            tracker_errors += 1
            print(f"HIBA tracker lekérésnél: {torrent_name}")
            print(error)
            continue

        for tracker in trackers:
            tracker_url = tracker.get("url") or ""
            tracker_message = tracker.get("msg") or ""
            if matching_delete_rule(tracker_url, tracker_message):
                candidates.append(
                    DeleteCandidate(
                        torrent_hash=torrent_hash,
                        name=torrent_name,
                        tracker_url=tracker_url,
                        message=tracker_message,
                    )
                )
                break

    return candidates, tracker_errors


def _lock_identifier(instance_name: str | None = None) -> str:
    identity = (
        instance_name
        or os.getenv("QBIT_DELETE_INSTANCE")
        or os.getenv("QBIT_DELETE_ENV_FILE")
        or "default"
    )
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]


def acquire_single_instance_lock(instance_name: str | None = None):
    lock_path = (
        Path(tempfile.gettempdir())
        / (
            "delete-deleted-torrents-from-qbit-"
            f"{os.getuid()}-{_lock_identifier(instance_name)}.lock"
        )
    )
    flags = os.O_CREAT | os.O_RDWR
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW

    descriptor = os.open(lock_path, flags, 0o600)
    lock_file = os.fdopen(descriptor, "w")
    try:
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        lock_file.close()
        return None
    return lock_file


def run_cleanup(*, dry_run: bool = False) -> int:
    try:
        config = load_config()
        client = QBittorrentClient(config)
        client.login()
        candidates, tracker_errors = find_delete_candidates(client)
    except (requests.RequestException, RuntimeError, ValueError) as error:
        print(f"HIBA: {error}", file=sys.stderr)
        return 1

    if not candidates:
        print("Nincs törlendő torrent.")
        return 1 if tracker_errors else 0

    print("Törlendő torrentek:")
    for candidate in candidates:
        print(f"- {candidate.name}")
        print(f"  tracker: {candidate.tracker_url}")
        print(f"  message: {candidate.message}")

    print(f"\nÖsszesen törlendő: {len(candidates)}")

    if dry_run:
        print("\nDRY-RUN: ellenőrzés kész; nem történt törlés.")
        return 1 if tracker_errors else 0

    print("\nTörlés indul: torrent + adatfájlok...")
    delete_errors = 0
    for candidate in candidates:
        try:
            client.delete_torrent(candidate.torrent_hash)
            print(f"TÖRÖLVE: {candidate.name}")
        except requests.RequestException as error:
            delete_errors += 1
            print(f"HIBA törlésnél: {candidate.name}", file=sys.stderr)
            print(error, file=sys.stderr)

    print("\nKész.")
    return 1 if tracker_errors or delete_errors else 0


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "A támogatott trackerek által töröltnek jelzett torrentek "
            "eltávolítása qBittorrentből az adatfájlokkal együtt."
        )
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="csak listázza a találatokat; nem töröl torrentet vagy adatfájlt",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    try:
        lock_file = acquire_single_instance_lock()
    except OSError as error:
        print(f"HIBA: a futási zár nem hozható létre: {error}", file=sys.stderr)
        return 1

    if lock_file is None:
        print("Ugyanehhez a qBittorrent-profilhoz egy másik példány már fut.")
        return 0

    try:
        return run_cleanup(dry_run=args.dry_run)
    finally:
        fcntl.flock(lock_file, fcntl.LOCK_UN)
        lock_file.close()


if __name__ == "__main__":
    raise SystemExit(main())
