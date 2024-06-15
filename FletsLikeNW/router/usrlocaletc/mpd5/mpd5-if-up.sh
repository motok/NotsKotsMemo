#!/bin/sh
#
# /usr/local/etc/mpd5/mpd-if-up.sh
#
# script interface proto local-ip remote-ip authname [ "dns1 server-ip" ] [ "dns2 server-ip" ] peer-address

iface=${1}
proto=${2}

case $# in
	8)	dns1=$(echo $6 | sed -e 's/dns1/nameserver/')
		dns2=$(echo $7 | sed -e 's/dns2/nameserver/')
		printf "%s\n%s\n" "${dns1}" "${dns2}" \
			| resolvconf -a ${iface}.${proto}

		;;
	7)	dns1=$(echo $6 | sed -e 's/dns1/nameserver:/')
		printf "%s\n" "${dns1}" \
			| resolvconf -a ${iface}.${proto}
		;;
	*)	;;
esac

