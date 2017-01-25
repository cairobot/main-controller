#!/bin/bash



# author:   redxef
# file:     gpio.sh
# version:  0.0.1
# since:    16-10-25
# desc:     An easy to handle shell script for interacting with the GPIO pins.



GPIO_DIR=/sys/class/gpio

# 1 ... the port
getGPIONr() {
        case "$1" in
                GPIO0)
                        echo 192
                ;;
                GPIO1)
                        echo 193
                ;;
                GPIO2)
                        echo 194
                ;;
                GPIO3)
                        echo 195
                ;;
                GPIO4)
                        echo 196
                ;;
                GPIO5)
                        echo 209
                ;;
                GPIO6)
                        echo 210
                ;;
                GPIO7)
                        echo 197
                ;;
        esac
}

# 1 ... the port
isInit() {
        local p="$1"
        if [ -d "$GPIO_DIR/gpio$(getGPIONr "$p")" ]; then
                echo 'true'
        else
                echo 'false'
        fi
}

# 1 ... the port (GPIO0..7)
initPin() {
        local p="$1"
        if [ "$(isInit "$p")" = 'false' ]; then
                echo "$(getGPIONr "$p")" > "$GPIO_DIR/export"
        else
                echo "already inited" >&2
        fi
}

# 1 ... the port (GPIO0..7)
# 2 ... dir
setDir() {
        local p="$1"
        local d="$2"
        if [ "$(isInit "$p")" = 'true' ]; then
                echo "$d" > "$GPIO_DIR/gpio$(getGPIONr "$p")/direction"
        else
                echo "not inited" >&2
        fi
}

# 1 ... the port
getDir() {
        local p="$1"
        if [ "$(isInit "$p")" = 'true' ]; then
                cat "$GPIO_DIR/gpio$(getGPIONr "$p")/direction"
        else
                echo "not inited" >&2
        fi
}

# 1 ... the port
# 2 ... the value 0 or 1
setValue() {
        local p="$1"
        local v="$2"
        if [ "$(isInit "$p")" = 'true' ]; then
                if [ "$(getDir "$p")" = "out" ]; then
                        echo "$v" > "$GPIO_DIR/gpio$(getGPIONr "$p")/value"
                fi
        else
                echo "not inited" >&2
        fi
}

# 1 ... the port
# returns the value
getValue() {
        local p="$1"
        local v="$2"
        if [ "$(isInit "$p")" = 'true' ]; then
                cat "$GPIO_DIR/gpio$(getGPIONr "$p")/value"
        else
                echo "not inited" >&2
        fi
}

"$@"
