from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import os
import time
from dotenv import load_dotenv

from services.pdf_processor import DocumentProcessor
from services.knowledge_estimator import KnowledgeEstimator
from services.prerequisite_generator import PrerequisiteGenerator
from services.knowledge_graph_logger import KnowledgeGraphLogger

load_dotenv()

app = FastAPI(title="読解支援システム")

# CORS設定（フロントエンドとの通信用）
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:3001").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# グローバルセッションストレージ（本番環境ではRedisなど使用）
SESSION_TTL = 86400  # 24時間（秒）
sessions: Dict[str, dict] = {}

def cleanup_expired_sessions():
    """期限切れセッションを削除"""
    now = time.time()
    expired = [sid for sid, s in sessions.items() if now - s.get("created_at", 0) > SESSION_TTL]
    for sid in expired:
        del sessions[sid]

# 知識グラフロガーのインスタンス
kg_logger = KnowledgeGraphLogger()

class SessionData(BaseModel):
    session_id: str

class AnswerConceptData(BaseModel):
    session_id: str
    concept: str
    understands: bool

@app.get("/")
async def root():
    return {"message": "読解支援システムAPI", "allowed_origins": ALLOWED_ORIGINS}

@app.post("/upload-file")
async def upload_file(file: UploadFile = File(...)):
    """PDF or Wordファイルをアップロードし、セッションIDを返す"""
    try:
        processor = DocumentProcessor()

        # ファイル形式チェック
        import os
        ext = os.path.splitext(file.filename or "")[1].lower()
        if ext not in DocumentProcessor.SUPPORTED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"未対応のファイル形式です。対応形式: {', '.join(DocumentProcessor.SUPPORTED_EXTENSIONS)}"
            )

        result = await processor.extract_text(file)

        # セッションIDを生成
        import uuid
        session_id = str(uuid.uuid4())

        # 期限切れセッションを削除
        cleanup_expired_sessions()

        # セッションにデータを保存
        sessions[session_id] = {
            "created_at": time.time(),
            "pdf_content": result["text"],
            "current_concepts": {},
            "concept_supplements": {},
            "knowledge_graph": {},
            "user_knowledge": [],
            "concept_depth": {},
            "fundamental_concepts": []
        }

        message = "ファイルアップロード成功"
        if result["method"] == "ocr":
            message = "PDFに埋め込みテキストが見つからなかったため、OCRで文字認識を行いました。精度が低い場合があります。"

        return {"session_id": session_id, "message": message, "method": result["method"]}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ファイル処理エラー: {str(e)}")

@app.post("/extract-concepts")
async def extract_concepts(data: SessionData):
    """論文から専門概念を抽出"""
    try:
        session = sessions.get(data.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="セッションが見つかりません")

        estimator = KnowledgeEstimator()
        concepts_dict = await estimator.extract_main_concepts(session["pdf_content"])

        session["current_concepts"] = concepts_dict
        session["concept_supplements"].update(concepts_dict)

        # 主要概念の深さを1に設定
        for concept in concepts_dict:
            session["concept_depth"][concept] = 1

        return {"concepts": list(concepts_dict.keys())}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"概念抽出エラー: {str(e)}")

@app.post("/get-next-question")
async def get_next_question(data: SessionData):
    """次の知識確認質問を取得"""
    try:
        session = sessions.get(data.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="セッションが見つかりません")

        estimator = KnowledgeEstimator()
        question = await estimator.get_next_prerequisite_question(
            session["current_concepts"],
            session["knowledge_graph"],
            session["user_knowledge"],
            session["concept_supplements"],
            session["fundamental_concepts"]
        )

        if question is None:
            return {"finished": True, "question": None}

        return {"finished": False, "question": question}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"質問生成エラー: {str(e)}")

@app.post("/answer-concept")
async def answer_concept(data: AnswerConceptData):
    """ユーザーの知識回答を記録"""
    try:
        session = sessions.get(data.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="セッションが見つかりません")

        # ユーザーの知識を記録
        session["user_knowledge"].append({
            "concept": data.concept,
            "understands": data.understands
        })

        # 理解していない場合、さらに前提知識を探索
        estimator = KnowledgeEstimator()
        if not data.understands:
            prerequisites = await estimator.update_knowledge_graph(
                data.concept,
                session["knowledge_graph"],
                session["pdf_content"],
                session["user_knowledge"],
                session["concept_supplements"],
                session["concept_depth"]
            )

            # 知識グラフの更新をログに記録
            kg_logger.log_graph_update(
                data.session_id,
                data.concept,
                prerequisites if prerequisites else [],
                action="add_prerequisites"
            )

        return {"message": "回答を記録しました"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"回答記録エラー: {str(e)}")

@app.post("/generate-prerequisite-text")
async def generate_prerequisite_text(data: SessionData):
    """前提知識文を生成"""
    try:
        session = sessions.get(data.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="セッションが見つかりません")

        generator = PrerequisiteGenerator()
        prerequisite_text = await generator.generate_text(
            session["knowledge_graph"],
            session["user_knowledge"],
            session["pdf_content"]
        )

        # 知識グラフを最終的なログファイルとして保存
        log_filepath = kg_logger.save_knowledge_graph(
            data.session_id,
            session["knowledge_graph"],
            session["user_knowledge"],
            metadata={
                "prerequisite_text_generated": True,
                "text_length": len(prerequisite_text)
            }
        )
        print(f"Knowledge graph saved to: {log_filepath}")

        return {"prerequisite_text": prerequisite_text}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"前提文生成エラー: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
