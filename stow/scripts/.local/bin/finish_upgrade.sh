#!/bin/bash
echo "Waiting for Proxmox host to come back online..."
while ! ssh -o BatchMode=yes -o StrictHostKeyChecking=no -o ConnectTimeout=3 root@192.168.1.30 "uptime" >/dev/null 2>&1; do
    sleep 5
done

echo "Host is online! Wait 30 seconds for services..."
sleep 30

echo "Installing apparmor and starting guests..."
ssh -o BatchMode=yes -o StrictHostKeyChecking=no root@192.168.1.30 "apt-get update && apt-get install -y apparmor && pct start 112; qm start 111; qm start 222"

echo "Waiting for LXC 112 to initialize..."
sleep 20

echo "Upgrading LXC..."
ssh -o BatchMode=yes -o StrictHostKeyChecking=no root@192.168.1.30 "pct exec 112 -- bash -c \"sed -i 's/bookworm/trixie/g' /etc/apt/sources.list /etc/apt/sources.list.d/*.list 2>/dev/null || true; apt-get update && DEBIAN_FRONTEND=noninteractive apt-get dist-upgrade -y -o Dpkg::Options::='--force-confdef' -o Dpkg::Options::='--force-confold' && reboot\""

echo "ALL DONE!"
