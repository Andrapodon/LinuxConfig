#!/usr/bin/env bash
# ==============================================================================
# Arch Linux Laptop Automated Bootstrap Script (UEFI + Btrfs + GRUB + Snapper)
# Run from the official Arch Linux Live ISO as root.
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$SCRIPT_DIR"

echo "=== Arch Linux Bootstrap (UEFI + Btrfs + GRUB + Snapper) ==="

if [ "${EUID}" -ne 0 ]; then
    echo "[!] Must be run as root from the Arch Linux Live ISO."
    exit 1
fi

if [ ! -d /sys/firmware/efi ]; then
    echo "[!] UEFI mode not detected (/sys/firmware/efi missing). Enable UEFI in BIOS."
    exit 1
fi

if ! curl -fsI --max-time 5 https://archlinux.org >/dev/null 2>&1; then
    echo "[!] No internet connection detected."
    echo "    For Wi-Fi on Live ISO run: iwctl station wlan0 connect <SSID>"
    exit 1
fi

echo "[*] Installing/updating archinstall and python on Live ISO..."
pacman -Sy --noconfirm archinstall python

echo ""
echo "Available disks:"
lsblk -d -e 7,11 -o NAME,PATH,SIZE,MODEL,TRAN
echo ""

DEFAULT_DISK=""
for candidate in /dev/nvme0n1 /dev/sda /dev/vda; do
    if [ -b "$candidate" ]; then
        DEFAULT_DISK="$candidate"
        break
    fi
done

read -rp "Target disk path [${DEFAULT_DISK}]: " TARGET_DISK
TARGET_DISK="${TARGET_DISK:-$DEFAULT_DISK}"
if [ ! -b "$TARGET_DISK" ]; then
    echo "[!] Block device not found: $TARGET_DISK"
    exit 1
fi

read -rp "Hostname [archlaptop]: " HOSTNAME_VAL
HOSTNAME_VAL="${HOSTNAME_VAL:-archlaptop}"

read -rp "Primary username (wheel/sudo) [marc]: " USERNAME_VAL
USERNAME_VAL="${USERNAME_VAL:-marc}"

read -rp "Timezone [Europe/Zurich]: " TIMEZONE_VAL
TIMEZONE_VAL="${TIMEZONE_VAL:-Europe/Zurich}"

read -rp "Console keymap [de_CH-latin1]: " KEYMAP_VAL
KEYMAP_VAL="${KEYMAP_VAL:-de_CH-latin1}"

read -rp "Kernels [linux linux-zen]: " KERNELS_VAL
KERNELS_VAL="${KERNELS_VAL:-linux linux-zen}"

CONFIG_FILE="$SCRIPT_DIR/user_configuration.json"
CREDS_FILE="$SCRIPT_DIR/user_credentials.json"

prompt_password() {
    local prompt_label="$1"
    local p1="" p2=""
    while true; do
        read -rsp "$prompt_label: " p1
        echo >&2
        read -rsp "Confirm $prompt_label: " p2
        echo >&2
        if [ -n "$p1" ] && [ "$p1" = "$p2" ]; then
            printf '%s' "$p1"
            return 0
        fi
        echo "[!] Passwords empty or mismatched. Try again." >&2
    done
}

CREDS_ARGS=()
if [ -f "$CREDS_FILE" ]; then
    read -rp "Use existing user_credentials.json? [Y/n]: " USE_EXISTING_CREDS
    USE_EXISTING_CREDS="${USE_EXISTING_CREDS:-Y}"
else
    USE_EXISTING_CREDS="n"
fi

if [[ ! "$USE_EXISTING_CREDS" =~ ^[Yy]$ ]]; then
    ARCH_ROOT_PASS="$(prompt_password "root password")"
    ARCH_USER_PASS="$(prompt_password "${USERNAME_VAL} password")"
    export ARCH_ROOT_PASS ARCH_USER_PASS
    CREDS_ARGS=(--creds-output "$CREDS_FILE")
fi

read -ra KERNELS_ARR <<< "$KERNELS_VAL"

python3 "$SCRIPT_DIR/generate_config.py" \
    --disk "$TARGET_DISK" \
    --hostname "$HOSTNAME_VAL" \
    --username "$USERNAME_VAL" \
    --timezone "$TIMEZONE_VAL" \
    --keymap "$KEYMAP_VAL" \
    --kernels "${KERNELS_ARR[@]}" \
    --output "$CONFIG_FILE" \
    "${CREDS_ARGS[@]}"

unset ARCH_ROOT_PASS ARCH_USER_PASS || true

echo "[*] Validating configuration with archinstall --dry-run..."
archinstall --dry-run --silent --offline --skip-version-check --skip-wifi-check \
    --config "$CONFIG_FILE" --creds "$CREDS_FILE"

echo ""
echo "=========================================================================="
echo "READY TO WIPE AND INSTALL ON: $TARGET_DISK"
echo "  Hostname: $HOSTNAME_VAL | User: $USERNAME_VAL | Timezone: $TIMEZONE_VAL"
echo "  Bootloader: GRUB (UEFI /efi + kernels in Btrfs @/boot) + Snapper"
echo "=========================================================================="
read -rp "Type YES to wipe $TARGET_DISK and begin installation: " CONFIRM_WIPE
if [ "$CONFIRM_WIPE" != "YES" ]; then
    echo "Aborted before modifying disk."
    exit 0
fi

archinstall --silent --skip-version-check --skip-wifi-check \
    --config "$CONFIG_FILE" --creds "$CREDS_FILE"

if [ -f "$REPO_ROOT/pictures/bioshock.png" ] && [ -d /mnt/efi/grub ]; then
    echo "[*] Installing GRUB background (/efi/grub/bioshock.png)..."
    cp "$REPO_ROOT/pictures/bioshock.png" /mnt/efi/grub/bioshock.png
    sed -i 's|^#\?GRUB_BACKGROUND=.*|GRUB_BACKGROUND="/efi/grub/bioshock.png"|' /mnt/etc/default/grub
    arch-chroot /mnt grub-mkconfig -o /efi/grub/grub.cfg
fi

if [ -d "/mnt/home/$USERNAME_VAL" ]; then
    TARGET_REPO="/mnt/home/$USERNAME_VAL/LinuxConfig"
    if [ ! -e "$TARGET_REPO" ]; then
        echo "[*] Copying LinuxConfig repository into $TARGET_REPO..."
        cp -a "$REPO_ROOT" "$TARGET_REPO"
        rm -f "$TARGET_REPO/archinstall-config/user_credentials.json"
        arch-chroot /mnt chown -R "$USERNAME_VAL:$USERNAME_VAL" "/home/$USERNAME_VAL/LinuxConfig"
    fi
fi

echo "=========================================================================="
echo "Base installation finished! Remove the USB stick and reboot."
echo "After logging in as $USERNAME_VAL, run:"
echo "  cd ~/LinuxConfig/ansible"
echo "  cp inventory/group_vars/local.yml.example inventory/group_vars/local.yml  # edit optional secrets/backups"
echo "  ansible-playbook playbook.yml"
echo "=========================================================================="
