

# ntpd packet logのための覚え書き(1)

## これは何？

- ntpdが送受信するパケットを記録したいと仮定する。
- ntpdのログ機構では、どうやらそこまで細かいログを取ることが出来ない。
- そこでちょっとソースを見てみる。
- 覚え書きなので**きっと**勘違いや誤りがあるに違いないです。先にごめんなさいしておきます。
- 追記、受信側だけで長くなったので送信側は稿を改めます。

## NTPd

- まず、[ntpd本家](https://www.ntp.org/)と[githubリポジトリ](https://github.com/ntp-project/ntp/)はこちら。
- RFCだと[Wikipdia記事](https://ja.wikipedia.org/wiki/Network_Time_Protocol)の出典を参考にしつつ、この辺を見るべきなのかしら。基本が5905で認証が7822で追加されている感じだと思うが、全部読んでいるわけではないし、ましてや全部理解しているわけではないです、はい、すみません。
  - [RFC5905: Network Time Protocol Version 4: Protocol and Algorithms Specification](https://tools.ietf.org/html/rfc5905)
  - [RFC5905 7.3 Packet Header Variables](https://tools.ietf.org/html/rfc5905#section-7.3)にNTPプロトコルのパケットフォーマットあり。
  - [RFC7822: Network Time Protocol Version 4 (NTPv4) Extension Fields](https://tools.ietf.org/html/rfc7822)
- [FreeBSD 12.1-RELEASE](https://www.freebsd.org)では、[/usr/src/usr.sbin/ntp](https://svnweb.freebsd.org/base/release/12.1.0/usr.sbin/ntp/)(実態はほぼ[/usr/src/contrib/ntp](https://svnweb.freebsd.org/base/release/12.1.0/contrib/ntp/)側にある)としてntp.orgのntpdを同梱している。
- NTPの他の実装としては次のふたつが有名処か。
  - [OpenNTPD](http://www.openntpd.org)
  - [Chrony](https://chrony.tuxfamily.org)


## ntpdがパケットを受信する流れ

- [ntpd/ntpd.c](https://github.com/ntp-project/ntp/blob/master-no-authorname/ntpd/ntpd.c)の[main()](https://github.com/ntp-project/ntp/blob/9c75327c3796ff59ac648478cd4da8b205bceb77/ntpd/ntpd.c#L355)はこの辺。

- `main()`ではコマンドライン引数をparseした後、[ntpdmain()を呼び出す](https://github.com/ntp-project/ntp/blob/9c75327c3796ff59ac648478cd4da8b205bceb77/ntpd/ntpd.c#L510)。

  ```c
  #ifdef NO_MAIN_ALLOWED
  CALL(ntpd,"ntpd",ntpdmain);
  #else	/* !NO_MAIN_ALLOWED follows */
  #ifndef SYS_WINNT
  int
  main(
  	int argc,
  	char *argv[]
  	)
  {
  	return ntpdmain(argc, argv);
  }
  #endif /* !SYS_WINNT */
  #endif /* !NO_MAIN_ALLOWED */
  ```

- `ntpdmain()`ではいろいろと初期設定をした後に他にやることがなくなると(?)、[io_handler()を呼び出す](https://github.com/ntp-project/ntp/blob/9c75327c3796ff59ac648478cd4da8b205bceb77/ntpd/ntpd.c#L1257)。

  ```c
  		if (!was_alarmed && !has_full_recv_buffer()) {
  			/*
  			 * Nothing to do.  Wait for something.
  			 */
  			io_handler();
  		}
  ```

- `io_handler()`は[ntpd/ntp_io.c](https://github.com/ntp-project/ntp/blob/master-no-authorname/ntpd/ntp_io.c)にあって[この辺から](https://github.com/ntp-project/ntp/blob/9c75327c3796ff59ac648478cd4da8b205bceb77/ntpd/ntp_io.c#L3493)始まり、[input_handler_scan()を呼び出す](https://github.com/ntp-project/ntp/blob/9c75327c3796ff59ac648478cd4da8b205bceb77/ntpd/ntp_io.c#L3550)。

  ```c
  	if (nfound > 0) {
  		l_fp ts;
  
  		get_systime(&ts);
  
  		input_handler_scan(&ts, &rdfdes);
  	} else if (nfound == -1 && errno != EINTR) {
  		msyslog(LOG_ERR, "select() error: %m");
  	}
  # 
  ```

- シグナルハンドラから呼ばれる[input_handler()](https://github.com/ntp-project/ntp/blob/9c75327c3796ff59ac648478cd4da8b205bceb77/ntpd/ntp_io.c#L3566)もあるが、結局`input_handler_scan()`を呼んでいる。

  ```c
      }
      if (n > 0)
  		    input_handler_scan(cts, &fds);
  }
  ```

- [input_handler_scan()](https://github.com/ntp-project/ntp/blob/9c75327c3796ff59ac648478cd4da8b205bceb77/ntpd/ntp_io.c#L3649)はこの辺から。

- `input_handler_scan()`では、まず[read_refclock_packet()](https://github.com/ntp-project/ntp/blob/9c75327c3796ff59ac648478cd4da8b205bceb77/ntpd/ntp_io.c#L3168)を呼び出して[Reference Clockをチェック](https://github.com/ntp-project/ntp/blob/9c75327c3796ff59ac648478cd4da8b205bceb77/ntpd/ntp_io.c#L3685)する。これがrefclockすなわち精密な時刻情報を提供する装置(通常ローカルにある)とのやり取りを担当するのであろう。

  ```c
  #ifdef REFCLOCK
  	/*
  	 * Check out the reference clocks first, if any
  	 */
  	
  	for (rp = refio; rp != NULL; rp = rp->next) {
  		fd = rp->fd;
  		
  		if (!FD_ISSET(fd, pfds))
  			continue;
  		buflen = read_refclock_packet(fd, rp, ts);
  ```

- 次いで`input_handler_scan()`は[read_network_packet()](https://github.com/ntp-project/ntp/blob/9c75327c3796ff59ac648478cd4da8b205bceb77/ntpd/ntp_io.c#L3358)を呼び出して[Network packetをチェックする](https://github.com/ntp-project/ntp/blob/9c75327c3796ff59ac648478cd4da8b205bceb77/ntpd/ntp_io.c#L3722)。こちらはおそらくNTPサーバとの間やその他の通信を担当するのであろう。

  ```c
  if (FD_ISSET(fd, pfds))
  do {
  					buflen = read_network_packet(
  							fd, ep, ts);
  				} while (buflen > 0);
  ```

- `read_network_packet()`では、`struct recvbuf *rb`にメモリ領域を確保して`recvfrom`ないし`recvmsg`からのデータを記録する。

  ```c
  #ifndef HAVE_PACKET_TIMESTAMP
  	rb->recv_length = recvfrom(fd, (char *)&rb->recv_space,
  				   sizeof(rb->recv_space), 0,
  				   &rb->recv_srcadr.sa, &fromlen);
  #else
  	iovec.iov_base        = &rb->recv_space;
  	iovec.iov_len         = sizeof(rb->recv_space);
  	msghdr.msg_name       = &rb->recv_srcadr;
  	msghdr.msg_namelen    = fromlen;
  	msghdr.msg_iov        = &iovec;
  	msghdr.msg_iovlen     = 1;
  	msghdr.msg_control    = (void *)&control;
  	msghdr.msg_controllen = sizeof(control);
  	msghdr.msg_flags      = 0;
  	rb->recv_length       = recvmsg(fd, &msghdr, 0);
  #endif
  ```

- さらに`add_full_recv_buffer()`を呼び出して[受信したデータを受信バッファに追加する](https://github.com/ntp-project/ntp/blob/9c75327c3796ff59ac648478cd4da8b205bceb77/ntpd/ntp_io.c#L3486)。この時、`rb->receiver`に`receive`を設定している点に注意。この要素はコールバック関数で、`receive`は`ntpd/ntp_proto.c`で定義された関数である（後述）。

  ```c
  	rb->recv_time = ts;
  	rb->receiver = receive;
  
  	add_full_recv_buffer(rb);
  
  	itf->received++;
  	packets_received++;
  	return (buflen);
  }
  ```

- [add_full_recv_buffer()](https://github.com/ntp-project/ntp/blob/9c75327c3796ff59ac648478cd4da8b205bceb77/libntp/recvbuff.c#L174)は[libntp/recvbuff.c](https://github.com/ntp-project/ntp/blob/master-no-authorname/libntp/recvbuff.c)にあって、渡されたバッファ`rb`を`full_recv_fifo`変数に追加する。

  ```c
  void
  add_full_recv_buffer(recvbuf_t *rb)
  {
  	if (rb == NULL) {
  		msyslog(LOG_ERR, "add_full_recv_buffer received NULL buffer");
  		return;
  	}
  	LOCK();
  	LINK_FIFO(full_recv_fifo, rb, link);
  	full_recvbufs++;
  	UNLOCK();
  }
  ```

- 受信バッファ`recvbuf`については[libntp/recvbuff.c](https://github.com/ntp-project/ntp/blob/master-no-authorname/libntp/recvbuff.c)に一通りの定義があるようだが、受信バッファを`add_full_recv_buffer()`で追加し、`get_full_recv_buffer()`で取り出すという動作であるようだ。

- `recvbuf_t`型こと`struct recvbuf`型は[include/recvbuff.hで定義されている](https://github.com/ntp-project/ntp/blob/9c75327c3796ff59ac648478cd4da8b205bceb77/include/recvbuff.h#L47)。要素にコールバック関数`void (*receiver)(struct recvbuf *)`がある点に注意。

  ```c
  typedef struct recvbuf recvbuf_t;
  
  struct recvbuf {
  	recvbuf_t *	link;	/* next in list */
  	union {
  		sockaddr_u	X_recv_srcadr;
  		caddr_t		X_recv_srcclock;
  		struct peer *	X_recv_peer;
  	} X_from_where;
  #define recv_srcadr		X_from_where.X_recv_srcadr
  #define	recv_srcclock		X_from_where.X_recv_srcclock
  #define recv_peer		X_from_where.X_recv_peer
  #ifndef HAVE_IO_COMPLETION_PORT
  	sockaddr_u	srcadr;		/* where packet came from */
  #else
  	int		recv_srcadr_len;/* filled in on completion */
  #endif
  	endpt *		dstadr;		/* address pkt arrived on */
  	SOCKET		fd;		/* fd on which it was received */
  	int		msg_flags;	/* Flags received about the packet */
  	l_fp		recv_time;	/* time of arrival */
  	void		(*receiver)(struct recvbuf *); /* callback */
  	int		recv_length;	/* number of octets received */
  	union {
  		struct pkt	X_recv_pkt;
  		u_char		X_recv_buffer[RX_BUFF_SIZE];
  	} recv_space;
  #define	recv_pkt		recv_space.X_recv_pkt
  #define	recv_buffer		recv_space.X_recv_buffer
  	int used;		/* reference count */
  };
  ```

- [get_full_recv_buffer()](https://github.com/ntp-project/ntp/blob/9c75327c3796ff59ac648478cd4da8b205bceb77/libntp/recvbuff.c#L225)は`full_recv_fifo`変数から受信バッファをひとつ取り出して返り値として返す。

  ```c
  recvbuf_t *
  get_full_recv_buffer(void)
  {
  	recvbuf_t *	rbuf;
  
  	LOCK();
  	
  #ifdef HAVE_SIGNALED_IO
  	/*
  	 * make sure there are free buffers when we
  	 * wander off to do lengthy packet processing with
  	 * any buffer we grab from the full list.
  	 * 
  	 * fixes malloc() interrupted by SIGIO risk
  	 * (Bug 889)
  	 */
  	if (NULL == free_recv_list || buffer_shortfall > 0) {
  		/*
  		 * try to get us some more buffers
  		 */
  		create_buffers(RECV_INC);
  	}
  #endif
  
  	/*
  	 * try to grab a full buffer
  	 */
  	UNLINK_FIFO(rbuf, full_recv_fifo, link);
  	if (rbuf != NULL)
  		full_recvbufs--;
  	UNLOCK();
  
  	return rbuf;
  }
  ```

- この`get_full_recv_buffer()`を呼び出すのは`ntpdmain()`の中の[この辺](https://github.com/ntp-project/ntp/blob/9c75327c3796ff59ac648478cd4da8b205bceb77/ntpd/ntpd.c#L1287)である。`rbuf->receiver`が`NULL`でない時に`(*rbuf->receiver)(rbuf);`でコールバック関数を呼び出している点に注意。

  ```c
  			rbuf = get_full_recv_buffer();
  			while (rbuf != NULL) {
  				if (alarm_flag) {
  					was_alarmed = TRUE;
  					alarm_flag = FALSE;
  				}
  				UNBLOCK_IO_AND_ALARM();
  
  				if (was_alarmed) {
  					/* avoid timer starvation during lengthy I/O handling */
  					timer();
  					was_alarmed = FALSE;
  				}
  
  				/*
  				 * Call the data procedure to handle each received
  				 * packet.
  				 */
  				if (rbuf->receiver != NULL) {
  # ifdef DEBUG_TIMING
  					l_fp dts = pts;
  
  					L_SUB(&dts, &rbuf->recv_time);
  					DPRINTF(2, ("processing timestamp delta %s (with prec. fuzz)\n", lfptoa(&dts, 9)));
  					collect_timing(rbuf, "buffer processing delay", 1, &dts);
  					bufcount++;
  # endif
  					(*rbuf->receiver)(rbuf);
  				} else {
  					msyslog(LOG_ERR, "fatal: receive buffer callback NULL");
  					abort();
  				}
  
  				BLOCK_IO_AND_ALARM();
  				freerecvbuf(rbuf);
  				rbuf = get_full_recv_buffer();
  			}
  ```

- `(*rbuf->receiver)(rbuf);`でコールバック関数を呼び出すということは、`add_full_recv_buffer()`でコールバックに設定した`receive()`を呼ぶということである。この関数は[ntpd/ntp_proto.c](https://github.com/ntp-project/ntp/blob/9c75327c3796ff59ac648478cd4da8b205bceb77/ntpd/ntp_proto.c)で定義された[receive()](https://github.com/ntp-project/ntp/blob/9c75327c3796ff59ac648478cd4da8b205bceb77/ntpd/ntp_proto.c#L475)であると思われる。

- [receive()](https://github.com/ntp-project/ntp/blob/9c75327c3796ff59ac648478cd4da8b205bceb77/ntpd/ntp_proto.c#L475)でパケットのフィールドを分別し始めるのは[この辺り](https://github.com/ntp-project/ntp/blob/9c75327c3796ff59ac648478cd4da8b205bceb77/ntpd/ntp_proto.c#L532)から。`pkt`に受信したパケットのメモリアドレスを保持して、`hisversion`, `hisleap`, `hismode`, `hisstratum`を読み出している。余談だが、これも`his`はダメで三人称単数の`their`にしろとかいうよくわからない話になるのであろうか。

  ```c
    register struct pkt *pkt;
          :
    pkt = &rbufp->recv_pkt;
    DPRINTF(2, ("receive: at %ld %s<-%s flags %x restrict %03x org %#010x.%08x xmt %#010x.%08x\n",
  		    current_time, stoa(&rbufp->dstadr->sin),
          stoa(&rbufp->recv_srcadr), rbufp->dstadr->flags,
  		    restrict_mask, ntohl(pkt->org.l_ui), ntohl(pkt->org.l_uf),
          ntohl(pkt->xmt.l_ui), ntohl(pkt->xmt.l_uf)));
  	hisversion = PKT_VERSION(pkt->li_vn_mode);
  	hisleap = PKT_LEAP(pkt->li_vn_mode);
  	hismode = (int)PKT_MODE(pkt->li_vn_mode);
  	hisstratum = PKT_TO_STRATUM(pkt->stratum);
  ```

- ところで、この`struct pkt`は[include/ntp.h](https://github.com/ntp-project/ntp/blob/9c75327c3796ff59ac648478cd4da8b205bceb77/include/ntp.h)の[この辺り](https://github.com/ntp-project/ntp/blob/9c75327c3796ff59ac648478cd4da8b205bceb77/include/ntp.h#L535)で定義されている。上で使われている`li_vn_mode`や`stratum`のような要素があることがわかる。

  ```c
  /*
   * NTP packet format.  The mac field is optional.  It isn't really
   * an l_fp either, but for now declaring it that way is convenient.
   * See Appendix A in the specification.
   *
   * Note that all u_fp and l_fp values arrive in network byte order
   * and must be converted (except the mac, which isn't, really).
   */
  struct pkt {
  	u_char	li_vn_mode;	/* peer leap indicator */
  	u_char	stratum;	/* peer stratum */
  	u_char	ppoll;		/* peer poll interval */
  	s_char	precision;	/* peer clock precision */
  	u_fp	rootdelay;	/* roundtrip delay to primary source */
  	u_fp	rootdisp;	/* dispersion to primary source*/
  	u_int32	refid;		/* reference id */
  	l_fp	reftime;	/* last update time */
  	l_fp	org;		/* originate time stamp */
  	l_fp	rec;		/* receive time stamp */
  	l_fp	xmt;		/* transmit time stamp */
  
  #define	LEN_PKT_NOMAC	(12 * sizeof(u_int32)) /* min header length */
  #define MIN_MAC_LEN	(1 * sizeof(u_int32))	/* crypto_NAK */
  #define MAX_MD5_LEN	(5 * sizeof(u_int32))	/* MD5 */
  #define	MAX_MAC_LEN	(6 * sizeof(u_int32))	/* SHA */
  
  	/*
  	 * The length of the packet less MAC must be a multiple of 64
  	 * with an RSA modulus and Diffie-Hellman prime of 256 octets
  	 * and maximum host name of 128 octets, the maximum autokey
  	 * command is 152 octets and maximum autokey response is 460
  	 * octets. A packet can contain no more than one command and one
  	 * response, so the maximum total extension field length is 864
  	 * octets. But, to handle humungus certificates, the bank must
  	 * be broke.
  	 *
  	 * The different definitions of the 'exten' field are here for
  	 * the benefit of applications that want to send a packet from
  	 * an auto variable in the stack - not using the AUTOKEY version
  	 * saves 2KB of stack space. The receive buffer should ALWAYS be
  	 * big enough to hold a full extended packet if the extension
  	 * fields have to be parsed or skipped.
  	 */
  #ifdef AUTOKEY
  	u_int32	exten[(NTP_MAXEXTEN + MAX_MAC_LEN) / sizeof(u_int32)];
  #else	/* !AUTOKEY follows */
  	u_int32	exten[(MAX_MAC_LEN) / sizeof(u_int32)];
  #endif	/* !AUTOKEY */
  };
  ```

- さて、[receive()](https://github.com/ntp-project/ntp/blob/9c75327c3796ff59ac648478cd4da8b205bceb77/ntpd/ntp_proto.c#L475)に戻って、`hisversion`から`hisstratum`までを取り出した後、`restrict_mask`が`RES_IGNORE`だったら (正確にはそのビットが立っていたら)[単純に無視する](https://github.com/ntp-project/ntp/blob/9c75327c3796ff59ac648478cd4da8b205bceb77/ntpd/ntp_proto.c#L542)。この`restrict_mask`は少し戻ったところで受信パケットの[ソースアドレスから計算されている](https://github.com/ntp-project/ntp/blob/9c75327c3796ff59ac648478cd4da8b205bceb77/ntpd/ntp_proto.c#L531)。

  ```c
  	restrict_mask = restrictions(&rbufp->recv_srcadr);
  	pkt = &rbufp->recv_pkt;
  	DPRINTF(2, ("receive: at %ld %s<-%s flags %x restrict %03x org %#010x.%08x xmt %#010x.%08x\n",
  		    current_time, stoa(&rbufp->dstadr->sin),
  		    stoa(&rbufp->recv_srcadr), rbufp->dstadr->flags,
  		    restrict_mask, ntohl(pkt->org.l_ui), ntohl(pkt->org.l_uf),
  		    ntohl(pkt->xmt.l_ui), ntohl(pkt->xmt.l_uf)));
  	hisversion = PKT_VERSION(pkt->li_vn_mode);
  	hisleap = PKT_LEAP(pkt->li_vn_mode);
  	hismode = (int)PKT_MODE(pkt->li_vn_mode);
  	hisstratum = PKT_TO_STRATUM(pkt->stratum);
  	if (restrict_mask & RES_IGNORE) {
  		sys_restricted++;
  		return;				/* ignore everything */
  	}
  ```

- 続いて`hismode`等を見ながらmode 7の処理を[ntpd/ntp_request.c](https://github.com/benegon/ntp/blob/e73fe484fe59fb52c489d7b1b41ee998be942f5e/ntpd/ntp_request.c)の[process_private()](https://github.com/benegon/ntp/blob/e73fe484fe59fb52c489d7b1b41ee998be942f5e/ntpd/ntp_request.c#L403)に渡し、mode 6の処理を[ntpd/ntp_control.c](https://github.com/benegon/ntp/blob/e73fe484fe59fb52c489d7b1b41ee998be942f5e/ntpd/ntp_control.c)の[process_control()](https://github.com/benegon/ntp/blob/e73fe484fe59fb52c489d7b1b41ee998be942f5e/ntpd/ntp_control.c#L670)に渡している。mode 6,7のパケットフォーマットを知るにはこれら関数(とその先)を見れば良いようだ。

- Mode6, 7以外のパケットについては、そのまま分岐せずに認証周りやpeerの処理などをした後に[この辺](https://github.com/ntp-project/ntp/blob/9c75327c3796ff59ac648478cd4da8b205bceb77/ntpd/ntp_proto.c#L1765)で[process_packet()](https://github.com/ntp-project/ntp/blob/9c75327c3796ff59ac648478cd4da8b205bceb77/ntpd/ntp_proto.c#L1795)に渡して処理しているようだ。

- というわけで、ntpdが受け取るパケットのログを取るなら[この辺り](https://github.com/ntp-project/ntp/blob/9c75327c3796ff59ac648478cd4da8b205bceb77/ntpd/ntp_proto.c#L532)の`hisversion`その他を取り出した直後が良いであろう。ここなら各種制約に掛かって捨てられるパケットも見える位置である。
