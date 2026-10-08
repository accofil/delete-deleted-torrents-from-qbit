#!/usr/bin/env bash
set -Eeuo pipefail

readonly PROJECT_SLUG="delete-deleted-torrents-from-qbit"
readonly SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly SOURCE_SCRIPT="${SCRIPT_DIR}/delete_deleted_torrents.py"
readonly REQUIREMENTS_FILE="${SCRIPT_DIR}/requirements.txt"
readonly INSTALL_DIR="${QBIT_DELETE_INSTALL_DIR:-/opt/${PROJECT_SLUG}}"
readonly CONFIG_DIR="${QBIT_DELETE_CONFIG_DIR:-/etc/${PROJECT_SLUG}}"
readonly BIN_DIR="${QBIT_DELETE_BIN_DIR:-/usr/local/bin}"
readonly VENV_DIR="${INSTALL_DIR}/venv"
readonly INSTALLED_SCRIPT="${INSTALL_DIR}/delete_deleted_torrents.py"
readonly SKIP_SYSTEM_PACKAGES="${QBIT_DELETE_SKIP_SYSTEM_PACKAGES:-0}"
readonly NO_SUDO="${QBIT_DELETE_NO_SUDO:-0}"

if [[ ! -f "$SOURCE_SCRIPT" || ! -f "$REQUIREMENTS_FILE" ]]; then
    echo "HIBA: az install.sh fájlt a teljes repositoryból futtasd." >&2
    exit 1
fi

if [[ ${EUID} -eq 0 ]]; then
    privilege_command=""
    use_root_ownership=1
elif [[ "$NO_SUDO" == "1" ]]; then
    privilege_command=""
    use_root_ownership=0
elif command -v sudo >/dev/null 2>&1; then
    privilege_command="sudo"
    use_root_ownership=1
else
    echo "HIBA: a telepítéshez root jogosultság vagy sudo szükséges." >&2
    exit 1
fi

install_user="${SUDO_USER:-$(id -un)}"
install_group="$(id -gn "$install_user")"

run_privileged() {
    if [[ -n "$privilege_command" ]]; then
        "$privilege_command" "$@"
    else
        "$@"
    fi
}

read -r -p "Telepítési profil neve [default]: " profile_name
profile_name="${profile_name:-default}"
if [[ ! "$profile_name" =~ ^[a-zA-Z0-9][a-zA-Z0-9._-]*$ ]]; then
    echo "HIBA: a profilnév csak betűt, számot, pontot, _ és - jelet tartalmazhat." >&2
    exit 1
fi

if [[ "$profile_name" == "default" ]]; then
    config_file="${CONFIG_DIR}/config.env"
    default_command_name="qbit-delete-deleted"
else
    config_file="${CONFIG_DIR}/${profile_name}.env"
    default_command_name="qbit-delete-deleted-${profile_name}"
fi

read -r -p "qBittorrent WebUI URL [http://127.0.0.1:8080]: " qbit_url
qbit_url="${qbit_url:-http://127.0.0.1:8080}"
qbit_url="${qbit_url%/}"
if [[ ! "$qbit_url" =~ ^https?://[^[:space:]]+$ ]]; then
    echo "HIBA: az URL-nek http:// vagy https:// kezdetűnek kell lennie." >&2
    exit 1
fi

read -r -p "qBittorrent felhasználónév: " qbit_user
if [[ -z "$qbit_user" ]]; then
    echo "HIBA: a felhasználónév nem lehet üres." >&2
    exit 1
fi

read -r -s -p "qBittorrent jelszó: " qbit_password
echo
if [[ -z "$qbit_password" ]]; then
    echo "HIBA: a jelszó nem lehet üres." >&2
    exit 1
fi

read -r -p \
    "Telepítendő parancsnév/alias [${default_command_name}]: " \
    command_name
command_name="${command_name:-${default_command_name}}"
if [[ ! "$command_name" =~ ^[a-zA-Z0-9][a-zA-Z0-9._-]*$ ]]; then
    echo "HIBA: a parancsnév csak betűt, számot, pontot, _ és - jelet tartalmazhat." >&2
    exit 1
fi

command_path="${BIN_DIR}/${command_name}"
if [[ -e "$command_path" ]]; then
    read -r -p \
        "A(z) ${command_path} már létezik. Felülírhatom biztonsági mentés után? [y/N]: " \
        overwrite_answer
    case "$overwrite_answer" in
        y|Y|yes|YES|igen|IGEN) ;;
        *)
            echo "A telepítés megszakadt; a meglévő parancs nem változott."
            exit 1
            ;;
    esac
