# qbit-delete-tag

Bash segédprogram qBittorrenthez. A megadott TAG torrentjeit a hozzájuk tartozó adatokkal együtt távolítja el, leválasztott tmux munkamenetben.

## Beállítás

Alapértelmezett WebUI:

```text
http://127.0.0.1:10998
```

Függőségek Debian 12 alatt:

```bash
sudo apt update
sudo apt install -y curl jq tmux
```

Telepítés:

```bash
cd ~/delete-deleted-torrents-from-qbit
mkdir -p ~/bin
install -m 755 tag-delete/qbit-delete-tag ~/bin/qbit-delete-tag
```

Konfiguráció:

```bash
mkdir -p ~/.config/qbit-tag-delete
chmod 700 ~/.config/qbit-tag-delete
cp tag-delete/config.example ~/.config/qbit-tag-delete/config
nano ~/.config/qbit-tag-delete/config
chmod 600 ~/.config/qbit-tag-delete/config
```

A jelszó csak a helyi konfigurációs fájlba kerüljön, ne a repositoryba.

## Használat

Interaktív TAG-bekérés:

```bash
qbit-delete-tag
```

Közvetlen TAG-megadás:

```bash
qbit-delete-tag ncore
```

Hibakereséshez, tmux nélkül:

```bash
qbit-delete-tag --worker ncore
```

A logok helye:

```text
~/.local/state/qbit-tag-delete/
```

A script a qBittorrent `/api/v2/torrents/delete` végpontját `deleteFiles=true` paraméterrel hívja, majd ellenőrzi, hogy maradt-e torrent a megadott TAG alatt.
