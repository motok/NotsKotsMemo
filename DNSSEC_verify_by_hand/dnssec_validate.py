#! /usr/bin/env python3

# IIJさんのエンジニアブログに「手を動かしてDNSSECの検証をやってみよう」という
# 記事があり、大変参考になった(というか、ほぼ翻案させていいただいた)。
# 記して感謝する。https://eng-blog.iij.ad.jp/archives/7689

from datetime import datetime as dtdt
from datetime import UTC as dtUTC
import base64
import re
import io
import hashlib

import dns.name
import dns.rdataclass
import dns.rdatatype
import dns.rdata
import dns.rdataset
import dns.dnssec

A_RR = 'eng-blog.iij.ad.jp.     300     IN      A       202.232.2.183'
AAAA_RR = 'eng-blog.iij.ad.jp.     300     IN      AAAA    2001:240:bb81::10:183'
RRSIG_A_RR = 'eng-blog.iij.ad.jp.     300     IN      RRSIG   A 8 4 300 20250606151004 20250507151004 13173 iij.ad.jp. TDdzswAs9+VZoN36cW90heOvBDL2u+ieWTcpPnFGitkovAIyXrYrMVtA UbTBdqLOvDMIvuwXA+Eww9Z2PqJszX+1R7F0zVDRo1XQ7kABPjMIjrn+ 1ecRtW5SAkLyaZy6QpwpIVedIUuFYX/2917hwbIRp1QaYnBfTqOtuqAc 6Wc='
RRSIG_AAAA_RR = 'eng-blog.iij.ad.jp.     300     IN      RRSIG   AAAA 8 4 300 20250606151004 20250507151004 13173 iij.ad.jp. rbxLu0WIN33K3uGidjRzyybZZRkTACiTDibuEufO8skQDoXHnqWxagHM EX1UrIFjkRbWcAfZ1LAVvjido+sHbzCzzOrnwu/WjGqN9aG/8xL91GjE a9wsn2jqqRCa+qiYGo0R5yN9W1MO8Y7EYcdbRuLj1jv7+GOcPJs5Uxbe OVk='
# key_tag=18490
DNSKEY_KSK_RR = 'iij.ad.jp.              86400   IN      DNSKEY  257 3 8 AwEAAahXWyIn8JmvtyrzvlNNYFvACfOS/LZoOpUzF3HpFje8ySj6z4d7 5p4P4VSIelgRFXDtjYpeqc8uUxIo6lg6Y69gyH+QK9UPS5/GdDlxpl2F jp7LifaeWPpMAYtr8frwjImY0sDeeWfYqgwZZD722aSEArM5Wpjft5F+ UzbPAnTYBnri29UA6YVCg4ZFRrGBYAUWKJfngPKMNRjLUyr9LeqgQp95 nal86y4LQjEJNbSXlP6GA0OOZ0JuyIZLJ8NPPqM8HD13DFDOc5He5pn/ N7PfCB5WGvYx58ZEvxpqWf0+V2a2XE6c1Ffomil/fQNiAu5JFTgumHY1 OXS5oLdRiuM='
# key_tag=31668
DNSKEY_ZSK_0_RR = 'iij.ad.jp.              86400   IN      DNSKEY  256 3 8 AwEAAdC5VKJuA30xxtw4DE2t5ihxGKzc3o527l1na+uUh/KkKLvqmYdT +t7kBKP1SVnO6Mz9w7wqqpiV5VwKdb0CWyA0N7rlBnWWhRCkIzVp/iuu ZB+fO4EcBKrUckWf6Kx/a7HXxRFrkF0Bi0E3dy8pMBbRukQpNOXFqlkc RR/G6qO9'
# key_tag=13173
DNSKEY_ZSK_1_RR = 'iij.ad.jp.              86400   IN      DNSKEY  256 3 8 AwEAAbTdVP0D8FFw/Tkjd9ZGMWqV+79pLtmKBbP7hy+k23DTXlHhX3mB G1Ylot7WLrCqg6LpIhk+PDzgizdQTcYR1S3uhMoTI3pytRR7GgCoB2d9 DaPaTt/ZUHm4CBKd2Yiw8SABXxkMdshqyqTVyRtgXBXRFSnhbSm0qoht 2ZI75bvX'
RRSIG_DNSKEY_0_RR = 'iij.ad.jp.              86400   IN      RRSIG   DNSKEY 8 3 86400 20250606151004 20250507151004 13173 iij.ad.jp. LbBYzPO6HmZiM8WIjNqXYrgicNMbttYD8oUTu2yrzVGzS+YrlIG8bnUV mzypYsj/LpJ7KJthCpU1YwvpJJ3kV2Er82PP2gKU09Gnu+38Ca5Auw7j dV6vkCK/vjn8rJKPmFfV9U65vm61CxIpfP+NXT/gNLxqM2FjjgzQRQLm TjE='
RRSIG_DNSKEY_1_RR = 'iij.ad.jp.              86400   IN      RRSIG   DNSKEY 8 3 86400 20250606151004 20250507151004 18490 iij.ad.jp. SLihKpwzMXQnzRHjTCPp6Y+UtVmbNEnEtheMHLyh6sI+IDOIP9os8E/U 3HawZgcXNMfLDaTj45rqU28k0wrAXo0rfG8Xif551CEB3chVIHDnqQbz iCroPEouZyksN3a/5bqkk2myhKzXDpYPfgI2r+4kGF/J1MV50Q3WN9A9 IDTNm2hqz/1jyFJic01igoV3fllepNncptJkZBqcCa7nGt07Lj1Mxvfp VIJnwjEUWflwosMYiyCjBIPVRj5TqOJiD8gbE1C5QjGF+SNKkF0qXL++ iVPrD4ePAvtdBj9Q5XehvnFfMN6EWZb6qcV61hB7xzr610pTrYO5qSJj rgnQHg=='
DS_RR = 'iij.ad.jp.              7200    IN      DS      18490 8 2 B354CF936F041F1E8D7E9420308AF5243E90B50A16E68AEBCB173049 54BD1AB1'
RRSIG_DS_RR = 'iij.ad.jp.              7200    IN      RRSIG   DS 8 3 7200 20250602174503 20250503174503 13611 jp. Z0JOJGgThFCMUcbthFpX6nLswWj9ygXt9CnXANTZkLRbDR7gjlkpp/k2 Cn4umcw1Ck9ATUk8ml8KnaOv9ULQjZIb4Z4m4wNIK4i7DOFfdxaaKD74 HloJZB7dgGmn42LqovECc1mQ3+DtwRYkzazxRsXULQtFoJA4h1DYJr3F Aro='