fi

if [[ "$SKIP_SYSTEM_PACKAGES" != "1" ]]; then
    if ! command -v apt-get >/dev/null 2>&1; then
        echo "HIBA: ez a telepítő Debian/Ubuntu apt környezetet támogat." >&2
        exit 1
    fi

    echo "Rendszercsomagok telepítése..."
    run_privileged apt-get update
    run_privileged env DEBIAN_FRONTEND=noninteractive \
        apt-get install -y python3 python3-venv ca-certificates
fi

if ! command -v python3 >/dev/null 2>&1; then
    echo "HIBA: a python3 nem érhető el." >&2
    exit 1
fi

temp_dir="$(mktemp -d)"
cleanup() {
    rm -rf -- "$temp_dir"
}
trap cleanup EXIT

{
    printf "QB_URL=%q\n" "$qbit_url"
    printf "QB_USER=%q\n" "$qbit_user"
    printf "QB_PASS=%q\n" "$qbit_password"
} >"${temp_dir}/config.env"
chmod 0600 "${temp_dir}/config.env"

{
    printf "#!/usr/bin/env bash\n"
    printf "set -Eeuo pipefail\n"
    printf "set -a\n"
    printf "source %q\n" "$config_file"
    printf "set +a\n"
    printf "unset QBIT_DELETE_ENV_FILE\n"
    printf "export QBIT_DELETE_INSTANCE=%q\n" "$profile_name"
    printf "export PYTHONUNBUFFERED=1\n"
    printf 'exec %q %q "$@"\n' \
        "${VENV_DIR}/bin/python" \
        "$INSTALLED_SCRIPT"
} >"${temp_dir}/launcher"
chmod 0755 "${temp_dir}/launcher"

echo "Izolált Python-környezet létrehozása..."
run_privileged install -d -m 0755 "$INSTALL_DIR" "$CONFIG_DIR" "$BIN_DIR"
run_privileged python3 -m venv --clear "$VENV_DIR"
run_privileged "${VENV_DIR}/bin/python" -m pip install \
    --disable-pip-version-check \
    --upgrade pip
run_privileged "${VENV_DIR}/bin/python" -m pip install \
    --disable-pip-version-check \
    -r "$REQUIREMENTS_FILE"

run_privileged install -m 0755 "$SOURCE_SCRIPT" "$INSTALLED_SCRIPT"
run_privileged install -m 0644 \
    "$REQUIREMENTS_FILE" "${INSTALL_DIR}/requirements.txt"

timestamp="$(date +%Y%m%d-%H%M%S)"
if run_privileged test -e "$config_file"; then
    run_privileged cp -a -- "$config_file" "${config_file}.backup-${timestamp}"
fi
if run_privileged test -e "$command_path"; then
    run_privileged cp -a -- "$command_path" "${command_path}.backup-${timestamp}"
fi

if ((use_root_ownership)); then
    run_privileged install -o root -g "$install_group" -m 0640 \
        "${temp_dir}/config.env" "$config_file"
    run_privileged install -o root -g root -m 0755 \
        "${temp_dir}/launcher" "$command_path"
else
    install -m 0600 "${temp_dir}/config.env" "$config_file"
    install -m 0755 "${temp_dir}/launcher" "$command_path"
fi

echo
echo "A telepítés elkészült."
echo "Profil: ${profile_name}"
echo "Telepített parancs: ${command_name}"
echo "Konfiguráció: ${config_file}"
echo
echo "Első ellenőrzés törlés nélkül:"
echo "  ${command_name} --dry-run"
echo
echo "Éles futtatás (torrent + adatfájlok törlése):"
echo "  ${command_name}"
echo
echo "Példa napi 03:00-s cron futtatásra:"
printf '  0 3 * * * %s >> "$HOME/%s.log" 2>&1\n' \
    "$command_path" "$command_name"
