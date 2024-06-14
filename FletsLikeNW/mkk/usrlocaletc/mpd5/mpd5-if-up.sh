#!/bin/sh
#
# /usr/local/etc/mpd5/mpd-if-up.sh
#
# script interface proto local-ip remote-ip authname [ "dns1 server-ip" ] [ "dns
2 server-ip" ] peer-address

iface=${1}
proto=${2}

# should add route to segment beyond pppoe link.