def parse_rr_str(rr_str: str):
    arr = rr_str.split()
    owner = dns.name.from_text(arr[0])
    ttl = int(arr[1])
    rdclass = dns.rdataclass.from_text(arr[2])
    rdtype = dns.rdatatype.from_text(arr[3])
    rest_data = ' '.join(arr[4:])
    rdata = dns.rdata.from_text(rdclass, rdtype, rest_data)
    rdset = dns.rdataset.Rdataset(rdclass, rdtype)
    rdset.add(rdata, ttl)
    return (owner, rdset)

def rsa_exponent_modulus_from_dnskey_key(dnskey_key: bytes):
    if dnskey_key[0] == 0:
        explen = int.from_bytes(dnskey_key[1:3], 'big')
        exponent = int.from_bytes(dnskey_key[3:3+explen], 'big')
        modulus = int.from_bytes(dnskey_key[3+explen:], 'big')
        modulus_len = len(dnskey_key[3+explen:])
    else:
        explen = dnskey_key[0]
        exponent = int.from_bytes(dnskey_key[1:1+explen], 'big')
        modulus = int.from_bytes(dnskey_key[1+explen:], 'big')
        modulus_len = len(dnskey_key[1+explen:])

    if False:
        print(f'DNSKEY key: {dnskey_key}')
        print( 'DNSKEY decoded.')
        print(f'  exponent length: {explen}')
        print(f'  exponent: {exponent}')
        print(f'  modulus: {modulus} (10)')
        print(f'  len(modulus): {modulus_len*8} bits')

    return (exponent, modulus)

