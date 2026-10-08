# Delete Deleted Torrents from qBittorrent

A program megkeresi azokat a torrenteket, amelyeket egy támogatott tracker már
töröltnek vagy nem engedélyezettnek jelez. Éles futtatáskor eltávolítja a
torrentet a qBittorrentből, és a hozzá tartozó adatfájlokat is törli a lemezről.

A telepítő több, ugyanazon a szerveren futó qBittorrent-példányt is támogat.
Minden példány külön profilt, külön konfigurációs fájlt és külön parancsot kap.

> [!CAUTION]
> A program éles futtatása megerősítő kérdés nélkül, véglegesen töröl. Elsőként
> mindig a `--dry-run` kapcsolóval ellenőrizd a találati listát.

## Támogatott trackerüzenetek

| Tracker URL kezdete | Törlést kiváltó üzenet |
| --- | --- |
| `https://aither.cc/announce/` | `Torrent has been deleted` |
| `https://hdts-announce.ru/` | `Torrent is not authorized for use on this tracker` |
| `https://trackerprxy.digitalcore.club/` | `Torrent does not exist on this tracker` |
| `http://ncore.sh:2710/` | `err: unregistered torrent` |

A program csak akkor jelöl törlésre egy torrentet, ha a tracker URL-je és a
tracker üzenete is ugyanahhoz a szabályhoz illeszkedik. Az üzenet
összehasonlítása nem érzékeny a kis- és nagybetűkre.

Az nCore esetén például az `invalid passkey`, időtúllépés vagy más trackerhiba
nem vált ki törlést; kizárólag az `err: unregistered torrent` üzenet.

## Mire lesz szükséged?

- Debian vagy Ubuntu rendszerű szerver;
- működő qBittorrent WebUI/API;
- minden qBittorrent-példány WebUI-címe, felhasználóneve és jelszava;
- internetkapcsolat a telepítés alatt;
- `sudo` vagy root jogosultság.

A helyi WebUI-cím formája általában:

```text
http://127.0.0.1:PORT
```

## Telepítés egy qBittorrent-példányhoz

### 1. Kapcsolódás a szerverhez

```bash
ssh -p SSH_PORT FELHASZNALO@SZERVER_IP
```

### 2. A repository letöltése

```bash
cd ~
git clone https://github.com/accofil/delete-deleted-torrents-from-qbit.git
cd delete-deleted-torrents-from-qbit
```

Ha a könyvtár már létezik:

```bash
cd ~/delete-deleted-torrents-from-qbit
git pull --ff-only
```

### 3. A telepítő indítása

```bash
chmod +x install.sh
./install.sh
```

A telepítőt normál felhasználóként indítsd, ne `sudo ./install.sh` formában.
A szükséges pontokon maga hívja meg a `sudo` parancsot.

A kérdések:

```text
Telepítési profil neve [default]:
qBittorrent WebUI URL [http://127.0.0.1:8080]:
qBittorrent felhasználónév:
qBittorrent jelszó:
Telepítendő parancsnév/alias [qbit-delete-deleted]:
```

A `default` profil megőrzi a korábbi telepítési elrendezést:

- konfiguráció: `/etc/delete-deleted-torrents-from-qbit/config.env`;
- parancs: `/usr/local/bin/qbit-delete-deleted`.

### 4. Első ellenőrzés törlés nélkül

```bash
qbit-delete-deleted --dry-run
```

A `--dry-run` kapcsoló lekéri és kilistázza a találatokat, de sem a torrentet,
sem az adatfájlokat nem törli.

### 5. Éles futtatás

Csak a találati lista ellenőrzése után:

```bash
qbit-delete-deleted
```

Ez a parancs a találatokat a qBittorrentből és a lemezről is törli.

## Több qBittorrent-példány ugyanazon a szerveren

Minden példányhoz egyszer futtasd le a telepítőt, eltérő profilnévvel. A
profilnév alapján külön konfiguráció és külön alapértelmezett parancs készül.

Példa két példányra:

### Első profil

```bash
./install.sh
```

Példaválaszok:

```text
Telepítési profil neve [default]: primary
qBittorrent WebUI URL [http://127.0.0.1:8080]: http://127.0.0.1:8080
qBittorrent felhasználónév: primary-user
qBittorrent jelszó:
Telepítendő parancsnév/alias [qbit-delete-deleted-primary]:
```

Eredmény:

```text
/usr/local/bin/qbit-delete-deleted-primary
/etc/delete-deleted-torrents-from-qbit/primary.env
```

### Második profil

A rendszercsomagokat nem szükséges még egyszer telepíteni:

```bash
QBIT_DELETE_SKIP_SYSTEM_PACKAGES=1 ./install.sh
```

