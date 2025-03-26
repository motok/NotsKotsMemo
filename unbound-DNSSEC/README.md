# 今更ながらunboundでDNSSECを検証できるようにする

[[TOC]]


## これは何？

これまで必要を感じなくてずっとサボっていたDNSSEC検証をやってみようと思
い腰をあげたところ、ちょっと小細工も必要だったのでメモに残す。

環境はFreeBSD 14.2 amd64とpkgで入れたunbound 1.22.0。

## unbound


unboundのDNSSEC対応については、本家NLNetLabsに
[Howto enable DNSSEC](https://nlnetlabs.nl/documentation/unbound/howto-anchor/)
というページがあって、ここに全部書いてある。
以下は、その抄録。

ドメイン名のルート`.`の鍵を取得しておく必要があるとのこと
で、/usr/local/etc/unbound/root.keyを作成する。

初回は`unbound-anchor`コマンドをunboundユーザで実行すればよいが、
FreeBSDの場合はunboundのrcスクリプト内でやってくれるので
`service unbound start`を実行すれば良い。

次に、unboundデーモンがroot.keyを認識するように、設定ファイルに追記す
る。


``` yaml
# /usr/local/etc/unbound/unbound.conf

server:
    auto-trust-anchor-file: "/usr/local/etc/unbound/root.key"
```

これで、unboundを再起動`service unbound restart`すれば出来上がり。

## drill

FreeBSDの場合は名前解決用のコマンドとして、`dig`の代わりに`drill`を使
うので、そのための小細工が必要になる。

その１、`drill`がroot.keyファイルを探す時、デフォルトでは
/var/unbound/root.keyを見に行く。
コマンドラインで`drill -k /usr/local/etc/unbound/root.key ...`
とすれば問題はないが、毎回これをやるのは面倒なので、デフォルトの位置に
インボリックリンクでroot.keyを置いておく方が良いだろう。

``` shell
# cd /var/unbound
# ln -s ../../usr/local/etc/unbound/root.key .
```

その２、`drill`はデフォルトではDNSSEC検証を行わない(?)ようなので、
`alias drill="drill -D"`を~/.bashrcかどこかに設定しておくと良いだろう。

## テスト

上記の本家ドキュメントにある試験を行うことで、DNSSECを検証できるかどう
かを試す。

``` shell
$ drill -DT -t SOA com.
;; Number of trusted keys: 2
;; Domain: .
[T] . 172800 IN DNSKEY 257 3 8 ;{id = 20326 (ksk), size = 2048b}
. 172800 IN DNSKEY 256 3 8 ;{id = 26470 (zsk), size = 2048b}
. 172800 IN DNSKEY 257 3 8 ;{id = 38696 (ksk), size = 2048b}
. 172800 IN DNSKEY 256 3 8 ;{id = 53148 (zsk), size = 2048b}
Checking if signing key is trusted:
New key: .	172800	IN	DNSKEY	256 3 8 AwEAAZ5A7jOztf62cGqhPhutjnyl7KBjIsjbyTb8il+FsgbMUbO2NQHaSbatHdlOlqANncDwSIKZ9ryqd1+Dy1PoGzeTUv95vOJnVVJHlJu7xdavnUmPs+Mh2NV7hDlTTwPn5uXgFxAaxoO9M/YIAC92GryCLjoJEg9JzeevkktEM/sFpmRv4I5jQtlLyRqVbnCzcWpi04XaVLxRKvURkd/Mdb/2RQS3MYvrkEBXuqtnAVBCf6Fx4sgBYOfYvbUuG2diLnGJW/MXvFpctZgQ76+3FwMqAZfR9k5bohL7AF3+jqz4MUiootYoh5koyt7VEnUULxxy6U5PINTGgOC26f3zZuk= ;{id = 26470 (zsk), size = 2048b}
	Trusted key: .	86400	IN	DNSKEY	257 3 8 AwEAAaz/tAm8yTn4Mfeh5eyI96WSVexTBAvkMgJzkKTOiW1vkIbzxeF3+/4RgWOq7HrxRixHlFlExOLAJr5emLvN7SWXgnLh4+B5xQlNVz8Og8kvArMtNROxVQuCaSnIDdD5LKyWbRd2n9WGe2R8PzgCmr3EgVLrjyBxWezF0jLHwVN8efS3rCj/EWgvIWgb9tarpVUDK/b58Da+sqqls3eNbuv7pr+eoZG+SrDK6nWeL3c6H5Apxz7LjVc1uTIdsIXxuOLYA4/ilBmSVIzuDWfdRUfhHdY6+cn8HFRm+2hM8AnXGXws9555KrUB5qihylGa8subX2Nn6UwNR1AkUTV74bU= ;{id = 20326 (ksk), size = 2048b}
        : (中略)
[T] com. 86400 IN DS 19718 13 2 8acbb0cd28f41250a80a491389424d341522d946b0da0c0291f2d3d771d7805a 
;; Domain: com.
[T] com. 86400 IN DNSKEY 257 3 13 ;{id = 19718 (ksk), size = 256b}
com. 86400 IN DNSKEY 256 3 13 ;{id = 23202 (zsk), size = 256b}
[T] com.	900	IN	SOA	a.gtld-servers.net. nstld.verisign-grs.com. 1742969527 1800 900 604800 900
;;[S] self sig OK; [B] bogus; [T] trusted; [U] unsigned
```

各行の先頭が[T]となっていればtrustedということらしい。

他にも、internet.nlで同様の試験をやればIPv6経由での検証ができているか
どうかがわかるとか、rootcanary.orgを試験すればすべてのDNSSECアルゴリズ
ムに対する試験ができるとか。
