#!/usr/bin/env python3
"""Generate archinstall 4.5 configuration and credentials JSON from disk geometry."""

from __future__ import annotations

import argparse
import copy
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any

MIB = 1024 * 1024
DEFAULT_EFI_MIB = 1024
DEFAULT_START_MIB = 1
DEFAULT_BTRFS_MOUNT_OPTIONS = ["compress=zstd:1", "noatime", "discard=async"]
DEFAULT_BTRFS_SUBVOLUMES = [
    {"name": "@", "mountpoint": "/"},
    {"name": "@home", "mountpoint": "/home"},
    {"name": "@snapshots", "mountpoint": "/.snapshots"},
    {"name": "@log", "mountpoint": "/var/log"},
    {"name": "@pkg", "mountpoint": "/var/cache/pacman/pkg"},
]


def query_disk_geometry(disk: Path) -> tuple[int, int]:
    """Return (total_bytes, logical_sector_size) for a block device via lsblk."""
    proc = subprocess.run(
        ["lsblk", "-J", "-b", "-n", "-d", "-o", "PATH,SIZE,LOG-SEC", str(disk)],
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(proc.stdout)
    devices = payload.get("blockdevices", [])
    if not devices:
        raise RuntimeError(f"Block device not found via lsblk: {disk}")

    dev = devices[0]
    total_bytes = int(dev["size"])
    sector_size = int(dev.get("log-sec") or 512)
    return total_bytes, sector_size


def compute_btrfs_size_bytes(
    total_bytes: int,
    efi_start_mib: int = DEFAULT_START_MIB,
    efi_size_mib: int = DEFAULT_EFI_MIB,
) -> tuple[int, int]:
    """Compute 1 MiB-aligned Btrfs start (MiB) and length (bytes) leaving 1 MiB for backup GPT."""
    btrfs_start_mib = efi_start_mib + efi_size_mib
    btrfs_start_bytes = btrfs_start_mib * MIB
    # Matches archinstall Size.gpt_end().align(): reserve 1 MiB for GPT header, floor to 1 MiB.
    aligned_end_bytes = ((total_bytes - MIB) // MIB) * MIB
    btrfs_size_bytes = aligned_end_bytes - btrfs_start_bytes

    if btrfs_size_bytes < 16 * 1024 * MIB:
        raise ValueError(
            f"Target disk too small ({total_bytes / (1024**3):.1f} GiB) after {btrfs_start_mib} MiB EFI split"
        )

    return btrfs_start_mib, btrfs_size_bytes


def build_disk_config(
    disk: Path,
    total_bytes: int,
    sector_size: int,
    efi_size_mib: int = DEFAULT_EFI_MIB,
) -> dict[str, Any]:
    """Build an archinstall 4.5 manual_partitioning disk_config dict."""
    btrfs_start_mib, btrfs_size_bytes = compute_btrfs_size_bytes(
        total_bytes=total_bytes,
        efi_start_mib=DEFAULT_START_MIB,
        efi_size_mib=efi_size_mib,
    )
    sector_obj = {"unit": "B", "value": sector_size}

    return {
        "config_type": "manual_partitioning",
        "device_modifications": [
            {
                "device": str(disk),
                "wipe": True,
                "partitions": [
                    {
                        "obj_id": str(uuid.uuid4()),
                        "status": "create",
                        "type": "primary",
                        "start": {"unit": "MiB", "value": DEFAULT_START_MIB, "sector_size": sector_obj},
                        "size": {"unit": "MiB", "value": efi_size_mib, "sector_size": sector_obj},
                        "fs_type": "fat32",
                        "mountpoint": "/efi",
                        "mount_options": [],
                        "flags": ["boot", "esp"],
                        "dev_path": None,
                        "btrfs": [],
                    },
                    {
                        "obj_id": str(uuid.uuid4()),
                        "status": "create",
                        "type": "primary",
                        "start": {"unit": "MiB", "value": btrfs_start_mib, "sector_size": sector_obj},
                        "size": {"unit": "B", "value": btrfs_size_bytes, "sector_size": sector_obj},
                        "fs_type": "btrfs",
                        "mountpoint": None,
                        "mount_options": list(DEFAULT_BTRFS_MOUNT_OPTIONS),
                        "flags": [],
                        "dev_path": None,
                        "btrfs": copy.deepcopy(DEFAULT_BTRFS_SUBVOLUMES),
                    },
                ],
            }
        ],
    }


def build_config(
    template: dict[str, Any],
    disk: Path,
    total_bytes: int,
    sector_size: int,
    hostname: str,
    timezone: str,
    keymap: str,
    kernels: list[str],
    efi_size_mib: int = DEFAULT_EFI_MIB,
) -> dict[str, Any]:
    """Merge runtime system parameters and disk geometry into template config."""
    cfg = copy.deepcopy(template)
    cfg["hostname"] = hostname
    cfg["timezone"] = timezone
    cfg["kernels"] = kernels
    cfg.setdefault("locale_config", {})["kb_layout"] = keymap
    cfg["disk_config"] = build_disk_config(
        disk=disk,
        total_bytes=total_bytes,
        sector_size=sector_size,
        efi_size_mib=efi_size_mib,
    )
    return cfg


def build_credentials(username: str, user_password: str, root_password: str) -> dict[str, Any]:
    """Build archinstall 4.5 credentials JSON using yescrypt hashes when archinstall is importable."""
    try:
        from archinstall.lib.crypt import crypt_yescrypt

        return {
            "root_enc_password": crypt_yescrypt(root_password),
            "users": [
                {
                    "username": username,
                    "enc_password": crypt_yescrypt(user_password),
                    "sudo": True,
                    "groups": [],
                }
            ],
        }
    except ImportError:
        return {
            "!root-password": root_password,
            "!users": [
                {
                    "username": username,
                    "!password": user_password,
                    "sudo": True,
                    "groups": [],
                }
            ],
        }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", type=Path, default=script_dir / "user_configuration.template.json")
    parser.add_argument("--output", type=Path, default=script_dir / "user_configuration.json")
    parser.add_argument("--creds-output", type=Path, default=None)
    parser.add_argument("--disk", type=Path, required=True, help="Target disk path, e.g. /dev/nvme0n1")
    parser.add_argument("--disk-bytes", type=int, default=None, help="Override disk size in bytes (for testing)")
    parser.add_argument("--sector-size", type=int, default=None, help="Override logical sector size (512 or 4096)")
    parser.add_argument("--efi-mib", type=int, default=DEFAULT_EFI_MIB)
    parser.add_argument("--hostname", default="archlaptop")
    parser.add_argument("--timezone", default="Europe/Zurich")
    parser.add_argument("--keymap", default="de_CH-latin1")
    parser.add_argument("--kernels", nargs="+", default=["linux", "linux-zen"])
    parser.add_argument("--username", default="marc")
    parser.add_argument("--user-password-env", default="ARCH_USER_PASS")
    parser.add_argument("--root-password-env", default="ARCH_ROOT_PASS")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    template = json.loads(args.template.read_text(encoding="utf-8"))

    if args.disk_bytes is not None:
        total_bytes = args.disk_bytes
        sector_size = args.sector_size or 512
    else:
        total_bytes, detected_sector = query_disk_geometry(args.disk)
        sector_size = args.sector_size or detected_sector

    config = build_config(
        template=template,
        disk=args.disk,
        total_bytes=total_bytes,
        sector_size=sector_size,
        hostname=args.hostname,
        timezone=args.timezone,
        keymap=args.keymap,
        kernels=args.kernels,
        efi_size_mib=args.efi_mib,
    )
    args.output.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")

    if args.creds_output is not None:
        root_pw = os.environ.get(args.root_password_env, "")
        user_pw = os.environ.get(args.user_password_env, "")
        if not root_pw or not user_pw:
            raise ValueError(
                f"Both {args.root_password_env} and {args.user_password_env} env vars must be set when --creds-output is given"
            )
        creds = build_credentials(args.username, user_pw, root_pw)
        args.creds_output.write_text(json.dumps(creds, indent=2) + "\n", encoding="utf-8")
        args.creds_output.chmod(0o600)

    btrfs_bytes = config["disk_config"]["device_modifications"][0]["partitions"][1]["size"]["value"]
    print(
        f"Generated {args.output} for {args.disk} "
        f"(disk={total_bytes / (1024**3):.2f} GiB, sector={sector_size}B, "
        f"/efi={args.efi_mib} MiB, btrfs={btrfs_bytes / (1024**3):.2f} GiB)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
