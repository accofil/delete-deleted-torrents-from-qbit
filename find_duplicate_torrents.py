#!/usr/bin/env python3
import requests
from collections import defaultdict

import os
from dotenv import load_dotenv

load_dotenv()

QBIT_URL = os.getenv("QB_URL")
USERNAME = os.getenv("QB_USER")
PASSWORD = os.getenv("QB_PASS")

session = requests.Session()


def login():
    r = session.post(
        f"{QBIT_URL}/api/v2/auth/login",
        data={"username": USERNAME, "password": PASSWORD},
        timeout=15,
    )
    if r.text != "Ok.":
        raise Exception("Login failed")


def get_torrents():
    r = session.get(f"{QBIT_URL}/api/v2/torrents/info", timeout=30)
    r.raise_for_status()
    return r.json()


def get_trackers(hash_):
    r = session.get(
        f"{QBIT_URL}/api/v2/torrents/trackers",
        params={"hash": hash_},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


def extract_tracker_names(trackers):
    names = []
    for t in trackers:
        url = t.get("url", "")
        if url.startswith("http"):
            domain = url.split("/")[2]
            names.append(domain)
    return list(set(names))


def main():
    login()
    torrents = get_torrents()

    groups = defaultdict(list)

    # csoportosítás name + size alapján
    for t in torrents:
        key = (t["name"], t["size"])
        groups[key].append(t)

    duplicates_found = False

    for (name, size), items in groups.items():
        if len(items) > 1:
            duplicates_found = True
            print("=" * 80)
            print(f"DUPE: {name}")
            print(f"SIZE: {size}")
            print(f"COUNT: {len(items)}\n")

            for t in items:
                hash_ = t["hash"]
                save_path = t.get("save_path", "UNKNOWN")

                try:
                    trackers = get_trackers(hash_)
                    tracker_names = extract_tracker_names(trackers)
                except Exception:
                    tracker_names = ["HIBA"]

                print(f"  HASH: {hash_}")
                print(f"  PATH: {save_path}")
                print(f"  TRACKERS: {', '.join(tracker_names)}\n")

    if not duplicates_found:
        print("Nincs duplikált torrent.")


if __name__ == "__main__":
    main()