Példaválaszok:

```text
Telepítési profil neve [default]: secondary
qBittorrent WebUI URL [http://127.0.0.1:8080]: http://127.0.0.1:8081
qBittorrent felhasználónév: secondary-user
qBittorrent jelszó:
Telepítendő parancsnév/alias [qbit-delete-deleted-secondary]:
```

Eredmény:

```text
/usr/local/bin/qbit-delete-deleted-secondary
/etc/delete-deleted-torrents-from-qbit/secondary.env
```

Mindkét példány ellenőrzése:

```bash
qbit-delete-deleted-primary --dry-run
qbit-delete-deleted-secondary --dry-run
```

A profilok külön futási zárat használnak. Ugyanaz a profil nem indul el kétszer
párhuzamosan, de két külön qBittorrent-profil egymástól függetlenül futtatható.

## Automatikus futtatás cronnal

A telepített parancs futás közben nem kér adatot, ezért cronból is használható.
Két profil esetén érdemes néhány perccel eltolni a futásokat.

```bash
crontab -e
```

Példa napi futtatásra:

```cron
0 3 * * * /usr/local/bin/qbit-delete-deleted-primary >> "$HOME/qbit-delete-deleted-primary.log" 2>&1
10 3 * * * /usr/local/bin/qbit-delete-deleted-secondary >> "$HOME/qbit-delete-deleted-secondary.log" 2>&1
```

A mentett cron ellenőrzése:

```bash
crontab -l
```

A naplók megtekintése:

```bash
tail -n 100 "$HOME/qbit-delete-deleted-primary.log"
tail -n 100 "$HOME/qbit-delete-deleted-secondary.log"
```

## Telepített fájlok

| Elem | Hely |
| --- | --- |
| Program és virtuális környezet | `/opt/delete-deleted-torrents-from-qbit/` |
| Alapértelmezett profil konfigurációja | `/etc/delete-deleted-torrents-from-qbit/config.env` |
| Névvel ellátott profil konfigurációja | `/etc/delete-deleted-torrents-from-qbit/PROFIL.env` |
| Telepített parancs | `/usr/local/bin/qbit-delete-deleted[-PROFIL]` |

A konfiguráció `0640` jogosultságot kap. A `root` és a telepítést végző
felhasználó csoportja olvashatja. A jelszót tartalmazó konfiguráció nem kerül a
GitHub repositoryba.

## Frissítés

A kód frissítése:

```bash
cd ~/delete-deleted-torrents-from-qbit
git pull --ff-only
```

Ezután minden telepített profilhoz futtasd újra az installert ugyanazzal a
profilnévvel, WebUI-adatokkal és parancsnévvel. A telepítő a meglévő
konfigurációról és launcherről időbélyeges biztonsági mentést készít.

Példa két profilnál:

```bash
./install.sh
QBIT_DELETE_SKIP_SYSTEM_PACKAGES=1 ./install.sh
```

Amikor a meglévő parancs felülírására kérdez rá, a folytatáshoz válaszolj `y`
betűvel.

## Gyakori hibák

### A qBittorrent bejelentkezés sikertelen

Ellenőrizd:

- a megfelelő példány WebUI-portját;
- a WebUI felhasználónevét és jelszavát;
- hogy a WebUI a `127.0.0.1` címen vagy a megadott címen figyel-e;
- hogy valóban a megfelelő profil parancsát futtatod-e.

### A parancs nem található

```bash
ls -l /usr/local/bin/qbit-delete-deleted*
```

### A cron nem fut

```bash
systemctl status cron --no-pager
crontab -l
journalctl -u cron --since today --no-pager
```

### A program szerint ugyanahhoz a profilhoz már fut egy példány

Ez azt jelenti, hogy ugyanazt a profilparancsot egy másik folyamat már
futtatja. Külön profilok nem blokkolják egymást.

## Kézi futtatás telepítés nélkül

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
nano .env
.venv/bin/python delete_deleted_torrents.py --dry-run
```

Éles futtatás:

```bash
.venv/bin/python delete_deleted_torrents.py
```

## Fejlesztői ellenőrzés

```bash
.venv/bin/python -m unittest discover -s tests -v
bash -n install.sh
python3 -m py_compile delete_deleted_torrents.py
```

## A repository tartalma

| Fájl | Leírás |
| --- | --- |
| `delete_deleted_torrents.py` | Trackerüzenetek ellenőrzése és törlés |
| `install.sh` | Többprofils, interaktív Debian/Ubuntu telepítő |
| `requirements.txt` | Python-függőségek |
| `.env.example` | Minta kézi futtatáshoz |
| `find_duplicate_torrents.py` | Kiegészítő duplikátumkereső |
| `tests/` | Automatikus tesztek |
