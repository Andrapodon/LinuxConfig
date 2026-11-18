# Arch Linux Sway Workstation Setup (`LinuxConfig`)

Automated two-stage provisioning for a **UEFI + Btrfs** Arch Linux laptop with **GRUB snapshot booting** (`snapper` + `snap-pac` + `grub-btrfs` + `bioshock.png`), **GNU Stow** dotfiles, [`config.nvim`](https://github.com/Andrapodon/config.nvim), Brother **QL-720NW** LaTeX printing ([`ql-print`](stow/scripts/.local/bin/ql-print)), **Proton `pass-cli`** secret management, and **3-2-1 remote backups** via **Borgmatic** (`Homelab` + `Hetzner Storage Box`).

This repository is public and contains **no secrets, private keys, or personal server endpoints**. Machine-specific overrides live in the gitignored `ansible/inventory/group_vars/local.yml`, and credentials/keys live in Proton Pass.

---

## Architecture Overview

1. **Stage 1 — `archinstall-config/` (run once from the Arch Live ISO)**
   - Targets **`archinstall 4.5+`**.
   - [`install-bootstrap.sh`](archinstall-config/install-bootstrap.sh) detects the target block device, calculates exact 1 MiB-aligned partitions via [`generate_config.py`](archinstall-config/generate_config.py) (`1024 MiB` FAT32 ESP mounted at **`/efi`** + remainder Btrfs with `@`, `@home`, `@snapshots`, `@log`, `@pkg`), keeps kernels in `@/boot` inside Btrfs snapshots, configures `snapper` + `grub-btrfs` + `grub-btrfs-overlayfs` + [`bioshock.png`](pictures/bioshock.png), validates with `archinstall --dry-run`, and runs the installation.
   - Copies this repository cleanly into `/home/<user>/LinuxConfig` (removing temporary `user_credentials.json`).
2. **Stage 2 — `ansible/` (run post-boot, idempotent)**
   - [`playbook.yml`](ansible/playbook.yml) enables `[multilib]`, bootstraps `yay-bin`, installs curated Sway/Wayland, Science/R/Quarto/LaTeX, Container, CAD/3D, Creative, Gaming, Printing (`brother-ql`), and Laptop packages defined in [`all.yml`](ansible/inventory/group_vars/all.yml).
   - Stows `stow/*` packages into `$HOME` (including scripts in `~/.local/bin/`), clones `Andrapodon/config.nvim` into `~/.config/nvim`, configures UFW + Snapper + `grub-btrfs`, and installs `proton-pass-cli-bin`.
   - Optionally hardens `sshd`, configures WireGuard WAN auto-connect, enables hardware-specific laptop tweaks (`local.yml`), and deploys `/etc/borgmatic.d/{homelab,hetzner}.yaml` + `borgmatic.timer`.

---

## Part 1: Arch Live ISO USB Setup (Stage 1)

1. **Boot the official Arch Linux Live ISO in UEFI mode** (disable Legacy/CSM in firmware).
   Verify UEFI and optionally set the Swiss German keyboard layout on the ISO:

   ```bash
   ls /sys/firmware/efi/efivars   # must exist
   loadkeys de_CH-latin1          # optional on ISO console
   ```

2. **Connect to the internet:**
   - **Ethernet**: usually connects automatically via DHCP.
   - **Wi-Fi (`iwctl`)**:

     ```bash
     iwctl
     device list
     station wlan0 scan
     station wlan0 get-networks
     station wlan0 connect "<YOUR_SSID>"
     exit
     ```

   Verify connectivity:

   ```bash
   curl -fsI https://archlinux.org
   ```

3. **Clone `LinuxConfig` over HTTPS** (no SSH keys required on the ISO) and start the installer:

   ```bash
   command -v git >/dev/null || pacman -Sy --noconfirm git
   git clone https://github.com/Andrapodon/LinuxConfig.git ~/LinuxConfig
   cd ~/LinuxConfig/archinstall-config
   ./install-bootstrap.sh
   ```

4. **Follow the interactive prompts:**
   - Confirms root + UEFI + HTTPS and updates `archinstall` and `python` on the Live ISO.
   - Lists `lsblk` disks and prompts for:
     - **Target disk** (e.g. `/dev/nvme0n1`)
     - **Hostname** (default: `archlaptop`)
     - **Primary username** (default: `marc`)
     - **Timezone** (default: `Europe/Zurich`)
     - **Console keymap** (default: `de_CH-latin1`)
     - **Kernels** (default: `linux linux-zen`)
     - **`root`** and **user** passwords
   - Runs `archinstall --dry-run` first, then asks you to type **`YES`** before wiping the target disk.
   - When finished, **remove the USB stick and reboot**:

     ```bash
     reboot
     ```

---

## Part 2: First Boot & Ansible Pass 1 (Base GUI + Tooling)

Stage 1 installs the **Minimal** profile with **NetworkManager** (leaving `ly` + `sway` to Ansible). Wait until Ansible Pass 1 finishes before trying to launch Sway or browser logins.

> [!IMPORTANT]
> **Log in on `tty2` (`Alt+F2`), not `tty1`!**
> During Pass 1, Ansible disables and stops `getty@tty1.service` before enabling `ly@tty1.service`. Running `ansible-playbook` inside `tty1` will terminate your shell mid-run when `getty@tty1` stops. Pressing **`Alt+F2`** at the boot login prompt avoids this cleanly.

1. **Press `Alt+F2`**, log in as your user (`marc`), and reconnect Wi-Fi via `nmcli` if not using Ethernet:

   ```bash
   nmcli device wifi list
   nmcli device wifi connect "<YOUR_SSID>" --ask
   ```

2. **Verify `~/LinuxConfig`** (`install-bootstrap.sh` pre-copied it into `/home/<user>/LinuxConfig`; pull latest commits or clone manually if absent):

   ```bash
   if [ -d ~/LinuxConfig/.git ]; then
     cd ~/LinuxConfig && git pull
   else
     git clone https://github.com/Andrapodon/LinuxConfig.git ~/LinuxConfig
   fi
   ```

3. **Run Ansible Pass 1** (before creating `local.yml` — roles that depend on keys/endpoints like `ssh_remote`, `wireguard_vpn`, and `borgmatic_backups` safely skip until configured in Part 3):

   ```bash
   cd ~/LinuxConfig/ansible
   ansible-playbook playbook.yml
   ```

   Enter your user password when prompted for **`BECOME password:`** (`become_ask_pass = True` in [`ansible.cfg`](ansible/ansible.cfg)).

4. **Reboot into the `ly` display manager + Sway** (also activates `docker` / `video` group memberships cleanly):

   ```bash
   sudo reboot
   ```

   At `ly`, select **Sway** and log in (`Super+Return` opens `alacritty`, tapping `Super_L` opens `fuzzel`, `Super+Shift+f` opens `firefox`, `Super+Shift+w` toggles `workspace.target`).

---

## Part 3: Proton `pass-cli`, Secrets & Ansible Pass 2

Once inside Sway (with `firefox` installed) — or even from a headless TTY using a Personal Access Token — sign into Proton Pass to restore SSH keys, `.pem` certificates, and secret config values.

1. **Authenticate `pass-cli`:**
   Because Sway runs without GNOME Keyring or KWallet enabled by default, tell `pass-cli` to store its key cleanly via filesystem protection (add this to `~/.bashrc` or export in your shell):

   ```bash
   export PROTON_PASS_KEY_PROVIDER=fs
   ```

   Then log in using **either**:
   - **Web login (inside Sway with Firefox):**

     ```bash
     pass-cli login
     ```

   - **Headless / no-browser login (TTY or SSH, using a Proton Pass PAT):**

     ```bash
     pass-cli login --pat "pst_<token>::<key>"
     ```

2. **Restore SSH keys, `.pem` certificates, and root's backup key:**
   - **User SSH keys / `.pem` certs:** either use Proton Pass's built-in agent (`pass-cli ssh-agent start` / `pass-cli ssh-agent load`) or extract your private keys / `.pem` files with `pass-cli item view` / `pass-cli item attachment` / `pass-cli inject` into `~/.ssh/` (`chmod 700 ~/.ssh && chmod 600 ~/.ssh/id_*`).
   - **Root SSH key for unattended Borgmatic backups (`borgmatic.timer` runs as `root`):** restore your backup key cleanly to `/root/.ssh/id_ed25519` with strict permissions:

     ```bash
     sudo install -d -m 700 -o root -g root /root/.ssh
     # Write private key from pass-cli (or ~/.ssh) into /root/.ssh/id_ed25519 (mode 0600)
     sudo chmod 600 /root/.ssh/id_ed25519
     ```

   - **Authorize `/root/.ssh/id_ed25519.pub` and seed `/root/.ssh/known_hosts`** (required because [`borgmatic-repo.yaml.j2`](ansible/roles/borgmatic_backups/templates/borgmatic-repo.yaml.j2) uses `-o BatchMode=yes`, which rejects unknown host keys without prompting):

     ```bash
     # 1. Homelab target (SSH port 22)
     sudo ssh-copy-id -i /root/.ssh/id_ed25519.pub backup@<homelab-host>
     sudo ssh -i /root/.ssh/id_ed25519 backup@<homelab-host> "true"

     # 2. Hetzner Storage Box (SSH port 23, SFTP mode)
     sudo ssh-copy-id -i /root/.ssh/id_ed25519.pub -p 23 -s uXXXXXX@uXXXXXX.your-storagebox.de
     sudo ssh -i /root/.ssh/id_ed25519 -p 23 uXXXXXX@uXXXXXX.your-storagebox.de ls
     ```

3. **Create and populate gitignored `ansible/inventory/group_vars/local.yml`:**

   ```bash
   cd ~/LinuxConfig/ansible
   cp inventory/group_vars/local.yml.example inventory/group_vars/local.yml
   chmod 600 inventory/group_vars/local.yml
   ```

   Edit `inventory/group_vars/local.yml` (based on [`local.yml.example`](ansible/inventory/group_vars/local.yml.example), or populate a template via `pass-cli inject --in-file ... --out-file inventory/group_vars/local.yml --file-mode 0600`):
   - `ssh_remote.maintainer_public_keys`: add your ED25519 public key so `sshd` is hardened (key-only) and enabled.
   - `home_wifi_ssids` & `wireguard.*`: set `wireguard.enabled: true` + endpoint/keys to auto-connect WireGuard whenever outside home Wi-Fi.
   - `borgmatic_targets`: set `encryption_passphrase`, `homelab_enabled: true` + `homelab_repo`, and `hetzner_enabled: true` + `hetzner_repo` (`ssh://uXXXXXX@uXXXXXX.your-storagebox.de:23/./archlaptop`).
   - **Hardware-specific toggles** (kept `false` in [`all.yml`](ansible/inventory/group_vars/all.yml) by default): enable `enable_trackpoint_scroller: true` only on a ThinkPad with a TrackPoint, or `enable_tlp_custom_conf: true` / `enable_custom_sleep_conf: true` if desired.
   - *(Optional)* Encrypt `local.yml` at rest:

     ```bash
     ansible-vault encrypt inventory/group_vars/local.yml
     ```

4. **Run Ansible Pass 2:**

   ```bash
   cd ~/LinuxConfig/ansible
   ansible-playbook playbook.yml
   # Add --ask-vault-pass if you encrypted local.yml with ansible-vault
   ```

5. **Switch Git origins from HTTPS to SSH** once SSH keys are active so you can push updates cleanly:

   ```bash
   cd ~/LinuxConfig && git remote set-url origin git@github.com:Andrapodon/LinuxConfig.git
   cd ~/.config/nvim && git remote set-url origin git@github.com:Andrapodon/config.nvim.git
   ```

---

## Part 4: 3-2-1 Backups (`borgmatic`) & Old SSD Migration (`rsync`)

### 1. Initialize Borgmatic Repositories (Once Per Machine)

After Pass 2 deploys `/etc/borgmatic.d/homelab.yaml` and `/etc/borgmatic.d/hetzner.yaml`:

```bash
sudo borgmatic repo-create --encryption repokey-blake2
sudo borgmatic create --verbosity 1 --stats
systemctl status borgmatic.timer
```

> [!CAUTION]
> Save your `encryption_passphrase` AND `sudo borgmatic key export` output inside **Proton Pass**! Without the passphrase and repokey, remote encrypted archives cannot be restored if the laptop SSD is lost.

### 2. Selective Data Migration from the Old SSD

Mount the old SSD **read-only** and selectively `rsync` user data directories without overwriting new Stow symlinks or XDG configs:

```bash
lsblk -f
sudo mkdir -p /mnt/oldssd
sudo mount -o ro /dev/sdX2 /mnt/oldssd

rsync -avh --progress --exclude='*.bak' \
  /mnt/oldssd/home/<olduser>/{Documents,"Calibre Library",Projects,Pictures,Downloads} \
  ~/

# Inspect & migrate GnuPG or KeePassXC DB separately if stored outside SeaDrive:
# rsync -avh /mnt/oldssd/home/<olduser>/.gnupg ~/ && chmod 700 ~/.gnupg

sudo umount /mnt/oldssd
```

---

## Part 5: Verification & Quick Reference

### Btrfs + Snapper + GRUB Snapshot Booting

```bash
sudo snapper -c root list
sudo snapper -c home list
sudo systemctl status grub-btrfsd.service snapper-timeline.timer snapper-cleanup.timer
grep -E "bioshock|snapshots" /efi/grub/grub.cfg | head -n 10
```

Reboot to confirm the custom `bioshock.png` GRUB background and the **Arch Linux snapshots** submenu appear.

### Custom Scripts (`~/.local/bin/`)

- **Brother QL-720NW LaTeX/Markdown Label Printer ([`ql-print`](stow/scripts/.local/bin/ql-print)):**

  ```bash
  echo '$E = mc^2$' | ql-print
  echo 'Workshop Box #1' | ql-print --ip 192.168.1.48 --label 62x29 --preview gui
  ```

- **Paperless-ngx AI Document Tagger ([`batch_process_final.py`](stow/scripts/.local/bin/batch_process_final.py)):**
  Reads `GEMINI_API_KEY`, `PAPERLESS_URL` (`--url`), `PAPERLESS_TOKEN` (`--token`), and optional `PAPERLESS_USER` (`--user`) at runtime — wrap with `pass-cli run` or shell environment variables so no tokens sit on disk.
- **Homelab Proxmox LXC Upgrade Helpers:** `upgrade_lxc.sh`, `wait_for_debian13.sh`, `finish_upgrade.sh`.

### Customizing Packages & Features

Edit feature flags or package lists in [`ansible/inventory/group_vars/all.yml`](ansible/inventory/group_vars/all.yml), or override host settings in `ansible/inventory/group_vars/local.yml`, then re-run:

```bash
cd ~/LinuxConfig/ansible
ansible-playbook playbook.yml
```
