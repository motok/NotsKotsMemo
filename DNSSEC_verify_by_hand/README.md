# DNSSEC verification by hand


- [RFC 9364 DNS Security Extensions (DNSSEC)](https://tex2e.github.io/rfc-translater/html/rfc9364.html)
  - DNSSEC関連のRFCのガイドマップみたいなRFC。
  - RFC 9364自体は他のRFCを更新しない。

- [手を動かしてDNSSECの検証をやってみよう](https://eng-blog.iij.ad.jp/archives/7689)

IIJさんの記事に従って、`eng-blog.iij.ad.jp`のAレコードを検証してみる。
関連するRRとしては、A, RRSIG, DNSKEYがあるので、一通り取得しておく。

``` shell
$ dig -t A eng-blog.iij.ad.jp +short
202.232.2.203

$ dig -t RRSIG eng-blog.iij.ad.jp +short
# RRSIG-A
A 8 4 300 20250506151005 20250406151005 31668 iij.ad.jp. ymqOC9wWY8IgYMHXBYB3o6RJ1v7n2bUMq7LiIysVvjbIcfmFm0yT+5uV XEBTKJGTMS3hwKufrTdD4QcJVqgtlfvOkl9l2Vpd2mGk43yRRc0DQkOe 211wxwP7DlUOlj6xTdlcqRCwgHEhKWK+vld1S4nQkbLm/CImQNDRMG2p mHw=
# RRSIG-B
AAAA 8 4 300 20250506151005 20250406151005 31668 iij.ad.jp. BuacmI1zH/Xz2ur8vSinD9RwSVSQdPbovjlLZieYLk6miMo9HMsOsD63 5yvbHMZbb0Fic5LOWGc9mnAFFsL1U7rL/eeAyMofXh1z7q4fRy95R5ne tD+1k97wU9T8uycl9OQyuGjVnvSH8WZgFtKWiKoXPMiB3t/7M37BRIPF 83o=

$ dig -t DNSKEY eng-blog.iij.ad.jp +short
(DNSKEY RRなし)

$ dig -t DNSKEY iij.ad.jp +short
# DNSKEY-1
256 3 8 AwEAAayQtSx/pvXV+AoGFJeNPv5vnZf6BATFUrx/ys5j9BQ3emE3sab4 Hro/zW1n/pEmfDG/AlC/mFg9t0vrFimiLM8GsymNoIXpw0PbaTbi0jhD 4eDUGZ2OpjtWMyCUYJPMfjx3pAisWg5zSYWuKQiv8TFbfy7yoWY6RzlV dbma9kop
# DNSKEY-2
256 3 8 AwEAAdC5VKJuA30xxtw4DE2t5ihxGKzc3o527l1na+uUh/KkKLvqmYdT +t7kBKP1SVnO6Mz9w7wqqpiV5VwKdb0CWyA0N7rlBnWWhRCkIzVp/iuu ZB+fO4EcBKrUckWf6Kx/a7HXxRFrkF0Bi0E3dy8pMBbRukQpNOXFqlkc RR/G6qO9
# DNSKEY-3
257 3 8 AwEAAahXWyIn8JmvtyrzvlNNYFvACfOS/LZoOpUzF3HpFje8ySj6z4d7 5p4P4VSIelgRFXDtjYpeqc8uUxIo6lg6Y69gyH+QK9UPS5/GdDlxpl2F jp7LifaeWPpMAYtr8frwjImY0sDeeWfYqgwZZD722aSEArM5Wpjft5F+ UzbPAnTYBnri29UA6YVCg4ZFRrGBYAUWKJfngPKMNRjLUyr9LeqgQp95 nal86y4LQjEJNbSXlP6GA0OOZ0JuyIZLJ8NPPqM8HD13DFDOc5He5pn/ N7PfCB5WGvYx58ZEvxpqWf0+V2a2XE6c1Ffomil/fQNiAu5JFTgumHY1 OXS5oLdRiuM=
```

A RRが信頼できるかどうかを知るためには、対応するRRSIGにある各データが正しいかどうかを調べる必要がある。

A RRを検証しようとしているので、対応するRRSIGは上で取得したうちのRRSIG-Aの方である。
(RRSIG-BはAAAA RRを検証するためのもの)

このRRSIG-Aのフィールドは以下のように読める。

| フィールド     | 値                | 意味                                            |
-----------------|-------------------|-------------------------------------------------|
| 署名対象タイプ | A                 | (eng-blog.iij.ad.jpの) A RR に対する署名である  |
| アルゴリズム   | 8                 | DNSKEYアルゴリズム8番はRSASHA256(RFC8624)       |
| ラベル数       | 4                 | (eng-blog.iij.ad.jpの)ラベルの数。              |
| オリジナルTTL  | 300               | 権威サーバで付与されたTTL(リゾルバなどが書き換えることがあるのでここに書いておく？) |
| 有効期間終了   | 20250505151004    | いつまで有効な署名であるか                      |
| 有効期間開始   | 20250405151004    | いつから有効な署名であるか                      |
| 鍵タグ         | 31668             | DNSKEY RRのRDATA部分のチェックサム。計算方法はRFC4034で独自に定義。このRRSIGに対応するDNSKEYを探す手掛かりとなる。 |
| 署名者名       | iij.ad.jp.        | 対応するDNSKEY RRの所有者                       |
| 署名           | FZZeDLZhGl7Cd.... | RRSIG RDATA(ただし署名フィールドを除く)を対象とした署名。アルゴリズムに応じて計算方法が変わる。 |

- 署名対象タイプはA RRだと言っているので正しい。
- アルゴリズムは8はRSASHA256ということで理解できる。
- ラベル数は4で正しい。
- 有効期間も現時点を含んでいるので正しい。
- 署名者もeng-blog.iij.ad.jpを署名するのはiij.ad.jpで正しい。

鍵タグについては、
- RRSIGに対応するDNSKEYを探すためのチェックサムである。
- DNSKEYが複数ある場合に、チェックサムが一致するものがあればそれが「対応する」。
  - チェックサムが衝突する場合もあって、その場合には対応すると思われるDNSKEYを全部試せとのこと。
  - (ひとつでも最後まで検証できたものがあればオッケーってこと？？？)
- チェックサムの計算方法はC言語のものがRFC 4034に掲載されている。
- それをPythonで実装したものがIIJさんのブログにあったので、それを借りてきて
  少し改変したものが [./keytag.py](./keytag.py) 。

これを使ってDNSKEYのRDATAのチェックサムを計算すると、
``` shell
$ dig -t DNSKEY iij.ad.jp +short | while read line; do echo $line; ./keytag.py $line; echo ""; done
# DNSKEY-1
256 3 8 AwEAAayQtSx/pvXV+AoGFJeNPv5vnZf6BATFUrx/ys5j9BQ3emE3sab4 Hro/zW1n/pEmfDG/AlC/mFg9t0vrFimiLM8GsymNoIXpw0PbaTbi0jhD 4eDUGZ2OpjtWMyCUYJPMfjx3pAisWg5zSYWuKQiv8TFbfy7yoWY6RzlV dbma9kop
47508

# DNSKEY-2
256 3 8 AwEAAdC5VKJuA30xxtw4DE2t5ihxGKzc3o527l1na+uUh/KkKLvqmYdT +t7kBKP1SVnO6Mz9w7wqqpiV5VwKdb0CWyA0N7rlBnWWhRCkIzVp/iuu ZB+fO4EcBKrUckWf6Kx/a7HXxRFrkF0Bi0E3dy8pMBbRukQpNOXFqlkc RR/G6qO9
31668

# DNSKEY-3
257 3 8 AwEAAahXWyIn8JmvtyrzvlNNYFvACfOS/LZoOpUzF3HpFje8ySj6z4d7 5p4P4VSIelgRFXDtjYpeqc8uUxIo6lg6Y69gyH+QK9UPS5/GdDlxpl2F jp7LifaeWPpMAYtr8frwjImY0sDeeWfYqgwZZD722aSEArM5Wpjft5F+ UzbPAnTYBnri29UA6YVCg4ZFRrGBYAUWKJfngPKMNRjLUyr9LeqgQp95 nal86y4LQjEJNbSXlP6GA0OOZ0JuyIZLJ8NPPqM8HD13DFDOc5He5pn/ N7PfCB5WGvYx58ZEvxpqWf0+V2a2XE6c1Ffomil/fQNiAu5JFTgumHY1 OXS5oLdRiuM=
18490
```
ということで、鍵タグから見てDNSKEY-2が対応するDNSKEY RRであるらしいことがわかる。

このDNSKEY-2は以下のように読める。

| フィールド     | 値                | 意味                                            |
-----------------|-------------------|-------------------------------------------------|
| フラグ         | 256               | |
| プロトコル     | 3                 | |
| アルゴリズム   | 8                 | |
| 公開鍵         | AwEAAdC5VKJuA3... | |

- 256(10)は 0000 0001 0000 0000 (2)で、署名鍵ビット(ビット7)が立っているので、これは署名鍵(KSKまたはZSK)である。
- セキュアエントリポイント(SEP)ビット(ビット15)は立っていないので、これはZSKである。
- プロトコルは3に固定されているので、これで良い。
- アルゴリズム8番は、RRSIGと同様にRSASHA256を指す。
- 公開鍵の部分は、RSASHA256の公開鍵をBASE64で符号化したもの。



続いて、DNSKEY-2のRDATAの公開鍵部分からRSASHA256で使うRSA公開鍵(指数expとモジュラスmodulus)を取り出す。

- 先頭1バイトが0x03なので、これが指数長でその値は3。(先頭1バイトが0x00だと続く2バイトが指数長)
- 従って、2,3,4バイト目の0x01 0x00 0x01が指数ということになる。
  すなわち、指数は、0x010001 = 65537(10)である。
- そして引き続く5バイト目から末尾までがモジュラスである。長さも1024 bit (128 Byte)でそれっぽいね。

``` shell
$ ./dnskey_pubkey.py 'AwEAAdC5VKJuA30xxtw4DE2t5ihxGKzc3o527l1na+uUh/KkKLvqmYdT +t7kBKP1SVnO6Mz9w7wqqpiV5VwKdb0CWyA0N7rlBnWWhRCkIzVp/iuu ZB+fO4EcBKrUckWf6Kx/a7HXxRFrkF0Bi0E3dy8pMBbRukQpNOXFqlkc RR/G6qO9' 
exp_len:     3 byte
exp:        65537 (10)
modulus_len: 128 byte
modulus:    146570940549784169560470017999114332147060637684277267914353988087770100550436284153018603966728195899715841350828674502930709645679912533263178982518867204828975579005111729953303455565104878375457027758339889765627365260603987810534482349585612830776590313168338334627378223244460959284522812712332521284541 (10)
```

DNSKEYから指数とモジュラスがわかったので、これを使ってRRSIGの署名部分を復号する。

- RRSIG RDATAの署名部分はBASE64で符号化されているので、まず復号する。
- それをネットワークバイトオーダで整数化する。
- 出てきた整数をDNSKEYから得た指数乗し、DNSKEYから得たモジュラスで剰余を取る。
- これでRRSIGの署名部分の復号ができた、はずなんだけど、16進数表記で先頭に0x1FFF...FFが付くやついず何？

``` shell
$ ./rrsig_decrypt.py 'AwEAAdC5VKJuA30xxtw4DE2t5ihxGKzc3o527l1na+uUh/KkKLvqmYdT +t7kBKP1SVnO6Mz9w7wqqpiV5VwKdb0CWyA0N7rlBnWWhRCkIzVp/iuu ZB+fO4EcBKrUckWf6Kx/a7HXxRFrkF0Bi0E3dy8pMBbRukQpNOXFqlkc RR/G6qO9' 'ymqOC9wWY8IgYMHXBYB3o6RJ1v7n2bUMq7LiIysVvjbIcfmFm0yT+5uV XEBTKJGTMS3hwKufrTdD4QcJVqgtlfvOkl9l2Vpd2mGk43yRRc0DQkOe 211wxwP7DlUOlj6xTdlcqRCwgHEhKWK+vld1S4nQkbLm/CImQNDRMG2p mHw='
exp:        65537 (10)
modulus:    146570940549784169560470017999114332147060637684277267914353988087770100550436284153018603966728195899715841350828674502930709645679912533263178982518867204828975579005111729953303455565104878375457027758339889765627365260603987810534482349585612830776590313168338334627378223244460959284522812712332521284541 (10)
decrypted_sig: 5486124068793688683255936251187209270074392635932332070112001988456197381759672947165175699536362793613284725337872111744958183862744647903224103718245670299614498700710006264535421091908069935709303403272242499531581061652193638003161254969882234923063128204197235396325009847066687978672709751165647701 (16)
decrypted_sig: 1FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF003031300D0609608648016503040201050004203685662E4E10C6A8115074327314313B0A3E7567F3EDB0D05263BA3FA0937B55 (hex)
```

次に、A RRとRRSIG RRからハッシュ値を計算する。
これが先ほどRRSIGの署名部分から復号したものに一致すれば署名を検証したことになる。
ハッシュ値を計算するには、以下のデータを連結してSHA256のハッシュ値を計算すれば良い。

- RRSIG RDATAのレコードタイプ
- 同、アルゴリズム
- 同、ラベル数
- 同、オリジナルのTTL
- 同、有効期間の終わり
- 同、有効期間の始まり
- 同、キータグ
- 同、署名者の名前
- 保護対象となるA RRのDNS名
- 同、レコードタイプ
- 同、クラス
- 同、TTL
- 同、RDATAの長さ
- 同、RDATAの値











次に、ZSKを使ってRRSIGの署名を計算する。








次に、DNSKEY RRの公開鍵を取り出すことにする。





管理者がゾーンに署名した時には、
- DNSKEY RDATAの公開鍵を使って同様の署名を行った
- RRSIG RDATAの署名部分を除いた残り全部についてZSKで署名し、その署名をBASE64符号化してRRSIG RDATAの署名部分に追加した
はずなので、この署名と
ときの署名が一致するかどうかを確認する。
両者が一致すれば、RRSIG RRは確かにDNSKEY RRを使って署名されているということがわかる。





$ drill -DS -k /usr/local/etc/unbound/root.key eng-blog.iij.ad.jp. A
;; Number of trusted keys: 2
;; Chasing: eng-blog.iij.ad.jp. A


DNSSEC Trust tree:
eng-blog.iij.ad.jp. (A)
|---iij.ad.jp. (DNSKEY keytag: 13173 alg: 8 flags: 256)
    |---iij.ad.jp. (DNSKEY keytag: 18490 alg: 8 flags: 257)
    |---iij.ad.jp. (DS keytag: 18490 digest type: 2)
        |---jp. (DNSKEY keytag: 13611 alg: 8 flags: 256)
            |---jp. (DNSKEY keytag: 35821 alg: 8 flags: 257)
            |---jp. (DS keytag: 35821 digest type: 2)
                |---. (DNSKEY keytag: 53148 alg: 8 flags: 256)
                    |---. (DNSKEY keytag: 20326 alg: 8 flags: 257)
;; Chase successful


https://github.com/motok/NotsKotsMemo/blob/5784509cdcaccb54d41a56510ab8ca4b1198d8f4/DNSSEC_verify_by_hand/dnssec_validate.py#L21
