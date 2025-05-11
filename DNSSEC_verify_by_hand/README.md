# DNSSEC verification by hand

DNSSECを知らないのでちょっと勉強したいと思っていたら、
IIJ Engineers Blog「
[手を動かしてDNSSECの検証をやってみよう](https://eng-blog.iij.ad.jp/archives/7689)
」を見つけた。
コマンドラインでDNSSECの信頼の鎖を追ってみようという趣旨で、
ちょうど良いのでこれに従う形でやってみることにします。
IIJさん、良い記事を出していただいてありがとうございます。
なお、本稿に錯誤などがあれば、もちろんすべて本稿の責任であります。

## DNSSECの資料など

- [RFC 9364 DNS Security Extensions (DNSSEC)](https://tex2e.github.io/rfc-translater/html/rfc9364.html)
  - DNSSEC関連のRFCのガイドマップみたいなRFC。
  - RFC 9364自体は他のRFCを更新しない。

- DNSSECの中核的なRFC
  - [RFC 4033 - DNS Security Introduction and Requirements 日本語訳](https://tex2e.github.io/rfc-translater/html/rfc4033.html)
    - [JPRS翻訳版 RFC 4033](https://jprs.jp/tech/material/rfc/RFC4033-ja.txt)
  - [RFC 4034 - Resource Records for the DNS Security Extensions 日本語訳](https://tex2e.github.io/rfc-translater/html/rfc4034.html)
    - [JPRS版 RFC 4034](https://jprs.jp/tech/material/rfc/RFC4034-ja.txt)
    - DNSKEY, RRSIG, DSなどの定義がある。
  - [RFC 4035 - Protocol Modifications for the DNS Security Extensions 日本語訳](https://tex2e.github.io/rfc-translater/html/rfc4035.html)
    - [JPRS版 RFC 4035](https://jprs.jp/tech/material/rfc/RFC4035-ja.txt)
  - [RFC 6840 - Clarifications and Implementation Notes for DNS Security (DNSSEC) 日本語訳](https://tex2e.github.io/rfc-translater/html/rfc6840.html)

- [DNSViz](https://dnsviz.net/d/eng-blog.iij.ad.jp/dnssec/) とその
  [ローカルコピー](./eng-blog.iij.ad.jp-2025-05-08-06_43_34-UTC.svg)
  - 今回検証してみる`eng-blog.iij.ad.jp`のA RRからルートのDNSKEYまでの
    信頼の鎖の図。
  - RRSIGは矢印の部分に隠れている。

- drillコマンドによる信頼の鎖
  ``` shell
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
  ```

- dnspython
  - 本稿では、DNSSECの処理を行う上で、大いに
    [dnspython 2.7](https://www.dnspython.org/news/2.7.0/)
    のお世話になった。
  - [dnspythonマニュアル](https://dnspython.readthedocs.io/en/stable/)
  - [dnspythonリポジトリ](https://github.com/rthalley/dnspython)

## 関連するリソースレコードの取得

関連するRRとしては、A, RRSIG, DNSKEY, DSがあるので、一通り取得しておく。
コマンドラインとしては、`dig +dnssec -t A eng-blog.iij.ad.jp`など。

https://github.com/motok/NotsKotsMemo/blob/5784509cdcaccb54d41a56510ab8ca4b1198d8f4/DNSSEC_verify_by_hand/dnssec_validate.py#L21-L34


## A_RRを信頼できるか？

`eng-blog.iij.ad.jp`のAリソースレコードである
A\_RRが信頼できるかどうかを知るためには、対応するRRSIGとDNSKEYを使って
検証する必要がある。
これには、次のふたつのハッシュ値が一致するか否かを調べる。
  1. RRSIGにはDNSKEYで署名されたハッシュ値があるので、これを取り出す。
	 このハッシュ値は、権威DNSサーバでA\RRとRRSIGから計算したもの。
  1. A\_RRとRRSIGを使って上記のハッシュ値を再計算する。
両者が一致するなら、「DNSKEYを信頼できる」という条件下でA\_RRを信頼す
ることができる。
信頼の鎖の最初のひとつである。

### RRSIG\_A\_RR

RRSIGの定義は
[RFC 4034の3 RRSIGリソースレコード](https://tex2e.github.io/rfc-translater/html/rfc4034.html#3--The-RRSIG-Resource-Record)
の節にある。

今、我々は`eng-blog.iij.ad.jp`のA RRを検証しようとしているので、
同じowner名のRRSIG RRでType Coveredが'A'であるもの、
すなわち、上で取得したうちのRRSIG\_A\_RRを使うことになる。
同様に、AAAA RRを検証しようとするなら、RRSIG_AAAA_RRが対応する。

さて、このRRSIG\_A\_RRでは、アルゴリズム/algorithmが'8'となっている。
このアルゴリズムは、元々は
[RFC4034のA.1. DNSSECアルゴリズムタイプ](https://tex2e.github.io/rfc-translater/html/rfc4034.html#A-1--DNSSEC-Algorithm-Types)
節で定義されていたが、その後拡張された
[RFC 5072の3.1 RSA/SHA-256 RRSIGリソースレコード](https://tex2e.github.io/rfc-translater/html/rfc5702.html#3-1--RSASHA-256-RRSIG-Resource-Records)
に'8'なら'RSA/SHA256'だよと書かれている。

次のラベル数/labelsは'4'であるが、これは、ownerの
`eng-blog.iij.ad.jp`にはラベルとして`eng-blog`, `iij`, `ad`, `jp`の４
個があるよということである。
この辺も署名検証の時にはチェックするのであるが、本稿ではあまり立ち入ら
ない。

続いてオリジナルTTL/original ttlがあり、これは、DNSリゾルバなどでTTLを
減算する場合があるので、元の権威DNSサーバでのTTLを保存しておくものらし
い。
ここでの例で言えばA\_RRのTTLが減算される場合があるが、ハッシュ値計算の
対象になっているので元々のTTLが不明だとハッシュ値が変わってしまって都
合が悪く、RRSIG\_A\_RR側に記録しておく必要があるということだと理解して
いる。

有効期間終了/expirationと有効期間開始/inceptionは、当該RRSIGがいつから
いつまで有効であるかを示す。この有効期間の外のタイミングでは署名検証が
意味を持たないので失敗させるべきということのようだ。

署名者signerは、署名検証の対象(ここではA\_RR)に対して署名を行うもの、
つまりDNSKEY\_A\_RRの所有者ということで、ここでは`iij.ad.jp`となってい
る。

鍵タグ/key\_tagは、RRSIGの署名/signatureを作成するのにどの鍵、つまり
どのDNSKEYを使ったかを「示唆」するチェックサム値である。
チェックサム値が衝突することもあるし、該当するDNSKEYが見つからないこと
もあるらしいが、その時は全部のDNSKEYを試せということのようである。

### DNSKEY_A_RRのkey\_tagを計算する

RRSIGにはkey\_tagが直接に書いてあるが、DNSKEYには書いていないので計算
しなければならない。
その計算方法は、
[RFC4034 付録B. キータグ計算](https://tex2e.github.io/rfc-translater/html/rfc4034.html#A-2--DNSSEC-Digest-Types)
に出ているし、上述のIIJさんのブログにはPython実装がある。
これらを整理したのが
[key_tag.py](./key_tag.py)
であるが、
[dns.dnssec.key_id()](https://dnspython.readthedocs.io/en/stable/dnssec.html#dns.dnssec.key_id)
でもできる。
やっていることは同じで、2バイトずつ取ってきて足し合わせてチェックサム
を計算するだけである。
(アルゴリズムによってはやり方が変わる。ここではアルゴリズム'8'の場合。)

https://github.com/motok/NotsKotsMemo/blob/f7cdac56cb69d15d71b7f4bc6a20415176ad4fc4/DNSSEC_verify_by_hand/key_tag.py#L39-L45

毎回計算するのも面倒なので、ここで計算しておく。

  | DNSKEY          | key_tag |
  | --------------- | ------- |
  | DNSKEY_KSK_RR   |  18490  |
  | DNSKEY_ZSK_0_RR |  31668  |
  | DNSKEY_ZSK_1_RR |  13173  |

RRSIG\_A\_RR に書かれているkey\_tagは13173なので、DNSKEY\_ZSK\_1\_RRが
対応することがわかる。

これで、A\_RRを信用して良いかどうかを検証するには、
RRSIG\_A\_RRとDNSKEY\_ZSK\_1\_RRを持ちいればよいことがわかった。
以下では、このような対応関係を
A\_RR/RRSIG\_A\_RR/DNSKEY_ZSK_1\_RR
のように略記する場合がある。

### DNSKEY\_ZSK\_1\_RRの公開鍵

では、DNSKEY\_ZSK\_1\_RRの公開鍵を取り出してみる。
実は、下のようにdnspythonを使ってRRをパースしていれば、
`dnskey\_zsk\_1\_rdset.key`みたいに取り出せる。

https://github.com/motok/NotsKotsMemo/blob/34ed7265f1a6a9ebcff78d5b7842eef768967847/DNSSEC_verify_by_hand/dnssec_validate.py#L79

https://github.com/motok/NotsKotsMemo/blob/34ed7265f1a6a9ebcff78d5b7842eef768967847/DNSSEC_verify_by_hand/dnssec_validate.py#L92

ここではもう少し先まで手動でやってみることにする。

先ほどRRSIGのアルゴリズム'8'を定義していたRFC 5702から
RFC 3110を参照していて、
[RFC 3110の2. RSA公開キーリソースレコード](https://tex2e.github.io/rfc-translater/html/rfc3110.html#2--RSA-Public-KEY-Resource-Records)
の節にRSAパブリックキーを(DNSKEYに)格納するやり方が出ている。
ただし、これはアルゴリズム'5'のRSA/SHA-1の場合っぽいけれども、
アルゴリズム'8'のRSA/SHA256でも同様であるようだ。

DNSKEYの公開鍵部分はBASE64で符号化されているので、最初にこれを復号しな
ければならないが、出てきたバイト列の構造は次のようになっているとのこと。

- バイト列の先頭1バイトが0x00の場合
  - 続く3バイト(第2から第4バイト)がRSA暗号のexponent
  - さらに続く第5バイトから最後までがRSA暗号のmodulus
- バイト列の先頭1バイトが0x00ではない場合
  - その1バイトがexponentの長さ(exp_len)
  - 続くexp_lenバイトがexponent
  - 残りの部分がmodulus

これをPythonで書くとこんな感じ。
ただし、この関数に渡す前にBASE64で復号済み。

https://github.com/motok/NotsKotsMemo/blob/34ed7265f1a6a9ebcff78d5b7842eef768967847/DNSSEC_verify_by_hand/dnssec_validate.py#L48-L58

このやり方でDNSKEY\_ZSK\_1\_RRから公開鍵(exponentとmodulus)を取り出す
と、次のようになった。

- exponent = 65537
- modulus = 127007425912000964714488293271813959090212068161547110390988345674781145963374145989328419379148946371196272690229816465331643091364504475049944858816134973456196613482581042741256361207887996874819718427946428176799616565692650827777062173351660205069754025885554424489650651260567113445763743276360536538071 (10進数)

### RRSIG\_A\_RRの署名検証

DNSKEY\_A\_RRから公開鍵を取り出すことができたので、これを使って
RRSIG\_A\_RRのsignatureを検証する。

これもdnspythonを使えば`dns.dnssec.validate()`でできる。

https://github.com/motok/NotsKotsMemo/blob/34ed7265f1a6a9ebcff78d5b7842eef768967847/DNSSEC_verify_by_hand/dnssec_validate.py#L125-L133

手動でやってみるとなると、
signatureを整数として取り出す部分は

https://github.com/motok/NotsKotsMemo/blob/34ed7265f1a6a9ebcff78d5b7842eef768967847/DNSSEC_verify_by_hand/dnssec_validate.py#L160

のようにできて、公開鍵で検証(復号)しているのが

https://github.com/motok/NotsKotsMemo/blob/34ed7265f1a6a9ebcff78d5b7842eef768967847/DNSSEC_verify_by_hand/dnssec_validate.py#L164

であり、
[RFC 5702の3. RRSIGリソースレコード](https://tex2e.github.io/rfc-translater/html/rfc5702.html#3--RRSIG-Resource-Records)
にあるように、

- 先頭にパディング 0x0001FFFFFF..FF00があり
- 次にPKCS#1 v2.1のprefix(0x3031300d060960864801650304020105000420)が
  あって
- その後にハッシュ値が続く

形をしている。
そこで、

https://github.com/motok/NotsKotsMemo/blob/34ed7265f1a6a9ebcff78d5b7842eef768967847/DNSSEC_verify_by_hand/dnssec_validate.py#L169-L170

のようにしてハッシュ値を取り出す。
このハッシュ値は、次のとおりであった。

- RRSIGから取り出したハッシュ値 = 87116a741e706921046eb34133178e418bcc44dbc3e609b7fa1fec3884c56c1e

### A\_RRとRRSIG\_A\_RRからハッシュ値を計算する

ここで、別の方法、すなわちA\_RRとRRSIG\_A\_RRを使ってハッシュ値を再計
算する。
この計算方法は
[RFC 4034 3.1.8.1. 署名計算](https://tex2e.github.io/rfc-translater/html/rfc4034.html#3-1-8--The-Signature-Field)
に出ている。

> signature = sign(RRSIG_RDATA | RR(1) | RR(2) ...)

ここで、RRSIG_RDATAのところは署名部分を除くので、
[RFC 4034 3.1 RRSIG RDATAワイヤー形式](https://tex2e.github.io/rfc-translater/html/rfc4034.html#3-1--RRSIG-RDATA-Wire-Format)
の図の、Type CoveredからSigner's Nameまで(両端含む)をワイヤー形式で並
べたもの。
さらに、RRが続く部分はownerからrdatamまでの全体、ここではA\_RRが該当す
るので`eng-blog.iij.ad.jp 300 IN A 202.232.2.183`の全体をワイヤー形式
で表現したもの。
ただし、TTLのところは、途中のリゾルバが減算してたりするので、RRSIGの
original ttlで上書きしておかないといけない。
`|`の意味は連結(concatenation)ということなので、Python的にはbytes型を
`+`で連結すればよい。

このハッシュ値計算をしている部分は次のとおりで、今回の例では、ハッシュ
値が
`0x87116a741e706921046eb34133178e418bcc44dbc3e609b7fa1fec3884c56c1e`
となった。

https://github.com/motok/NotsKotsMemo/blob/34ed7265f1a6a9ebcff78d5b7842eef768967847/DNSSEC_verify_by_hand/dnssec_validate.py#L174-L195


これで、RRSIG\_A\_RRの署名部分から復号したハッシュ値と、
RRSIG\_A\_RRおよびA\_RRから計算したハッシュ値が一致することがわかった。
DNSKEYの公開鍵に対応する秘密鍵を知ることなしにはこれらを一致させること
が非常に困難なので、DNSKEY\_ZSK\_1\_RRを信じて良いならA\_RRを信じて良
いことがわかった。

## DNSKEY\_ZSK\_1\_RRを信頼できるか？

では、DNSKEY\_ZSK\_1\_RRを信用することはできるのか？
これには、A\_RRの時と同様に、DNSKEY\_ZSK\_1\_RRに対応するRRSIGとDNSKEY
を使って署名を検証すればよいはずである。
先に結果を述べると、本稿ではこの署名検証に成功することができなかった。
上記のDNSVizやdrillコマンドでは検証できているので、本稿のやり方が間違っ
ているということになるが、筆者には誤りを見つけることができなかった。
先達諸賢のご教示を乞いたいところであります。

気を取り直して、署名検証をやってみよう。
信用できるか否かを知りたいリソースレコードはDNSKEY\_ZSK\_1\_RRで、これ
に対応する可能性のあるRRSIGは、RRSIG_DNSKEY_0_RRとRRSIG_DNSKEY_1_RRの
２個である。

https://github.com/motok/NotsKotsMemo/blob/f2dabcfa3a429276622a7e9f4c76e817256e64c4/DNSSEC_verify_by_hand/dnssec_validate.py#L30-L32

dns.dnssec.validate()を用いて署名検証を試みているのは下の部分である。

https://github.com/motok/NotsKotsMemo/blob/f2dabcfa3a429276622a7e9f4c76e817256e64c4/DNSSEC_verify_by_hand/dnssec_validate.py#L220

手元にある３個のDNSKEYを全て使ってvalidate_keysを作り(L.229)、
それを使ってDNSKEY\_ZSK\_1\_RRとRRSIG\_DNSKEY\_0\_RRのペアについて
署名検証を試みた(L.235)が成功しなかった。
もう一つのRRSIGであるRRSIG\_DNSKEY\_1\_RRについても試みた(L.243)が、
やはり成功しなかった。

では、手動で検証する方法ではどうか？
下のように、A\_RRの時と同様にやってみたが、やはり成功しなかった。

https://github.com/motok/NotsKotsMemo/blob/f2dabcfa3a429276622a7e9f4c76e817256e64c4/DNSSEC_verify_by_hand/dnssec_validate.py#L251-L307


本来であれば、KSKとそれを利用したRRSIG、つまり
DNSKEY\_ZSK\_1\_RR/RRSIG\_DNSKEY\_1\_RR/DNSKEY\_KSK\_RR
の組み合わせで署名が検証できるはずであるが、できなかったということにな
る。
DNSVizやdrillコマンドでは署名検証できているので、本稿のやり方がおかし
いのであるが、誤りを発見できていない。
先達諸賢の皆様のご教示を切に乞い願うところであります。

## DNSKEY\_KSK\_RRを信頼できるか？

