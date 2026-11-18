#!/bin/bash
echo "Waiting for Proxmox host to reboot..."
while ssh -o BatchMode=yes -o StrictHostKeyChecking=no -o ConnectTimeout=3 root@192.168.1.30 "uptime | grep 'up 10 days'" >/dev/null 2>&1; do
    sleep 10
done

echo "Waiting for Proxmox host to come back online..."
while ! ssh -o BatchMode=yes -o StrictHostKeyChecking=no -o ConnectTimeout=3 root@192.168.1.30 "uptime" >/dev/null 2>&1; do
    sleep 10
done

echo "Host is back online! Waiting a few seconds for services to settle..."
sleep 20

echo "Applying AppArmor fix and starting VMs..."
ssh -o BatchMode=yes -o StrictHostKeyChecking=no root@192.168.1.30 "apt-get update && apt-get install -y apparmor && pct start 112; qm start 111; qm start 222"

echo "Waiting for LXC to initialize..."
sleep 15

echo "Executing OS upgrade inside LXC 112..."
ssh -o BatchMode=yes -o StrictHostKeyChecking=no root@192.168.1.30 "pct exec 112 -- bash -c \"sed -i 's/bookworm/trixie/g' /etc/apt/sources.list /etc/apt/sources.list.d/*.list 2>/dev/null || true; apt-get update && DEBIAN_FRONTEND=noninteractive apt-get dist-upgrade -y -o Dpkg::Options::='--force-confdef' -o Dpkg::Options::='--force-confold' && reboot\""

echo "LXC 112 upgrade complete!"
