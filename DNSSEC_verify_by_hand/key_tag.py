#!/usr/bin/env python3

import sys
import base64

def keytag(flag: int, protocol: int, algorithm: int, b64_data: str):
    '''DNSKEY RRに対するキータグを計算する。

    DNSKEYのRDATAが
        flag protocol algorithm b64_data
    の時、
      - flag, protocol, algorithmを(文字列から変換して)整数として扱い、
      - b64_dataのところはアルゴリズムによって形が変わり、
        空白文字でいくつかに区切られる場合があるのでその場合は単純に連結したものを
        この関数の入力とする。
    そして、この順にバイト列に並べて、先頭から1バイトずつ取り出して、
    Pythonの配列の指定でインデックスが偶数なら上位バイト、奇数なら下位バイトに
    加えていく。2バイトずつ取り出してタグへ足し合わせる(末尾で1バイト不足する場合は
    0でパディング)のと同じ。
    上位バイトのさらに上位へ溢れる桁上がりのキャリーは最後に2バイト整数内へ戻す。
    結果として、2バイトの整数ができる。

    なお、DNSKEY RRに対するキータグの計算の方法はRFC 4034にC言語のものが定義されており、
    それをPythonで実装したものが https://eng-blog.iij.ad.jp/archives/7689 に掲載されている。
    本スクリプトはそれを元に改変したものである。
    '''

    # flagは2バイトの整数。2バイト取り出して2バイトのtag変数へ収めるから、代入と同じ。
    tag = flag

    # protocolとalgorithmは1バイトの整数。前者をtagの上位バイトへ、後者を下位バイトへ足し合わせる。
    tag += (protocol << 8)
    tag += algorithm

    # b64_dataはBASE64で符号化されているので、それを戻す。
    data = base64.b64decode(b64_data)

    # dataの先頭から1バイト取り出して
    for i in range(len(data)):
        # そのインデックス番号が偶数なら上位バイトへ足し合わせる。
        if i % 2 == 0:
            tag += (data[i] << 8)
        # 奇数なら下位バイトへ足し合わせる。
        else:
            tag += data[i]

    # 2バイトの上位側へ溢れたキャリーを2バイト内へ戻して足し合わせる。
    tag += (tag >> 16) & 0xFFFF

    # タグの2バイトの部分だけを取り出す。
    tag &= 0xFFFF

    # これがRFC4034付録で定義されるキータグ
    return tag

if __name__ == '__main__':

    import argparse

    p = argparse.ArgumentParser(description='RFC4034付録に定義されたキータグの計算を行う。')
    p.add_argument('flag', type=int, help='DNSKEY RDATAの最初の項であるflag')
    p.add_argument('protocol', type=int, help='DNSKEY RDATAの2番目の項であるprotocol')
    p.add_argument('algorithm', type=int, help='DNSKEY RDATAの3番目最初の項であるalgorithm')
    p.add_argument('b64_data', nargs='+', help='DNSKEY RDATAの残りの項であるb64_data')

    args = p.parse_args()
    #print(args)

    tag = keytag(args.flag, args.protocol, args.algorithm, ''.join(args.b64_data))
    print(tag)
