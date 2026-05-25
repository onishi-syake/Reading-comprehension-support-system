# 読解支援システム

情報科学論文の理解を支援するWebアプリケーション

## システム構成

- **バックエンド**: FastAPI (Python)
- **フロントエンド**: Next.js (TypeScript) + TailwindCSS
- **LLM**: OpenAI GPT-4

## 機能

1. **PDF入力**: 論文PDFをアップロード
2. **知識情報推定**: 読者の知識レベルを再帰的に推定（RPKTベース）
3. **前提知識生成**: 読者に合わせた前提知識文を自動生成

## セットアップ

### 前提条件

- Python 3.9以上
- Node.js 18以上
- OpenAI APIキー

### インストール手順

#### 1. バックエンドのセットアップ

```bash
cd backend

# 仮想環境の作成（推奨）
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 依存パッケージのインストール
pip install -r requirements.txt

# 環境変数の設定
cp .env.example .env
# .envファイルを開いて、OPENAI_API_KEYを設定してください
```

#### 2. フロントエンドのセットアップ

```bash
cd frontend

# 依存パッケージのインストール
npm install

# 環境変数の設定（オプション）
# デフォルトではhttp://localhost:8000をバックエンドとして使用
```

## 起動方法

### バックエンドの起動

```bash
cd backend
source venv/bin/activate  # 仮想環境がある場合
python main.py
```

バックエンドは `http://localhost:8000` で起動します。

### フロントエンドの起動

別のターミナルで:

```bash
cd frontend
npm run dev
```

フロントエンドは `http://localhost:3000` で起動します。

## 使い方

1. ブラウザで `http://localhost:3000` を開く
2. 論文PDFをアップロード
3. 表示される概念について、理解しているかを回答
4. 生成された前提知識文を確認

## プロジェクト構造

```
.
├── backend/
│   ├── main.py                 # FastAPI アプリケーション
│   ├── requirements.txt        # Python依存パッケージ
│   ├── .env.example           # 環境変数テンプレート
│   └── services/
│       ├── pdf_processor.py        # PDF処理
│       ├── knowledge_estimator.py  # 知識推定（RPKT）
│       └── prerequisite_generator.py # 前提知識生成
│
└── frontend/
    ├── app/
    │   ├── page.tsx           # メインページ
    │   ├── layout.tsx         # レイアウト
    │   └── globals.css        # グローバルスタイル
    ├── components/
    │   ├── PDFUpload.tsx             # PDFアップロードUI
    │   ├── KnowledgeAssessment.tsx   # 知識確認UI
    │   └── PrerequisiteText.tsx      # 前提文表示UI
    ├── lib/
    │   └── api.ts             # APIクライアント
    └── package.json

```

## API エンドポイント

- `POST /upload-pdf`: PDFアップロード
- `POST /extract-concepts`: 概念抽出
- `POST /get-next-question`: 次の質問取得
- `POST /answer-concept`: 知識回答
- `POST /generate-prerequisite-text`: 前提文生成

## 今後の改善点

- [ ] 知識抽出の高速化
- [ ] 複数概念の並列処理
- [ ] セッション管理の永続化（Redis等）
- [ ] ユーザー認証機能
- [ ] 前提文の品質評価機能
- [ ] 比較手法の実装（要約、ChatGPT等）

## ライセンス

研究用途
