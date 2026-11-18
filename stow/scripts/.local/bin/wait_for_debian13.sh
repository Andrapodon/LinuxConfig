#!/bin/bash
while true; do
  VER_112=$(ssh -o BatchMode=yes -o StrictHostKeyChecking=no root@192.168.1.30 "pct exec 112 -- cat /etc/debian_version 2>/dev/null" || echo "")
  VER_222_JSON=$(ssh -o BatchMode=yes -o StrictHostKeyChecking=no root@192.168.1.30 "qm guest exec 222 -- cat /etc/debian_version 2>/dev/null" || echo "")
  
  if [[ "$VER_112" == 13.* && "$VER_222_JSON" == *"13."* ]]; then
     echo "Both upgraded to Debian 13!"
     break
  fi
  sleep 15
done
