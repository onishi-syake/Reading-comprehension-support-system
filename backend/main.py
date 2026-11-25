from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import os
import time
import asyncio
from dotenv import load_dotenv
from openai import AsyncOpenAI

from services.pdf_processor import DocumentProcessor
from services.knowledge_estimator import KnowledgeEstimator
from services.prerequisite_generator import PrerequisiteGenerator
from services.knowledge_graph_logger import KnowledgeGraphLogger
from services.comparison_generator import ComparisonGenerator

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
SESSION_EXPIRED_MESSAGE = "セッションが切れました。お手数ですが、最初からやり直してください。"
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

class ChatData(BaseModel):
    session_id: str
    message: str

class ComparisonData(BaseModel):
    session_id: str
    task: str  # "simplify"（平易化）または "summarize"（要約）

@app.get("/")
async def root():
    return {"message": "読解支援システムAPI"}

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
            "fundamental_concepts": [],
            "checked_concepts": set(),
            "pending_tasks": []
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
            raise HTTPException(status_code=404, detail=SESSION_EXPIRED_MESSAGE)

        estimator = KnowledgeEstimator()
        concepts_dict = await estimator.extract_main_concepts(session["pdf_content"])

        session["current_concepts"] = concepts_dict
        session["concept_supplements"].update(concepts_dict)

        # 主要概念の深さを1に設定
        for concept in concepts_dict:
            session["concept_depth"][concept] = 1

        return {"concepts": list(concepts_dict.keys())}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"概念抽出エラー: {str(e)}")

async def generate_prerequisites_in_background(session_id: str, concept: str):
    """理解されなかった概念の前提概念をバックグラウンドで生成する"""
    session = sessions.get(session_id)
    if not session:
        return
    try:
        estimator = KnowledgeEstimator()
        prerequisites = await estimator.update_knowledge_graph(
            concept,
            session["knowledge_graph"],
            session["pdf_content"],
            session["user_knowledge"],
            session["concept_supplements"],
            session["concept_depth"]
        )
        kg_logger.log_graph_update(
            session_id,
            concept,
            prerequisites if prerequisites else [],
            action="add_prerequisites"
        )

        # 生成した前提概念の基礎概念判定も先にバックグラウンドで済ませておく
        # （質問取得時のLLM待ちをなくすため）
        checked = session.setdefault("checked_concepts", set())
        for prereq in prerequisites:
            normalized = estimator.normalizer.normalize_text(prereq)
            if normalized in checked:
                continue
            checked.add(normalized)
            if await estimator.is_fundamental(prereq):
                session["fundamental_concepts"].append(normalized)
    except Exception as e:
        print(f"前提概念生成エラー (concept={concept}): {e}")


async def wait_for_pending_prerequisites(session: dict):
    """進行中の前提概念生成がすべて完了するまで待機する"""
    tasks = session.get("pending_tasks", [])
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
        session["pending_tasks"] = []


@app.post("/get-next-question")
async def get_next_question(data: SessionData):
    """次の知識確認質問を取得"""
    try:
        session = sessions.get(data.session_id)
        if not session:
            raise HTTPException(status_code=404, detail=SESSION_EXPIRED_MESSAGE)

        estimator = KnowledgeEstimator()

        # まず現時点で回答可能な質問を探す（バックグラウンド生成を待たない）。
        # 主要概念や、生成済みの前提概念が残っていれば即座に返せる。
        question = await estimator.get_next_prerequisite_question(
            session["current_concepts"],
            session["knowledge_graph"],
            session["user_knowledge"],
            session["concept_supplements"],
            session["fundamental_concepts"],
            session.setdefault("checked_concepts", set())
        )

        # 回答可能な質問が無く、かつ前提概念生成が進行中の場合のみ、
        # その完了を待ってから再度探索する
        while question is None and session.get("pending_tasks"):
            await wait_for_pending_prerequisites(session)
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

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"質問生成エラー: {str(e)}")

