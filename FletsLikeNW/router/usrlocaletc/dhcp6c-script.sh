#!/bin/sh
#
# /usr/local/etc/dhcp6c-script.sh
#

#new_ntp_servers
#new_domain_name
#new_domain_name_servers
#REASON=INFOREQ

print_resolvconf() {
	if [ "${new_domain_name}" ]
	then
		echo "search: ${new_domain_name}"
	fi

	if [ "${new_domain_name_servers}" ]
	then
		for i in ${new_domain_name_servers}
		do
			echo "nameserver ${i}"
		done
	fi
}

print_ntpconf() {
	if [ "${new_ntp_servers}" ]
	then
		echo "tos minclock 3 maxclock 6"
		#echo "pool 0.freebsd.pool.ntp.org iburst"
		#echo "pool 2.freebsd.pool.ntp.org iburst"
		#echo "pool ntp.nict.jp iburst"

		for i in ${new_ntp_servers}
		do
			echo "server $i iburst"
		done

		echo "server 127.127.1.0"
		echo "fudge 127.127.1.0 stratum 10"
		echo "restrict default limited kod nomodify notrap noquery nopeer"
		echo "restrict source  limited kod nomodify notrap noquery"
		echo "restrict 127.0.0.1"
		echo "restrict ::1"
		echo "leapfile \"/var/db/ntpd.leap-seconds.list\""

	fi
}

print_rtadvdconf() {
	echo "default: \\"

	if [ "${new_domain_name}" ]
	then
		echo "	:dnssl=\"$(echo -n ${new_domain_name})\": \\"
	fi

	if [ "${new_domain_name_servers}" ]
	then
		echo "	:rdnss=\"$(echo -n ${new_domain_name_servers})\": \\"
	fi

	echo ""

	for i in vtnet1 vtnet2
	do
		echo "${i}: \\"
		echo "	:tc=default:"
		echo ""
	done
}

configure_gif() {
	#REMOTE_END=$(host -t aaaa gw.transix.jp | head -1 | cut -d' ' -f5)
	REMOTE_END="2001:db8:cafe::2a0:98ff:fe29:5561" # fake gw.transit.jp
	LOCAL_END=$(ifconfig vtnet0 | grep inet6 | grep autoconf | cut -d' ' -f2)
	ifconfig gif0 > /dev/null 2>&1 || ifconfig gif0 create
	ifconfig gif0 inet6 tunnel ${LOCAL_END} ${REMOTE_END}
	ifconfig gif0 inet 192.168.99.2 192.168.99.1
	route add -inet default -iface gif0
}

case "${REASON}" in
	"INFOREQ") ;;
	"REQUEST" | "RENEW" | "REBIND")
		print_resolvconf | /sbin/resolvconf -a vtnet0.dhcp6c

		print_ntpconf > /etc/ntp-dhcp6c.conf
		service ntpd restart

		print_rtadvdconf > /etc/rtadvd-dhcp6c.conf
		#service rtadvd restart
		rtadvctl reload

		configure_gif
		;;
	"RELEASE" | "EXIT")
		/sbin/resolvconf -d vtnet0
		#ifconfig gif0 destroy
		;;
	*) ;;
esac
