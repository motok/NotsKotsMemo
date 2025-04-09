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

このRRSIGのフィールドは以下のように読める。

+----------------+-------------------+-------------------------------------------------+
| フィールド     | 値                | 意味                                            |
+----------------+-------------------+-------------------------------------------------+
| 署名対象タイプ | A                 | (eng-blog.iij.ad.jpの) A RR に対する署名である  |
+----------------+-------------------+-------------------------------------------------+





| アルゴリズム   | 8                 | DNSKEYアルゴリズム8番はRSASHA256(RFC8624)       |
| ラベル数       | 4                 | (eng-blog.iij.ad.jpの)ラベルの数。              |
| オリジナルTTL  | 300               | 権威サーバで付与されたTTL(リゾルバなどが書き換えることがあるのでここに書いておく？) |
| 有効期間終了   | 20250505151004    | いつまで有効な署名であるか                      |
| 有効期間開始   | 20250405151004    | いつから有効な署名であるか                      |
| 鍵タグ         | 31668             | DNSKEY RRのRDATA部分のチェックサム。計算方法はRFC4034で独自に定義。このRRSIGに対応するDNSKEYを探す手掛かりとなる。 |
| 署名者名       | iij.ad.jp.        | 対応するDNSKEY RRの所有者                       |
| 署名           | FZZeDLZhGl7Cd.... | RRSIG RDATA(ただし署名フィールドを除く)を対象とした署名。アルゴリズムに応じて計算方法が変わる。 |
+----------------+-------------------+-------------------------------------------------+

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
257 3 8 AwEAAahXWyIn8JmvtyrzvlNNYFvACfOS/LZoOpUzF3HpFje8ySj6z4d7 5p4P4VSIelgRFXDtjYpeqc8uUxIo6lg6Y69gyH+QK9UPS5/GdDlxpl2F jp7LifaeWPpMAYtr8frwjImY0sDeeWfYqgwZZD722aSEArM5Wpjft5F+ UzbPAnTYBnri29UA6YVCg4ZFRrGBYAUWKJfngPKMNRjLUyr9LeqgQp95 nal86y4LQjEJNbSXlP6GA0OOZ0JuyIZLJ8NPPqM8HD13DFDOc5He5pn/ N7PfCB5WGvYx58ZEvxpqWf0+V2a2XE6c1Ffomil/fQNiAu5JFTgumHY1 OXS5oLdRiuM=
18490

256 3 8 AwEAAdC5VKJuA30xxtw4DE2t5ihxGKzc3o527l1na+uUh/KkKLvqmYdT +t7kBKP1SVnO6Mz9w7wqqpiV5VwKdb0CWyA0N7rlBnWWhRCkIzVp/iuu ZB+fO4EcBKrUckWf6Kx/a7HXxRFrkF0Bi0E3dy8pMBbRukQpNOXFqlkc RR/G6qO9
31668

256 3 8 AwEAAayQtSx/pvXV+AoGFJeNPv5vnZf6BATFUrx/ys5j9BQ3emE3sab4 Hro/zW1n/pEmfDG/AlC/mFg9t0vrFimiLM8GsymNoIXpw0PbaTbi0jhD 4eDUGZ2OpjtWMyCUYJPMfjx3pAisWg5zSYWuKQiv8TFbfy7yoWY6RzlV dbma9kop
47508
```
ということで、二つ目の 256 3 8 で始まって RR/G6qO9 で終わるものが「対応する」。


