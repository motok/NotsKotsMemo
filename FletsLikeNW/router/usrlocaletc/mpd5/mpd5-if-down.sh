#!/bin/sh
#
# /usr/local/etc/mpd5/mpd-if-down.sh
#
# script interface proto local-ip remote-ip authname peer-address

iface=${1}
proto=${2}

resolvconf -d ${iface}.${proto}

