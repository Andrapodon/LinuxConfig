#!/bin/bash
CONF="/etc/trackpoint-scroller.conf"

get_speed() {
    if [ -f "$CONF" ]; then
        cat "$CONF" | tr -d ' \n'
    else
        echo "5"
    fi
}

set_speed() {
    local val="$1"
    if [ "$val" -lt 1 ]; then val=1; fi
    if [ "$val" -gt 10 ]; then val=10; fi
    echo "$val" > "$CONF"
    pkill -RTMIN+9 waybar 2>/dev/null
}

case "$1" in
    get)
        speed=$(get_speed)
        echo "{\"text\": \"$speed\", \"tooltip\": \"TrackPoint Scroll Speed: $speed/10\n• Scroll up/down to adjust\n• Click for slider\", \"class\": \"speed-$speed\"}"
        ;;
    up)
        speed=$(get_speed)
        set_speed $((speed + 1))
        ;;
    down)
        speed=$(get_speed)
        set_speed $((speed - 1))
        ;;
    slider)
        speed=$(get_speed)
        new_speed=$(zenity --scale \
            --title="TrackPoint Scroll Speed" \
            --text="Adjust scroll speed (1 = slow, 10 = fast):" \
            --min-value=1 \
            --max-value=10 \
            --value="$speed" \
            --step=1 2>/dev/null)
        if [ -n "$new_speed" ]; then
            set_speed "$new_speed"
        fi
        ;;
    *)
        get_speed
        ;;
esac
