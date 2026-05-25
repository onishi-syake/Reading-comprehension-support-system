"""
PDFテキスト抽出の精度確認スクリプト
pdf_processor.pyと同じ処理を再現し、LLMが受け取るテキストを出力する

使い方:
    python tests/test_pdf_extract.py <PDFファイルパス>

出力:
    - 使用された抽出方法（pdfplumber or OCR）
    - LLMが受け取るテキスト（clean_text適用済み）
    - 抽出結果を extracted_output.txt に保存
"""

import pdfplumber
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.pdf_processor import PDFProcessor


def extract_like_pdf_processor(pdf_path: str) -> dict:
    """pdf_processor.pyのextract_textと同じ処理を再現"""
    processor = PDFProcessor()

    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    # 1. pdfplumberでテキスト抽出を試行
    extracted_text = ""
    with pdfplumber.open(pdf_path) as pdf:
        page_count = len(pdf.pages)
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                extracted_text += text

    # 2. OCR判定
    if not processor._needs_ocr(extracted_text, page_count):
        return {
            "text": processor.clean_text(extracted_text),
            "method": "pdfplumber",
            "raw_text": extracted_text,
            "page_count": page_count,
        }

    # 3. OCRにフォールバック
    print("pdfplumberでのテキスト抽出が不十分なため、OCRを実行します...")
    ocr_text = processor._extract_with_ocr(pdf_bytes)
    return {
        "text": processor.clean_text(ocr_text),
        "method": "ocr",
        "raw_text": ocr_text,
        "page_count": page_count,
    }


def main():
    if len(sys.argv) < 2:
        print("使い方: python tests/test_pdf_extract.py <PDFファイルパス>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    if not os.path.exists(pdf_path):
        print(f"エラー: ファイルが見つかりません: {pdf_path}")
        sys.exit(1)

    result = extract_like_pdf_processor(pdf_path)

    print(f"ファイル: {pdf_path}")
    print(f"ページ数: {result['page_count']}")
    print(f"抽出方法: {result['method']}")
    print(f"生テキスト文字数: {len(result['raw_text'])}")
    print(f"クリーニング後文字数: {len(result['text'])}")
    print("=" * 60)
    print(result["text"])

    # --- ファイルに保存 ---
    output_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(output_dir, "extracted_output.txt")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(result["text"])

    print(f"\n{'=' * 60}")
    print(f"結果を保存しました: {output_path}")


if __name__ == "__main__":
    main()
