

# ntpd packet logのための覚え書き(2)

## これは何？

- ntpdが送受信するパケットを記録したいと仮定する。
- ntpdのログ機構では、どうやらそこまで細かいログを取ることが出来ない。
- そこでちょっとソースを見てみる。
- 覚え書きなので**きっと**勘違いや誤りがあるに違いないです。先にごめんなさいしておきます。
- [ntpd packet logのための覚え書き(1)](https://ameblo.jp/ypsilondelta/entry-12632534671.html)ではmain()から順にパケットを受信する流れを追った。
  - [ntpd/ntp_proto.c](https://github.com/ntp-project/ntp/blob/9c75327c3796ff59ac648478cd4da8b205bceb77/ntpd/ntp_proto.c)で定義された[receive()](https://github.com/ntp-project/ntp/blob/9c75327c3796ff59ac648478cd4da8b205bceb77/ntpd/ntp_proto.c#L475)の[この辺り](https://github.com/ntp-project/ntp/blob/9c75327c3796ff59ac648478cd4da8b205bceb77/ntpd/ntp_proto.c#L532)で`pkt`に受信したパケットのメモリアドレスを保持して、`hisversion`, `hisleap`, `hismode`, `hisstratum`を読み出しており、
  - その後、`hismode`等を見ながらmode 7の処理を[ntpd/ntp_request.c](https://github.com/benegon/ntp/blob/e73fe484fe59fb52c489d7b1b41ee998be942f5e/ntpd/ntp_request.c)の[process_private()](https://github.com/benegon/ntp/blob/e73fe484fe59fb52c489d7b1b41ee998be942f5e/ntpd/ntp_request.c#L403)に渡し、mode 6の処理を[ntpd/ntp_control.c](https://github.com/benegon/ntp/blob/e73fe484fe59fb52c489d7b1b41ee998be942f5e/ntpd/ntp_control.c)の[process_control()](https://github.com/benegon/ntp/blob/e73fe484fe59fb52c489d7b1b41ee998be942f5e/ntpd/ntp_control.c#L670)に渡している。
  - mode 6, mode7以外のmodeはそのまま処理を続けて、結局[process_packet()](https://github.com/ntp-project/ntp/blob/9c75327c3796ff59ac648478cd4da8b205bceb77/ntpd/ntp_proto.c#L1795)を呼び出しているようだ。
- 次は[process_private()](https://github.com/benegon/ntp/blob/e73fe484fe59fb52c489d7b1b41ee998be942f5e/ntpd/ntp_request.c#L403)を見てみる。

## ntpd/ntp_request.c: process_private()

- 簡単のためにいくつかの[ポインタを初期化](https://github.com/benegon/ntp/blob/e73fe484fe59fb52c489d7b1b41ee998be942f5e/ntpd/ntp_request.c#L426)する。（って、コメントのまんまやな。）

```c
  recv_len = rbufp->recv_length;                     // 受信パケット長
	inpkt = (struct req_pkt *)&rbufp->recv_pkt;        // 受信パケット(の先頭アドレス)
	srcadr = &rbufp->recv_srcadr;                      // 送信側IPアドレス
	inter = rbufp->dstadr;                             // 受信側IPアドレス
```

- サニティチェックの後、[NTPプロトコルバージョンを取り出す](https://github.com/benegon/ntp/blob/e73fe484fe59fb52c489d7b1b41ee998be942f5e/ntpd/ntp_request.c#L462)。

```c
	reqver = INFO_VERSION(inpkt->rm_vn_mode);
```

- `inpkt`は`struct req_pkt`へのポインタで、[include/ntp_request.h](https://github.com/benegon/ntp/blob/e73fe484fe59fb52c489d7b1b41ee998be942f5e/include/ntp_request.h)で[struct req_pktを定義](https://github.com/benegon/ntp/blob/e73fe484fe59fb52c489d7b1b41ee998be942f5e/include/ntp_request.h#L125)している。

```c
struct req_pkt {
	u_char rm_vn_mode;		/* response, more, version, mode */
	u_char auth_seq;		/* key, sequence number */
	u_char implementation;		/* implementation number */
	u_char request;			/* request number */
	u_short err_nitems;		/* error code/number of data items */
	u_short mbz_itemsize;		/* item size */
	char data[MAXFILENAME + 48];	/* data area [32 prev](176 byte max) */
					/* struct conf_peer must fit */
	l_fp tstamp;			/* time stamp, for authentication */
	keyid_t keyid;			/* (optional) encryption key */
	char mac[MAX_MAC_LEN-sizeof(keyid_t)]; /* (optional) auth code */
};
```

- この[include/ntp_request.h](https://github.com/benegon/ntp/blob/e73fe484fe59fb52c489d7b1b41ee998be942f5e/include/ntp_request.h)ファイルの冒頭にはmode 7のパケットフォーマットの説明があるので必見。

- mode 7はRFCのようなNTPの仕様にはない実装独自の機能部分なので、まあ、そうね。

- [INFO_VERSIONマクロ](https://github.com/benegon/ntp/blob/e73fe484fe59fb52c489d7b1b41ee998be942f5e/include/ntp_request.h#L203)も[include/ntp_request.h](https://github.com/benegon/ntp/blob/e73fe484fe59fb52c489d7b1b41ee998be942f5e/include/ntp_request.h)で定義されていて、パケット先頭の１バイト(`rm_vn_mode`)からバージョン部分の３ビットを取り出している。

- 続いて`inpkt->implementation`を調べて[`proc`に適切な関数リストを設定](https://github.com/benegon/ntp/blob/e73fe484fe59fb52c489d7b1b41ee998be942f5e/ntpd/ntp_request.c#L465)する。

  ```c
  	/*
  	 * Get the appropriate procedure list to search.
  	 */
  	if (inpkt->implementation == IMPL_UNIV)
  		proc = univ_codes;
  	else if ((inpkt->implementation == IMPL_XNTPD) ||
  		 (inpkt->implementation == IMPL_XNTPD_OLD))
  		proc = ntp_codes;
  	else {
  		req_ack(srcadr, inter, inpkt, INFO_ERR_IMPL);
  		return;
  	}
  ```

- `IMPL_UNIV`, `IMPLE_XNTPD`, `IMPL_XNTPD_OLD`は[ここ](https://github.com/benegon/ntp/blob/e73fe484fe59fb52c489d7b1b41ee998be942f5e/include/ntp_request.h#L227)で定義されていて、順に「"universal"な用法」「IPv6以後のntpdcが使う」「IPv6以前のntpdcが使う」とのこと。

  - universalが何を意味するのか、はよくわからない。何に対して「一般」？（→後述）
  - XNTPDのXは、[version 3までのntpdがxntpdと呼ばれていて、version 4になる時にntpdと改めた](http://x68000.q-e-d.net/~68user/unix/pickup?xntpd)名残らしい。両方あるのは知っていたが、そういう違いであったとは知らなかった。

  ```c
  #define	IMPL_UNIV	0
  #define	IMPL_XNTPD_OLD	2	/* Used by pre ipv6 ntpdc */
  #define	IMPL_XNTPD	3	/* Used by post ipv6 ntpdc */
  ```

- [`proc`は`struct req_proc *`型](https://github.com/benegon/ntp/blob/e73fe484fe59fb52c489d7b1b41ee998be942f5e/ntpd/ntp_request.c#L417)でその定義は[こちら](https://github.com/benegon/ntp/blob/e73fe484fe59fb52c489d7b1b41ee998be942f5e/ntpd/ntp_request.c#L48)。その要素である`void (*handler)`に`univ_codes`か`ntp_codes`を代入していることになる。

  ```c
  struct req_proc {
  	short request_code;	/* defined request code */
  	short needs_auth;	/* true when authentication needed */
  	short sizeofitem;	/* size of request data item (older size)*/
  	short v6_sizeofitem;	/* size of request data item (new size)*/
  	void (*handler) (sockaddr_u *, struct interface *,
  			   struct req_pkt *);	/* routine to handle request */
  };
  ```

- まず[`univ_codes`](https://github.com/benegon/ntp/blob/e73fe484fe59fb52c489d7b1b41ee998be942f5e/ntpd/ntp_request.c#L60)は`NO_REQUEST`しかないので多分使うことはないのだろう。RFCでmode 7を定義した場合にここに追記すればよいというつもりで作ったけどまだ使われていない、に一票。

  ```c
  static	struct req_proc univ_codes[] = {
  	{ NO_REQUEST,		NOAUTH,	 0,	0 }
  };
  ```

- `struct req_proc`と`univ_codes`の４つ並びが対応していて、構造体を埋めるわけだ。

  ```c
  request_code  = NO_REQUEST
  needs_auth    = NOAUTH
  sizeofitem    = 0
  v6_sizeofitem = 0
  ```

- この`NO_REQUEST`は[ここ](https://github.com/benegon/ntp/blob/e73fe484fe59fb52c489d7b1b41ee998be942f5e/ntpd/ntp_request.c#L38)で定義されていて、値は`-1`。ついでに`NOAUTH`, `AUTH`もその直前で定義されている。

- ```c
  /*
   * Structure to hold request procedure information
   */
  #define	NOAUTH	0
  #define	AUTH	1
  
  #define	NO_REQUEST	(-1)
  ```

- 次に[`ntp_codes`](https://github.com/benegon/ntp/blob/e73fe484fe59fb52c489d7b1b41ee998be942f5e/ntpd/ntp_request.c#L122)は`REQ_PEER_LIST`に始まって`REQ_MON_GETLIST`など`ntpdc`で見たようなものがたくさん並んでいる。これが("universal"ではなくて)`ntpd`が独自に実装したmode 7のコマンド群ということだろう。`NO_REQUEST`を除いて他は５つ並びになっていて呼び出すべきハンドラ関数の値(`req_proc->handler`)も設定されている点に注意。

  ```c
  static	struct req_proc ntp_codes[] = {
  	{ REQ_PEER_LIST,	NOAUTH,	0, 0,	peer_list },
  	{ REQ_PEER_LIST_SUM,	NOAUTH,	0, 0,	peer_list_sum },
  	{ REQ_PEER_INFO,    NOAUTH, v4sizeof(struct info_peer_list),
  				sizeof(struct info_peer_list), peer_info},
  	{ REQ_PEER_STATS,   NOAUTH, v4sizeof(struct info_peer_list),
  				sizeof(struct info_peer_list), peer_stats},
  	{ REQ_SYS_INFO,		NOAUTH,	0, 0,	sys_info },
  	{ REQ_SYS_STATS,	NOAUTH,	0, 0,	sys_stats },
  	{ REQ_IO_STATS,		NOAUTH,	0, 0,	io_stats },
  	{ REQ_MEM_STATS,	NOAUTH,	0, 0,	mem_stats },
        (後略)
  ```

- この`REQ_PEER_LIST`等は[ここから](https://github.com/benegon/ntp/blob/e73fe484fe59fb52c489d7b1b41ee998be942f5e/include/ntp_request.h#L245)定義されている。

  ```c
  /*
   * NTPD request codes go here.
   */
  #define	REQ_PEER_LIST		0	/* return list of peers */
  #define	REQ_PEER_LIST_SUM	1	/* return summary info for all peers */
  #define	REQ_PEER_INFO		2	/* get standard information on peer */
      (後略)
  ```

- 戻って、`proc`に代入された`univ_codes`なり`ntp_codes`なりの`request_code`のリストの中に、受信パケットの`inpkt->request`に[該当するものがあるかどうかを調べる](https://github.com/benegon/ntp/blob/e73fe484fe59fb52c489d7b1b41ee998be942f5e/ntpd/ntp_request.c#L478)。なければ`req_ack()`でINFO_ERR_REQを返してエラーリターン(準正常系)か。(`req_ack()`の中は後で見る)

- この後しばらく返すべきデータがあるかその他のサニティチェックが続いた後、いよいよ問題なく応答できるとなれば[`proc->handler`](https://github.com/benegon/ntp/blob/e73fe484fe59fb52c489d7b1b41ee998be942f5e/ntpd/ntp_request.c#L652)を呼び出して`process_private()`が完了する。

  ```c
  	DPRINTF(3, ("process_private: all okay, into handler\n"));
  	/*
  	 * Packet is okay.  Call the handler to send him data.
  	 */
  	(proc->handler)(srcadr, inter, inpkt);
  }    // process_private()の終わり
  ```

- 例えば`input->request`が`REQ_PEER_LIST`であれば`proc->handler`には`peer_list`関数が入っているので、`peer_list(srcadr, inter, inpkt)`という呼び出しを行うことになる。

- `input->request`で指示される全部の関数を追うことはできない（やれ、という声が大きかったら考えますが）ので、次節で一例として`REQ_PEER_LIST`の場合を追うことにする。

## ntpd/ntp_request.c: peer_list()

### peer_list()の処理(1)

- 今、我々はmode 6の`peer_list()`の処理を辿ろうとしているわけだが、これは`ntpq -p`に相当する処理であるはず。（man ntpqに"ntpq uses NTP mode 6 packets..."とあり、また-pは"print a list of the peers ..."とある。ついでにmode 7はntpdcの役割らしい。）

  ```shell
  $ ntpq -p
       remote           refid      st t when poll reach   delay   offset  jitter
  ==============================================================================
   0.freebsd.pool. .POOL.          16 p    -   64    0    0.000   +0.000   0.000
   ntp.nict.jp     .POOL.          16 p    -   64    0    0.000   +0.000   0.000
   ntp.jst.mfeed.a .POOL.          16 p    -   64    0    0.000   +0.000   0.000
   LOCAL(0)        .LOCL.          10 l   7d   64    0    0.000   +0.000   0.000
  +ntp-a2.nict.go. .NICT.           1 u  597 1024  377    3.963   -0.987   6.311
  +ntp-b2.nict.go. .NICT.           1 u  361 1024  377    3.055   -1.214   2.107
  +ntp-b3.nict.go. .NICT.           1 u  990 1024  377    5.171   -0.349   5.288
  +ntp-k1.nict.jp  .nict.           1 u  250 1024  377   22.296   -6.392   4.372
  *ntp-a3.nict.go. .NICT.           1 u  727 1024  377    4.108   -0.686   3.839
  ```

- `peer_list()`は[ntp_request.cのこの辺](https://github.com/benegon/ntp/blob/e73fe484fe59fb52c489d7b1b41ee998be942f5e/ntpd/ntp_request.c#L657)から定義されていて、ソースアドレス・インタフェイス・受信パケットを引数に取り、`prepare_pkt()`・`more_pkt()`・`flush_pkt()`を呼び出して`struct info_peer_list *ip`の先の返送用パケットを組み立てる。

- `struct info_peer_list型`は[include/ntp_request.hのこの辺](https://github.com/benegon/ntp/blob/e73fe484fe59fb52c489d7b1b41ee998be942f5e/include/ntp_request.h#L326)で定義。

  ```c
  /*
   * Peer list structure.  Used to return raw lists of peers.  It goes
   * without saying that everything returned is in network byte order.
   * Well, it *would* have gone without saying, but somebody said it.
   */
  struct info_peer_list {
  	u_int32 addr;		/* address of peer */
  	u_short port;		/* port number of peer */
  	u_char hmode;		/* mode for this peer */
  	u_char flags;		/* flags (from above) */
  	u_int v6_flag;		/* is this v6 or not */
  	u_int unused1;		/* (unused) padding for addr6 */
  	struct in6_addr addr6;	/* v6 address of peer */
  };
  ```

- というわけで[peer_list()では最初にprepare_pkt()を呼んで](https://github.com/benegon/ntp/blob/e73fe484fe59fb52c489d7b1b41ee998be942f5e/ntpd/ntp_request.c#L671)`struct info_peer_list *型`のポインタ`ip`を初期化する。

  ```c
  	ip = (struct info_peer_list *)prepare_pkt(srcadr, inter, inpkt,
  	    v6sizeof(struct info_peer_list));
  ```

- `prepare_pkt()`での処理については次項。

### ntpd/ntp_request.c: prepare_pkt()

- `prepare_pkt()`は[ntp_request.cの上の方](https://github.com/benegon/ntp/blob/e73fe484fe59fb52c489d7b1b41ee998be942f5e/ntpd/ntp_request.c#L274)で定義されている。

- 送信(返信)用の応答パケットを準備してそのパケットの中の**データ格納領域へのポインタ**を返す、とコメントにある。パケット先頭へのポインタではないところに注意。

- 処理を追うと突然出てくる`rpkt`は[さらに上の方](https://github.com/benegon/ntp/blob/e73fe484fe59fb52c489d7b1b41ee998be942f5e/ntpd/ntp_request.c#L215)で定義されている。要は大域変数。

  ```c
  static struct resp_pkt rpkt;
  ```

- この`struct resp_pkt`型の定義は[ntp/include/ntp_request.hの中](https://github.com/benegon/ntp/blob/e73fe484fe59fb52c489d7b1b41ee998be942f5e/include/ntp_request.h#L168)にある。これが応答パケットの型ということであろう。

  ```c
  #define	RESP_HEADER_SIZE	(offsetof(struct resp_pkt, data))
  #define	RESP_DATA_SIZE		(500)
  
  struct resp_pkt {
  	u_char rm_vn_mode;		/* response, more, version, mode */
  	u_char auth_seq;		/* key, sequence number */
  	u_char implementation;		/* implementation number */
  	u_char request;			/* request number */
  	u_short err_nitems;		/* error code/number of data items */
  	u_short mbz_itemsize;		/* item size */
  	char data[RESP_DATA_SIZE];	/* data area */
  };
  ```

- `prepare_pkt()`は短いので全部引用しておく。

  ```c
  static char *
  prepare_pkt(
  	sockaddr_u *srcadr,
  	struct interface *inter,
  	struct req_pkt *pkt,
  	size_t structsize
  	)
  {
  	DPRINTF(4, ("request: preparing pkt\n"));
  
  	/*
  	 * Fill in the implementation, request and itemsize fields
  	 * since these won't change.
  	 */
  	rpkt.implementation = pkt->implementation;
  	rpkt.request = pkt->request;
  	rpkt.mbz_itemsize = MBZ_ITEMSIZE(structsize);
  
  	/*
  	 * Compute the static data needed to carry on.
  	 */
  	toaddr = srcadr;
  	frominter = inter;
  	seqno = 0;
  	nitems = 0;
  	itemsize = structsize;
  	databytes = 0;
  	usingexbuf = 0;
  
  	/*
  	 * return the beginning of the packet buffer.
  	 */
  	return &rpkt.data[0];
  }
  ```

- `prepare_pkt()`では、ソースアドレス・インタフェイス・受信パケットを元にして返送パケットを組み立てている。あまり判断とかいらなくて単にあのフィールドをこのフィールドへコピーすればよいとか初期値を入れればオーケーみたいなやつだけれども。

  - 返信パケットのrpkt.implementationには受信パケットからpkt->implementationをコピー。
  - toaddrにはsrcaddrをコピー等。

- `prepare_pkt()`の返り値として`return &rpkt.data[0];`を返しているので、`struct resp_pkt`のデータ部分(`rpkt.data[]`)の先頭アドレスを返す、ということになる。。逆にいうとその手前までがヘッダ部分。

### peer_list()の処理(2)

- `prepare_pkt()`から`peer_list()`へ戻ると、for文・while文を回してpeer情報を転記する処理を行う。

  - 外側のfor文は`peer_hash[]`を一通り回って調べるもの。内側の`while`は一つの`pp = peer_hash[i]`について調べるもの。
  - 二重ループになっているのは`peer_hash[]`が配列の配列になっているのか、他の理由があるのか。これは将来課題にしておきます。すみません。

- いずれにしてもこれは、[`peer_hash[i]`を`pp`に受けておいて、`&pp->srcadr`を`ip->addr`に転記するような処理](https://github.com/benegon/ntp/blob/e73fe484fe59fb52c489d7b1b41ee998be942f5e/ntpd/ntp_request.c#L673)である。

  ```c
  	for (i = 0; i < NTP_HASH_SIZE && ip != 0; i++) {
  		pp = peer_hash[i];
  		while (pp != 0 && ip != 0) {
  			if (IS_IPV6(&pp->srcadr)) {
  				if (client_v6_capable) {
  					ip->addr6 = SOCK_ADDR6(&pp->srcadr);
   					ip->v6_flag = 1;
  					skip = 0;
  				} else {
  					skip = 1;
  					break;
  				}
  			} else {
  				ip->addr = NSRCADR(&pp->srcadr);
  				if (client_v6_capable)
  					ip->v6_flag = 0;
  				skip = 0;
  			} // else clause
      :
    }  // for loop
  ```

- 二行目、peer_hashは大域変数でpeerの情報が格納されているらしい。これは[ntp/ntpd/ntp_peer.cの初めの方](https://github.com/benegon/ntp/blob/e73fe484fe59fb52c489d7b1b41ee998be942f5e/ntpd/ntp_peer.c#L82)で宣言されている。

  ```c
  struct peer *peer_hash[NTP_HASH_SIZE];	/* peer hash table */
  ```

- この`struct peer型`は[ntp/include/ntp.h](https://github.com/benegon/ntp/blob/e73fe484fe59fb52c489d7b1b41ee998be942f5e/include/ntp.h#L252)で定義されている。長いので冒頭だけ引用するが、たしかに`srcadr`なる要素が存在することがわかる。

  ```c
  /*
   * The peer structure. Holds state information relating to the guys
   * we are peering with. Most of this stuff is from section 3.2 of the
   * spec.
   */
  struct peer {
  	struct peer *next;	/* link pointer in peer hash */
  	struct peer *ass_next;	/* link pointer in associd hash */
  	struct peer *ilink;	/* list of peers for interface */
  	sockaddr_u srcadr;	/* address of remote host */
  	endpt *	dstadr;		/* local address */
  	associd_t associd;	/* association ID */
  	u_char	version;	/* version number */
  	u_char	hmode;		/* local association mode */
  	u_char	hpoll;		/* local poll interval */
  	u_char	minpoll;	/* min poll interval */
  	u_char	maxpoll;	/* max poll interval */
  	u_int	flags;		/* association flags */
  	u_char	cast_flags;	/* additional flags */
  	u_char	last_event;	/* last peer error code */
  	u_char	num_events;	/* number of error events */
  	u_char	ttl;		/* ttl/refclock mode */
        :
  ```

- `peer_list()`に戻って上に引用した[転記処理whileの前半部分](https://github.com/benegon/ntp/blob/e73fe484fe59fb52c489d7b1b41ee998be942f5e/ntpd/ntp_request.c#L673)では、`peer_hash[]`側の`srcadr`すなわちピアのリモート側のアドレスを転記している。

- IPv4/IPv6の別があるのでそれを識別して、`ip`側でいう`ip->addr`/`ip->addr6`に格納すると共に識別フラグ`ip->v6_flag`を`1/0`にしている。

- IPv6側の処理ではさらに、`client_v6_capable`を検査してIPv6通信が可能であれば`srcadr`を転記するが、未対応であれば`skip=1`とフラグを立てて次の`pp`へ処理を移す（ということだと思うけれど、client_v6_capableについては追えていない）。

- IPv4でもIPv6でも、`srcadr`の転記ができていれば`skip=0`とフラグを倒しているので、`while`ループの後半の処理へ向かう。

  ```c
  		while (pp != 0 && ip != 0) {
          :
        if(!skip) {
  				ip->port = NSRCPORT(&pp->srcadr);
  				ip->hmode = pp->hmode;
  				ip->flags = 0;
  				if (pp->flags & FLAG_CONFIG)
  				    ip->flags |= INFO_FLAG_CONFIG;
  				if (pp == sys_peer)
  				    ip->flags |= INFO_FLAG_SYSPEER;
  				if (pp->status == CTL_PST_SEL_SYNCCAND)
  				    ip->flags |= INFO_FLAG_SEL_CANDIDATE;
  				if (pp->status >= CTL_PST_SEL_SYSPEER)
  				    ip->flags |= INFO_FLAG_SHORTLIST;
  				ip = (struct info_peer_list *)more_pkt();
  			}  // if(!skip)
  			pp = pp->next; 
  		}  // while
  ```

- ここでは、ポート番号(`ip->port`)やリモート側のモード(`ip->hmode`)などが`peer_list[]`側から転記され、さらに各種のフラグも転記されている。

- そして、`more_pkt()`を呼び出して返り値を`ip`に代入している。`more_pkt()`の中の処理については次項で。

- ここまで終わると、`pp=pp->next`で次のピアへのポインタに更新してもう一度`while`ループを回る。

### ntp/ntpd/ntp-request.c: more_pkt()

- `more_pkt()`は、[`ntp/ntpd/ntp-request.c`のこの辺](https://github.com/benegon/ntp/blob/e73fe484fe59fb52c489d7b1b41ee998be942f5e/ntpd/ntp_request.c#L314)で定義されている。

- [最初の`if`ブロック](https://github.com/benegon/ntp/blob/e73fe484fe59fb52c489d7b1b41ee998be942f5e/ntpd/ntp_request.c#L322)は、extra bufferを使っている場合に返信パケットを送出するべく`sendpkt()`を呼び出す。このとき、`rm_vm_mode`等いくつかのフィールドを埋めている。

  ```c
  static char *
  more_pkt(void)
  {
  	/*
  	 * If we were using the extra buffer, send the packet.
  	 */
  	if (usingexbuf) {
  		DPRINTF(3, ("request: sending pkt\n"));
  		rpkt.rm_vn_mode = RM_VN_MODE(RESP_BIT, MORE_BIT, reqver);
  		rpkt.auth_seq = AUTH_SEQ(0, seqno);
  		rpkt.err_nitems = htons((u_short)nitems);
  		sendpkt(toaddr, frominter, -1, (struct pkt *)&rpkt,
  			RESP_HEADER_SIZE + databytes);
  		numresppkts++;
  
   		/*
  		 * Copy data out of exbuf into the packet.
  		 */
  		memcpy(&rpkt.data[0], exbuf, (unsigned)itemsize);
  		seqno++;
  		databytes = 0;
  		nitems = 0;
  		usingexbuf = 0;
  	}
  ```

- [第二の`if`ブロック](https://github.com/benegon/ntp/blob/e73fe484fe59fb52c489d7b1b41ee998be942f5e/ntpd/ntp_request.c#L343)の前半は、返信パケットのデータ領域にまだ余裕があるのでもっとデータを転記するべく、その書き込み先となるアドレスを返す。[後半](https://github.com/benegon/ntp/blob/e73fe484fe59fb52c489d7b1b41ee998be942f5e/ntpd/ntp_request.c#L350)では、もはや余裕がないときにデータ領域がぴったり埋まっていればNULLを返し、はみ出す場合にはextra bufferのアドレスを返す。NULLが返れば、`peer_list()`の`while`文中でipがNULLになってループが終わる。

  ```c
  	databytes += itemsize;
  	nitems++;
  	if (databytes + itemsize <= RESP_DATA_SIZE) {
  		DPRINTF(4, ("request: giving him more data\n"));
  		/*
  		 * More room in packet.  Give him the
  		 * next address.
  		 */
  		return &rpkt.data[databytes];
  	} else {
  		/*
  		 * No room in packet.  Give him the extra
  		 * buffer unless this was the last in the sequence.
  		 */
  		DPRINTF(4, ("request: into extra buffer\n"));
  		if (seqno == MAXSEQ)
  			return NULL;
  		else {
  			usingexbuf = 1;
  			return exbuf;
  		}
  	}
  ```

- To Do: extra bufferを表す変数`exbuf`の宣言箇所、型などを調べよ。

### peer_list()の処理(3)

- `for`/`while`の二重ループを抜けると、`flush_pkt()`を呼び出して`peer_list()`の処理は終わる。

### ntp/ntpd/ntp_request.c: flush_pkt()

- [`flush_pkt()`はntp/ntpd/ntp_request.cのこの辺](https://github.com/benegon/ntp/blob/e73fe484fe59fb52c489d7b1b41ee998be942f5e/ntpd/ntp_request.c#L370)に定義されている。

  ```c
  static void
  flush_pkt(void)
  {
  	DPRINTF(3, ("request: flushing packet, %d items\n", nitems));
  	/*
  	 * Must send the last packet.  If nothing in here and nothing
  	 * has been sent, send an error saying no data to be found.
  	 */
  	if (seqno == 0 && nitems == 0)
  		req_ack(toaddr, frominter, (struct req_pkt *)&rpkt,
  			INFO_ERR_NODATA);
  	else {
  		rpkt.rm_vn_mode = RM_VN_MODE(RESP_BIT, 0, reqver);
  		rpkt.auth_seq = AUTH_SEQ(0, seqno);
  		rpkt.err_nitems = htons((u_short)nitems);
  		sendpkt(toaddr, frominter, -1, (struct pkt *)&rpkt,
  			RESP_HEADER_SIZE+databytes);
  		numresppkts++;
  	}
  }
  ```

- `if`文の前半部では、コメントにある通り、送るべきパケットがなく(`seqno==0`)、かつ、まだ何も送っていない(`ntimes==0`)場合には`req_ack()`を`INFO_ERR_NODATA`付きで呼び出してエラー応答をしているようだ。

- 後半部では返信パケット(`rpkt`)の`rm_vn_mode`などのフィールドを埋めたあと`sendpkt()`を呼び出して返信パケットを送出している。

### ntp/ntpd/ntp_io.c: sendpkt()

- ここで、返信パケットの送出に使われる`sendpkt()`は[ntpd/ntp_io.cのこの辺](https://github.com/benegon/ntp/blob/e73fe484fe59fb52c489d7b1b41ee998be942f5e/ntpd/ntp_io.c#L3129)に定義されていて、内部で`sendto()`を呼んでパケットを送出している。

  ```c
  void
  sendpkt(
  	sockaddr_u *		dest,
  	struct interface *	ep,
  	int			ttl,
  	struct pkt *		pkt,
  	int			len
  	)
  {
        :
    		cc = sendto(src->fd, (char *)pkt, (u_int)len, 0,
  			    &dest->sa, SOCKLEN(dest));
  ```

- 返信パケットの記録を取るなら、このsendtoの直前あたりが良さそうである。

