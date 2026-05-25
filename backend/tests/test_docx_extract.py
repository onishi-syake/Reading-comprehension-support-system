"""
Wordファイルテキスト抽出の精度確認スクリプト
pdf_processor.pyのDocumentProcessor.extract_text()と同じフローを再現する

使い方:
    python tests/test_docx_extract.py <Wordファイルパス>

出力:
    - LLMが受け取るテキスト
    - 使用された抽出方法
    - 抽出結果を extracted_output_docx.txt に保存
"""

import asyncio
import sys
import os
from fastapi import UploadFile
from io import BytesIO

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.pdf_processor import DocumentProcessor


class FakeUploadFile:
    """ローカルファイルをUploadFileとして扱うためのラッパー"""
    def __init__(self, filepath: str):
        self.filename = os.path.basename(filepath)
        with open(filepath, "rb") as f:
            self._content = f.read()

    async def read(self):
        return self._content


async def main():
    if len(sys.argv) < 2:
        print("使い方: python tests/test_docx_extract.py <Wordファイルパス>")
        sys.exit(1)

    docx_path = sys.argv[1]
    if not os.path.exists(docx_path):
        print(f"エラー: ファイルが見つかりません: {docx_path}")
        sys.exit(1)

    processor = DocumentProcessor()
    fake_file = FakeUploadFile(docx_path)
    result = await processor.extract_text(fake_file)

    print(f"ファイル: {docx_path}")
    print(f"抽出方法: {result['method']}")
    print(f"文字数: {len(result['text'])}")
    print("=" * 60)
    print(result["text"])

    # --- ファイルに保存 ---
    output_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(output_dir, "extracted_output_docx.txt")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(result["text"])

    print(f"\n{'=' * 60}")
    print(f"結果を保存しました: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