@app.post("/answer-concept")
async def answer_concept(data: AnswerConceptData):
    """ユーザーの知識回答を記録"""
    try:
        session = sessions.get(data.session_id)
        if not session:
            raise HTTPException(status_code=404, detail=SESSION_EXPIRED_MESSAGE)

        # ユーザーの知識を記録
        session["user_knowledge"].append({
            "concept": data.concept,
            "understands": data.understands
        })

        # 理解していない場合、前提知識の探索をバックグラウンドで開始し、
        # 生成の完了を待たずに即座にレスポンスを返す
        if not data.understands:
            task = asyncio.create_task(
                generate_prerequisites_in_background(data.session_id, data.concept)
            )
            session.setdefault("pending_tasks", []).append(task)

        return {"message": "回答を記録しました"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"回答記録エラー: {str(e)}")

@app.post("/generate-prerequisite-text")
async def generate_prerequisite_text(data: SessionData):
    """前提知識文を生成"""
    try:
        session = sessions.get(data.session_id)
        if not session:
            raise HTTPException(status_code=404, detail=SESSION_EXPIRED_MESSAGE)

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

        # セッションに前提知識文を保存（チャットボットで使用）
        session["prerequisite_text"] = prerequisite_text
        session["chat_history"] = []

        return {"prerequisite_text": prerequisite_text}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"前提文生成エラー: {str(e)}")

@app.post("/generate-comparison-text")
async def generate_comparison_text(data: ComparisonData):
    """比較手法（平易化・要約）の文章を生成"""
    try:
        session = sessions.get(data.session_id)
        if not session:
            raise HTTPException(status_code=404, detail=SESSION_EXPIRED_MESSAGE)

        if data.task not in ("simplify", "summarize"):
            raise HTTPException(status_code=400, detail=f"未対応の処理です: {data.task}")

        generator = ComparisonGenerator()
        text = await generator.generate_text(data.task, session["pdf_content"])
        print(f"比較手法の生成 (task={data.task}): 入力 {len(session['pdf_content'])}文字 → 出力 {len(text)}文字")

        return {"text": text}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成エラー: {str(e)}")

CHAT_MAX_HISTORY = 20  # 直近10往復分
# 他のモジュールと同じく、安全のため30万文字（約60kトークン）を上限とする
CHAT_PAPER_MAX_CHARS = 300000

@app.post("/chat")
async def chat(data: ChatData):
    """前提知識文に関するチャット対話"""
    try:
        session = sessions.get(data.session_id)
        if not session:
            raise HTTPException(status_code=404, detail=SESSION_EXPIRED_MESSAGE)

        prerequisite_text = session.get("prerequisite_text", "")
        if not prerequisite_text:
            raise HTTPException(status_code=400, detail="前提知識文がまだ生成されていません")

        # 知識グラフから理解していない概念を取得
        unknown_concepts = [
            entry["concept"] for entry in session.get("user_knowledge", [])
            if not entry["understands"]
        ]

        system_prompt = (
            "あなたは情報科学論文の読解を支援するアシスタントです。\n"
            "以下の前提知識文と論文本文を参考にして、ユーザーの質問にわかりやすく回答してください。\n"
            "回答は簡潔にしつつ、必要に応じて具体例を交えて説明してください。\n"
            "前提知識文や論文の範囲を大きく超える質問には、範囲外であることを伝えてください。\n\n"
            f"【前提知識文】\n{prerequisite_text}\n\n"
            f"【ユーザーが理解していない概念】\n{', '.join(unknown_concepts) if unknown_concepts else 'なし'}\n\n"
            f"【論文本文（参考）】\n{session['pdf_content'][:CHAT_PAPER_MAX_CHARS]}"
        )

        # 会話履歴を構築
        messages = [{"role": "system", "content": system_prompt}]
        for entry in session.get("chat_history", [])[-CHAT_MAX_HISTORY:]:
            messages.append(entry)
        messages.append({"role": "user", "content": data.message})

        # LLM呼び出し
        client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = await client.chat.completions.create(
            model="gpt-5.2",
            messages=messages,
            temperature=0.7,
            max_completion_tokens=1000,
        )
        reply = response.choices[0].message.content.strip()

        # 会話履歴を保存
        session["chat_history"].append({"role": "user", "content": data.message})
        session["chat_history"].append({"role": "assistant", "content": reply})

        # 履歴が上限を超えたら古いものを削除
        if len(session["chat_history"]) > CHAT_MAX_HISTORY:
            session["chat_history"] = session["chat_history"][-CHAT_MAX_HISTORY:]

        return {"reply": reply}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"チャットエラー: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
