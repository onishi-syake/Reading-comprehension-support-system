"""
PDF構造の診断スクリプト
署名テキストがどのオブジェクトとして格納されているか調査する

使い方:
    python tests/diagnose_pdf.py <PDFファイルパス>
"""

import pdfplumber
import sys
import os


def main():
    if len(sys.argv) < 2:
        print("使い方: python tests/diagnose_pdf.py <PDFファイルパス>")
        sys.exit(1)

    pdf_path = sys.argv[1]

    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[0]

        # 1. 注釈情報
        print("=" * 60)
        print("【1. page.annots（注釈オブジェクト）】")
        print("=" * 60)
        annots = page.annots or []
        if annots:
            for i, annot in enumerate(annots):
                print(f"\n  annot[{i}]:")
                for key, val in annot.items():
                    print(f"    {key}: {val}")
        else:
            print("  注釈なし")

        # 2. 署名テキスト周辺の文字属性
        print(f"\n{'=' * 60}")
        print("【2. 先頭50文字の属性（font, size, 座標）】")
        print("=" * 60)
        chars = page.chars
        for c in chars[:50]:
            print(f"  文字: {c['text']:>2}  font: {c.get('fontname','?'):30}  "
                  f"size: {c.get('size',0):5.1f}  "
                  f"top: {c.get('top',0):6.1f}  left: {c.get('x0',0):6.1f}")

        # 3. フォント一覧（どんなフォントが使われているか）
        print(f"\n{'=' * 60}")
        print("【3. ページ内の全フォント一覧】")
        print("=" * 60)
        fonts = {}
        for c in chars:
            key = (c.get('fontname', '?'), round(c.get('size', 0), 1))
            if key not in fonts:
                fonts[key] = {"count": 0, "sample": ""}
            fonts[key]["count"] += 1
            if len(fonts[key]["sample"]) < 20:
                fonts[key]["sample"] += c['text']

        for (fname, fsize), info in sorted(fonts.items(), key=lambda x: -x[1]["count"]):
            print(f"  {fname}  size={fsize}  使用数={info['count']}  例: {info['sample']}")

        # 4. ページのオブジェクトタイプ一覧
        print(f"\n{'=' * 60}")
        print("【4. ページ内オブジェクトタイプ】")
        print("=" * 60)
        for obj_type, objs in page.objects.items():
            print(f"  {obj_type}: {len(objs)}個")


if __name__ == "__main__":
    main()
