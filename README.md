# Arch Linux Sway Workstation Setup (`LinuxConfig`)

Automated two-stage provisioning for a UEFI + Btrfs Arch Linux laptop with **GRUB snapshot booting** (`snapper` + `snap-pac` + `grub-btrfs` + custom `bioshock.png`), **GNU Stow** dotfiles, and **3-2-1 remote backups** via **Borgmatic** (`Homelab` + `Hetzner Storage Box`).

## Architecture Overview

1. **Stage 1 — `archinstall-config/` (run once from the Arch Live ISO)**
   - Targets **`archinstall 4.5+`** cleanly.
   - `install-bootstrap.sh` inspects your target disk via `generate_config.py`, calculates exact 1 MiB-aligned partition sizes, mounts the FAT32 ESP at `/efi` (so kernels in `/boot` stay inside the `@` Btrfs subvolume), creates `@`, `@home`, `@snapshots`, `@log`, `@pkg`, configures `snapper` + `grub-btrfs` (`/efi/grub`) + `grub-btrfs-overlayfs` + `bioshock.png`, validates the config with `archinstall --dry-run`, and runs the installation.
2. **Stage 2 — `ansible/` (run post-boot, idempotent)**
   - Enables `[multilib]`, `ParallelDownloads`, and bootstraps `yay-bin`.
   - Installs curated Sway/Wayland, Productivity, R/Quarto/LaTeX, Container, CAD/3D, Creative, Gaming, Printing, and Laptop packages defined in [all.yml](ansible/inventory/group_vars/all.yml).
   - Enforces Snapper + `grub-btrfs` + `GRUB_BACKGROUND="/efi/grub/bioshock.png"` configuration.
   - Stows dotfiles under `stow/` cleanly into `$HOME` and clones `Andrapodon/config.nvim` into `~/.config/nvim`.
   - Optionally configures SeaDrive user service, SSH hardening, WireGuard WAN auto-connect, ThinkPad `trackpoint-scroller`, and Borgmatic 3-2-1 backups (`homelab.yaml` + `hetzner.yaml`).

---

## Stage 1: Live ISO Bootstrap

1. Boot the latest official Arch Linux Live ISO in **UEFI mode** and connect to the network (`iwctl` for Wi-Fi).
2. Clone the repository and run the bootstrap:
   ```bash
   git clone https://github.com/Andrapodon/LinuxConfig.git
   cd LinuxConfig/archinstall-config
   ./install-bootstrap.sh
   ```
3. Confirm the detected NVMe/SSD path, hostname, username (`marc`), timezone (`Europe/Zurich`), keymap (`de_CH-latin1`), and passwords.
4. Reboot and remove the USB stick.

---

## Stage 2: First-Boot Provisioning (Ansible + Stow)

1. Log in as your user (`~/LinuxConfig` is pre-copied during Stage 1).
2. Prepare your gitignored local variables for secrets, SSH keys, WireGuard, and Borgmatic targets:
   ```bash
   cd ~/LinuxConfig/ansible
   cp inventory/group_vars/local.yml.example inventory/group_vars/local.yml
   nano inventory/group_vars/local.yml
   # Optional: ansible-vault encrypt inventory/group_vars/local.yml
   ```
3. Run the playbook locally:
   ```bash
   ansible-playbook playbook.yml
   # (Add --ask-vault-pass if you encrypted local.yml with ansible-vault)
   ```
4. **Initialize Borgmatic repositories once** (when `homelab_enabled` / `hetzner_enabled` are turned on in `local.yml`, after copying `/root/.ssh/id_ed25519.pub` to your Homelab & Hetzner Storage Box):
   ```bash
   sudo borgmatic repo-create --encryption repokey-blake2
   ```