if __name__ == '__main__':

    # 各RRを(owner, rdset)の形に読み込む。
    (a_owner, a_rdset) = parse_rr_str(A_RR)
    (aaaa_owner, aaaa_rdset) = parse_rr_str(AAAA_RR)
    (rrsig_a_owner, rrsig_a_rdset) = parse_rr_str(RRSIG_A_RR)
    (rrsig_aaaa_owner, rrsig_aaaa_rdset) = parse_rr_str(RRSIG_AAAA_RR)
    (dnskey_ksk_owner, dnskey_ksk_rdset) = parse_rr_str(DNSKEY_KSK_RR)
    (dnskey_zsk_0_owner, dnskey_zsk_0_rdset) = parse_rr_str(DNSKEY_ZSK_0_RR)
    (dnskey_zsk_1_owner, dnskey_zsk_1_rdset) = parse_rr_str(DNSKEY_ZSK_1_RR)
    (rrsig_dnskey_0_owner, rrsig_dnskey_0_rdset) = parse_rr_str(RRSIG_DNSKEY_0_RR)
    (rrsig_dnskey_1_owner, rrsig_dnskey_1_rdset) = parse_rr_str(RRSIG_DNSKEY_1_RR)
    (ds_owner, ds_rdset) = parse_rr_str(DS_RR)
    (rrsig_ds_owner, rrsig_ds_rdset) = parse_rr_str(RRSIG_DS_RR)

    if False:
        print(f'A_RR: {a_owner} {a_rdset.ttl} {dns.rdataclass.to_text(a_rdset.rdclass)} {dns.rdatatype.to_text(a_rdset.rdtype)} {a_rdset[0].address}')
        print(f'AAAA_RR: {aaaa_owner} {aaaa_rdset.ttl} {dns.rdataclass.to_text(aaaa_rdset.rdclass)} {dns.rdatatype.to_text(aaaa_rdset.rdtype)} {aaaa_rdset[0].address}')
        print(f'RRSIG_A_RR: {rrsig_a_owner} {rrsig_a_rdset.ttl} {dns.rdataclass.to_text(rrsig_a_rdset.rdclass)} {dns.rdatatype.to_text(rrsig_a_rdset.rdtype)} {dns.rdatatype.to_text(rrsig_a_rdset[0].type_covered)} {rrsig_a_rdset[0].algorithm} {rrsig_a_rdset[0].labels} {rrsig_a_rdset[0].original_ttl} {dtdt.fromtimestamp(rrsig_a_rdset[0].expiration, dtUTC).strftime("%Y%m%d%H%M%S")} {dtdt.fromtimestamp(rrsig_a_rdset[0].inception, dtUTC).strftime("%Y%m%d%H%M%S")} {rrsig_a_rdset[0].key_tag} {rrsig_a_rdset[0].signer} {base64.b64encode(rrsig_a_rdset[0].signature).decode("ascii")}')
        print(f'RRSIG_AAAA_RR: {rrsig_aaaa_owner} {rrsig_aaaa_rdset.ttl} {dns.rdataclass.to_text(rrsig_aaaa_rdset.rdclass)} {dns.rdatatype.to_text(rrsig_aaaa_rdset.rdtype)} {dns.rdatatype.to_text(rrsig_aaaa_rdset[0].type_covered)} {rrsig_aaaa_rdset[0].algorithm} {rrsig_aaaa_rdset[0].labels} {rrsig_aaaa_rdset[0].original_ttl} {dtdt.fromtimestamp(rrsig_aaaa_rdset[0].expiration, dtUTC).strftime("%Y%m%d%H%M%S")} {dtdt.fromtimestamp(rrsig_aaaa_rdset[0].inception, dtUTC).strftime("%Y%m%d%H%M%S")} {rrsig_aaaa_rdset[0].key_tag} {rrsig_aaaa_rdset[0].signer} {base64.b64encode(rrsig_aaaa_rdset[0].signature).decode("ascii")}')
        print(f'DNSKEY_KSK_RR: {dnskey_ksk_owner} {dnskey_ksk_rdset.ttl} {dns.rdataclass.to_text(dnskey_ksk_rdset.rdclass)} {dns.rdatatype.to_text(dnskey_ksk_rdset.rdtype)} {dnskey_ksk_rdset[0].flags} {dnskey_ksk_rdset[0].protocol} {dnskey_ksk_rdset[0].algorithm} {base64.b64encode(dnskey_ksk_rdset[0].key).decode("ascii")}')
        print(f'DNSKEY_ZSK_0_RR: {dnskey_zsk_0_owner} {dnskey_zsk_0_rdset.ttl} {dns.rdataclass.to_text(dnskey_zsk_0_rdset.rdclass)} {dns.rdatatype.to_text(dnskey_zsk_0_rdset.rdtype)} {dnskey_zsk_0_rdset[0].flags} {dnskey_zsk_0_rdset[0].protocol} {dnskey_zsk_0_rdset[0].algorithm} {base64.b64encode(dnskey_zsk_0_rdset[0].key).decode("ascii")}')
        print(f'DNSKEY_ZSK_1_RR: {dnskey_zsk_1_owner} {dnskey_zsk_1_rdset.ttl} {dns.rdataclass.to_text(dnskey_zsk_1_rdset.rdclass)} {dns.rdatatype.to_text(dnskey_zsk_1_rdset.rdtype)} {dnskey_zsk_1_rdset[0].flags} {dnskey_zsk_1_rdset[0].protocol} {dnskey_zsk_1_rdset[0].algorithm} {base64.b64encode(dnskey_zsk_1_rdset[0].key).decode("ascii")}')
        print(f'RRSIG_DNSKEY_0_RR: {rrsig_dnskey_0_owner} {rrsig_dnskey_0_rdset.ttl} {dns.rdataclass.to_text(rrsig_dnskey_0_rdset.rdclass)} {dns.rdatatype.to_text(rrsig_dnskey_0_rdset.rdtype)} {dns.rdatatype.to_text(rrsig_dnskey_0_rdset[0].type_covered)} {rrsig_dnskey_0_rdset[0].algorithm} {rrsig_dnskey_0_rdset[0].labels} {rrsig_dnskey_0_rdset[0].original_ttl} {dtdt.fromtimestamp(rrsig_dnskey_0_rdset[0].expiration, dtUTC).strftime("%Y%m%d%H%M%S")} {dtdt.fromtimestamp(rrsig_dnskey_0_rdset[0].inception, dtUTC).strftime("%Y%m%d%H%M%S")} {rrsig_dnskey_0_rdset[0].key_tag} {rrsig_dnskey_0_rdset[0].signer} {base64.b64encode(rrsig_dnskey_0_rdset[0].signature).decode("ascii")}')
        print(f'RRSIG_DNSKEY_1_RR: {rrsig_dnskey_1_owner} {rrsig_dnskey_1_rdset.ttl} {dns.rdataclass.to_text(rrsig_dnskey_1_rdset.rdclass)} {dns.rdatatype.to_text(rrsig_dnskey_1_rdset.rdtype)} {dns.rdatatype.to_text(rrsig_dnskey_1_rdset[0].type_covered)} {rrsig_dnskey_1_rdset[0].algorithm} {rrsig_dnskey_1_rdset[0].labels} {rrsig_dnskey_1_rdset[0].original_ttl} {dtdt.fromtimestamp(rrsig_dnskey_1_rdset[0].expiration, dtUTC).strftime("%Y%m%d%H%M%S")} {dtdt.fromtimestamp(rrsig_dnskey_1_rdset[0].inception, dtUTC).strftime("%Y%m%d%H%M%S")} {rrsig_dnskey_1_rdset[0].key_tag} {rrsig_dnskey_1_rdset[0].signer} {base64.b64encode(rrsig_dnskey_1_rdset[0].signature).decode("ascii")}')
        print(f'RRSIG_DNSKEY_1_RR: {rrsig_dnskey_1_owner} {rrsig_dnskey_1_rdset}')
        print(f'DS_RR: {ds_owner} {ds_rdset.ttl} {dns.rdataclass.to_text(ds_rdset.rdclass)} {dns.rdatatype.to_text(ds_rdset.rdtype)} {ds_rdset[0].key_tag} {ds_rdset[0].algorithm} {ds_rdset[0].digest_type} {base64.b16encode(ds_rdset[0].digest).decode('ascii')}')
        # ↑ なんでDSだけBASE64じゃなくてBASE16を使うの？
        print(f'RRSIG_DS_RR: {rrsig_ds_owner} {rrsig_ds_rdset.ttl} {dns.rdataclass.to_text(rrsig_ds_rdset.rdclass)} {dns.rdatatype.to_text(rrsig_ds_rdset.rdtype)} {dns.rdatatype.to_text(rrsig_ds_rdset[0].type_covered)} {rrsig_ds_rdset[0].algorithm} {rrsig_ds_rdset[0].labels} {rrsig_ds_rdset[0].original_ttl} {dtdt.fromtimestamp(rrsig_ds_rdset[0].expiration, dtUTC).strftime("%Y%m%d%H%M%S")} {dtdt.fromtimestamp(rrsig_ds_rdset[0].inception, dtUTC).strftime("%Y%m%d%H%M%S")} {rrsig_ds_rdset[0].key_tag} {rrsig_ds_rdset[0].signer} {base64.b64encode(rrsig_ds_rdset[0].signature).decode("ascii")}')

    print('### A_RR の検証 ###')
    # A_RRについてDNSSECによる検証を行う。
    # まず、A_RRに対応するRRSIGは、RRSIG_A_RRである。(type_coverdに注目)
    # RRSIG_A_RRのkey_tagは13173であることが読み取れる。
    if False:
        print(f'RRSIG_A_RRのkey_tagは {rrsig_a_rdset[0].key_tag} である')

    # このkey_tagを持つDNSKEY RRを探す。
    # key_tagは、dns.dnssec.key_id()関数を使えば計算できる。
    # この結果、DNSKEY_ZSK_1_RRがA_RR/RRSIG_A_RRに対応することがわかる。
    # 計算の方法は、https://github.com/rthalley/dnspython/blob/4d97d38fc71a40e97cddf8bc3d768a085cd5a6c0/dns/dnssec.py#L112 を参照。
    if False:
        for x in (dnskey_ksk_rdset[0], dnskey_zsk_0_rdset[0], dnskey_zsk_1_rdset[0]):
            print(f'key_tag: {dns.dnssec.key_id(x)} ({x.flags} {x.protocol} {x.algorithm} {base64.b64encode(x.key).decode("ascii")[:50]}...)')

    # RRSIG_A_RRとDNSKEY_ZSK_1_RRを用いてA_RRについての署名検証を行う。
    # これは、(1) RRSIG_A_RRの署名部分をDNSKEY_ZSK_1_RRの公開鍵部分で
    # 復号した時の結果として出てくるハッシュ値と、(2) そのハッシュ値を
    # A_RRおよびRRSIG_A_RRから再計算して出てくるハッシュ値を比較して
    # 合致すれば署名検証に成功したと判断できる。

    # この検証は、dns.dnssec.validate()関数を使えばできる。
    # そして、検証に成功した。
    # なお、この関数はRRSIGのinception/expirationを見ているので、有効な
    # 日付をnow引数に渡しておく。
    valid_date = dtdt.strptime('20250508010800', '%Y%m%d%H%M%S').replace(tzinfo=dtUTC).timestamp()
    validate_keys = {dnskey_zsk_1_owner: dnskey_zsk_1_rdset}
    if True:
        try:
            dns.dnssec.validate((a_owner, a_rdset), (rrsig_a_owner, rrsig_a_rdset), validate_keys, now=valid_date)
        except dns.dnssec.ValidationFailure as e:
            print(f'dns.dnssec.validate()による検証に失敗。{e}')
        else:
            print('dns.dnssec.validate()による検証に成功.')
    # 以下は、DNSKEY_ZSK_1_RRに代えてDNSKEY_KSK_RRやDNSKEY_ZSK_0_RRでは
    # 検証できないことを試すコード。
    if False:
        validate_keys = { dnskey_zsk_0_owner: dnskey_zsk_0_rdset}
        try:
            dns.dnssec.validate((a_owner, a_rdset), (rrsig_a_owner, rrsig_a_rdset), validate_keys, now=valid_date)
        except dns.dnssec.ValidationFailure as e:
            print(f'{e}')
        else:
            print('A_RR/RRSIG_A_RR/DNSKEY_ZSK_0_RR set validated.')
    if False:
        validate_keys = { dnskey_ksk_owner: dnskey_ksk_rdset}
        try:
            dns.dnssec.validate((a_owner, a_rdset), (rrsig_a_owner, rrsig_a_rdset), validate_keys, now=valid_date)
        except dns.dnssec.ValidationFailure as e:
            print(f'{e}')
        else:
            print('A_RR/RRSIG_A_RR/DNSKEY_KSK_RR set validated.')

    # 検証のやり方を調べるために、(1)を自分でやってみる。
    # まず、DNSKEY_ZSK_1_RRからRSA公開鍵(指数とモジュラス)を取り出す。
    (exponent, modulus) = rsa_exponent_modulus_from_dnskey_key(dnskey_zsk_1_rdset[0].key)
    if False:
        print(f'exponent: {exponent}')
        print(f'modulus:  {modulus}')
    # 続いて、RRSIG_A_RRの署名部分を取り出す。
    rrsignature = int.from_bytes(rrsig_a_rdset[0].signature, 'big')
    if False:
        print(f'rrsig signature: {rrsignature}')
    # exponentとmodulusを使ってrrsignatureを復号する。
    rrhash_padded = hex(pow(rrsignature, exponent, modulus))
    if False:
        print(f'rrhash_padded: {rrhash_padded}')
    # rrhash_paddedはPKCS#1 v1.5の形式で書かれているらしい。
    # 先頭のパディングなどを取り除く。これが(1)のハッシュ値。
    pad_pattern = re.compile('^0x1(?:f)+003031300d060960864801650304020105000420', flags=re.IGNORECASE)
    rrhash = pad_pattern.sub('', rrhash_padded)
    if True:
        print(f'ハッシュ値(1): {rrhash}')

    # (2)のA_RRとRRSIG_A_RRからのハッシュ値を計算する。
    # RRSIG_A_RRのrdata部分、ただし、署名部分を取り除いたものを作る。
    rrsig_rdata_wire = rrsig_a_rdset[0].to_wire()
    # 先頭18バイトは固定長。その後に署名者(ドメイン名をDNSプロトコル的に
    # エンコードしたもの)が来て0x00でターミネートされる。この0x00を含んで
    # 0x00までの部分が必要。これがrrsig_part。
    rrsig_part = rrsig_rdata_wire[:rrsig_rdata_wire.find(0x00, 18)+1]
    
    # A_RRの全体をon wireな形で取り出す。
    # 途中のリゾルバがTTLを減算している場合があるのでRRSIGのoriginal_ttlで
    # 上書きしておく。
    with io.BytesIO() as wire:
        x = a_rdset
        x.ttl = rrsig_a_rdset[0].original_ttl
        x.to_wire(a_owner, wire)
        a_part = wire.getvalue()

    # rrsig_partとa_partを連結したもののSHA256ハッシュを取る。
    # これが(2)のハッシュ値。
    rrsig_a_hash = hashlib.sha256(rrsig_part + a_part).hexdigest()
    if True:
        print(f'ハッシュ値(2): {rrsig_a_hash}')

    # (1)と(2)のハッシュ値が一致していれば、検証成功。
    if True:
        if rrhash == rrsig_a_hash:
            print('(1)と(2)のハッシュ値が一致したので検証成功。')
        else:
            print('(1)と(2)のハッシュ値が一致しなかったので検証失敗。')

    ##########
    print('### AAAA_RR の検証 ###')

    # AAAA_RRに対応するのはRRSIG_AAAA_RRとkey_tag=13173のDNSKEY_ZSK_1_RR。
    validate_keys = {dnskey_zsk_1_owner: dnskey_zsk_1_rdset}
    if True:
        try:
            dns.dnssec.validate((aaaa_owner, aaaa_rdset), (rrsig_aaaa_owner, rrsig_aaaa_rdset), validate_keys, now=valid_date)
        except dns.dnssec.ValidationFailure as e:
            print(f'dns.dnssec.validate()による検証に失敗。{e}')
        else:
            print('dns.dnssec.validate()による検証に成功.')

    ##########
    print('### DNSKEY_ZSK_1_RR の検証 ###')

    # DNSKEY_ZSK_1_RRに対応するのはRRSIG_DNSKEY_[01]_RR。
    # これらRRSIGのkey_tagは、13173, 18490である。
    # これらのkey_tagは、それぞれ、DNSKEY_ZSK_1_RR, DNSKEY_KSK_RRに対応。
    # 色々やってみたがうまく検証できないので、鍵としてDNSKEY_*を使っても
    # 検証失敗することを示しておく。

    mykeys = dnskey_ksk_rdset
    mykeys.union_update(dnskey_zsk_0_rdset)
    mykeys.union_update(dnskey_zsk_1_rdset)
    validate_keys = {dnskey_ksk_owner: mykeys}

    if True:
        print('# DNSKEY_ZSK_1_RR/RRSIG_DNSKEY_0_RR/DNSKEY_*_RR')
        try:
            # import pdb; pdb.set_trace();
            dns.dnssec.validate((dnskey_zsk_1_owner, dnskey_zsk_1_rdset), (rrsig_dnskey_0_owner, rrsig_dnskey_0_rdset), validate_keys, now=valid_date)
        except dns.dnssec.ValidationFailure as e:
            print(f'dns.dnssec.validate()による検証に失敗。{e}')
        else:
            print('dns.dnssec.validate()による検証に成功.')

        print('# DNSKEY_ZSK_1_RR/RRSIG_DNSKEY_1_RR/DNSKEY_*_RR')
        try:
            dns.dnssec.validate((dnskey_zsk_1_owner, dnskey_zsk_1_rdset), (rrsig_dnskey_1_owner, rrsig_dnskey_1_rdset), validate_keys, now=valid_date)
        except dns.dnssec.ValidationFailure as e:
            print(f'dns.dnssec.validate()による検証に失敗。{e}')
        else:
            print('dns.dnssec.validate()による検証に成功.')

    # 仕方がないので、DNSKEY_ZSK_1_RR/RRSIG_DNSKEY_1_RR/DNSKEY_KSK_RR
    # について手動で検証を試みる。
    print('### DNSKEY_ZSK_1_RR の手動検証 ###')

    # まずはハッシュ値(1)
    # まず、DNSKEY_KSK_RRからRSA公開鍵(指数とモジュラス)を取り出す。
    (exponent, modulus) = rsa_exponent_modulus_from_dnskey_key(dnskey_ksk_rdset[0].key)
    if False:
        print(f'exponent: {exponent}')
        print(f'modulus:  {modulus}')

    # 続いて、RRSIG_DNSKEY_1_RRの署名部分を取り出す。
    rrsignature = int.from_bytes(rrsig_dnskey_1_rdset[0].signature, 'big')
    if False:
        print(f'rrsig signature: {rrsignature}')
    # exponentとmodulusを使ってrrsignatureを復号する。
    rrhash_padded = hex(pow(rrsignature, exponent, modulus))
    if False:
        print(f'rrhash_padded: {rrhash_padded}')
    # rrhash_paddedはPKCS#1 v1.5の形式で書かれているらしい。
    # 先頭のパディングなどを取り除く。これが(1)のハッシュ値。
    pad_pattern = re.compile('^0x1(?:f)+003031300d060960864801650304020105000420', flags=re.IGNORECASE)
    rrhash = pad_pattern.sub('', rrhash_padded)
    if True:
        print(f'ハッシュ値(1): {rrhash}')

    # ハッシュ値(2)を計算する。
    # RRSIG_DNSKEY_1_RRのrdata部分、ただし、署名部分を取り除いたものを作る。
    rrsig_rdata_wire = rrsig_dnskey_1_rdset[0].to_wire()
    # 先頭18バイトは固定長。その後に署名者(ドメイン名をDNSプロトコル的に
    # エンコードしたもの)が来て0x00でターミネートされる。この0x00を含んで
    # 0x00までの部分が必要。これがrrsig_part。
    rrsig_part = rrsig_rdata_wire[:rrsig_rdata_wire.find(0x00, 18)+1]
    if False:
        print(f'rrsig_part: {rrsig_part}')
    
    # DNSKEY_ZSK_1_RRの全体をon wireな形で取り出す。
    # 途中のリゾルバがTTLを減算している場合があるのでRRSIGのoriginal_ttlで
    # 上書きしておく。
    with io.BytesIO() as wire:
        x = dnskey_zsk_1_rdset
        x.ttl = rrsig_dnskey_1_rdset[0].original_ttl
        x.to_wire(dnskey_zsk_1_owner, wire)
        dnskey_part = wire.getvalue()
    if False:
        print(f'dnskey_part: {dnskey_part}')

    # rrsig_partとdnskey_partを連結したもののSHA256ハッシュを取る。
    # これが(2)のハッシュ値。
    rrsig_dnskey_hash = hashlib.sha256(rrsig_part + dnskey_part).hexdigest()
    if True:
        print(f'ハッシュ値(2): {rrsig_a_hash}')

    # (1)と(2)のハッシュ値が一致していれば、検証成功。
    if True:
        if rrhash == rrsig_dnskey_hash:
            print('(1)と(2)のハッシュ値が一致したので検証成功。')
        else:
            print('(1)と(2)のハッシュ値が一致しなかったので検証失敗。')

    # DNSKEY_ZSK_1_RRの署名検証は諦めて、DNSKEY_KSK_RRの検証に移る。
    # DNSKEY_KSK_RRには上位ドメイン名にDS_RRがあってそこにハッシュ値が
    # 掲載されている。
    print('### DNSKEY_KSK_RR の検証 ###')

    # DS_RRに掲載されているDNSKEY_KSK_RRのハッシュ値
    ds_hash = ds_rdset[0].digest.hex()
    if False:
        print(f'DS_RRのkey_tag:     {ds_rdset[0].key_tag}')
        print(f'DS_RRのalgorithm:   {dns.dnssec.algorithm_to_text(ds_rdset[0].algorithm)}')
        print(f'DS_RRのdigest_type: {ds_rdset[0].digest_type}')
        print(f'DS_RRのdigest:      {ds_hash}')

    # DNSKEY_KSK_RRのowner, flags, protocol, algorithm, keyをon wireの
    # 形式で並べたものをdigest_type=2 (SHA256)でハッシュ値を取る。
    ksk_hash_target = b''.join([dnskey_ksk_owner.to_wire()
                              ,dnskey_ksk_rdset[0].flags.to_bytes(2, 'big')
                              ,dnskey_ksk_rdset[0].protocol.to_bytes(1, 'big')
                              ,dnskey_ksk_rdset[0].algorithm.to_bytes(1, 'big')
                              ,dnskey_ksk_rdset[0].key])
    ksk_hash = hashlib.sha256(ksk_hash_target).hexdigest()
    if False:
        print(f'KSK hash target: {ksk_hash_target}')
        print(f'KSK hash: {ksk_hash}')

    if ds_hash == ksk_hash:
        print('DSとKSKのハッシュ値が一致したので検証成功。')
    else:
        print('DSとKSKのハッシュ値が一致しなかったので検証失敗。')

    # これでDS_RRを信用するなら、DNSKEY_KSK_RRを信用できることがわかった。








