from openai import OpenAI
from typing import List, Dict, Optional
import os
import json
import re
from .concept_normalizer import ConceptNormalizer

class KnowledgeEstimator:
    """知識情報推定システム（RPKTベース）"""

    MAX_DEPTH = 3

    MAX_RETRIES = 3

    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = "gpt-5.2"
        self.normalizer = ConceptNormalizer()

    def _extract_json(self, text: str) -> dict | list:
        """
        LLMの応答テキストからJSONを抽出してパースする

        Args:
            text: LLMの応答テキスト

        Returns:
            パースされたJSONオブジェクト

        Raises:
            ValueError: JSONの抽出・パースに失敗した場合
        """
        # そのままパースを試行
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # マークダウンのコードブロックを除去して試行
        code_block = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
        if code_block:
            try:
                return json.loads(code_block.group(1))
            except json.JSONDecodeError:
                pass

        # テキスト中の最初の { } または [ ] を抽出して試行
        brace_match = re.search(r'\{[\s\S]*\}', text)
        if brace_match:
            try:
                return json.loads(brace_match.group())
            except json.JSONDecodeError:
                pass

        bracket_match = re.search(r'\[[\s\S]*\]', text)
        if bracket_match:
            try:
                return json.loads(bracket_match.group())
            except json.JSONDecodeError:
                pass

        raise ValueError(f"JSONの抽出に失敗しました: {text[:200]}")

    def _call_llm_with_retry(self, messages: list, temperature: float = 0, max_tokens: int = None) -> str:
        """
        LLMを呼び出し、失敗時にリトライする

        Args:
            messages: チャットメッセージのリスト
            temperature: 温度パラメータ
            max_tokens: 最大トークン数

        Returns:
            LLMの応答テキスト
        """
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens:
            kwargs["max_completion_tokens"] = max_tokens

        last_error = None
        for attempt in range(self.MAX_RETRIES):
            try:
                response = self.client.chat.completions.create(**kwargs)
                return response.choices[0].message.content.strip()
            except Exception as e:
                last_error = e
                print(f"LLM呼び出しエラー (試行 {attempt + 1}/{self.MAX_RETRIES}): {e}")

        raise Exception(f"LLM呼び出しが{self.MAX_RETRIES}回失敗しました: {last_error}")

    def _call_llm_json_with_retry(self, messages: list, temperature: float = 0) -> dict | list:
        """
        LLMを呼び出してJSON応答を取得する。パース失敗時もリトライする

        Args:
            messages: チャットメッセージのリスト
            temperature: 温度パラメータ

        Returns:
            パースされたJSONオブジェクト
        """
        last_error = None
        for attempt in range(self.MAX_RETRIES):
            try:
                response_text = self._call_llm_with_retry(messages, temperature)
                return self._extract_json(response_text)
            except ValueError as e:
                last_error = e
                print(f"JSONパースエラー (試行 {attempt + 1}/{self.MAX_RETRIES}): {e}")

        raise Exception(f"JSON応答の取得が{self.MAX_RETRIES}回失敗しました: {last_error}")

    async def is_fundamental(self, concept: str) -> bool:
        """
        概念が基礎的で前提知識の確認が不要かを判定

        Args:
            concept: 判定する概念

        Returns:
            基礎的な概念であればTrue
        """
        try:
            prompt = f"""
「{concept}」という概念は、一般的な高校卒業程度の知識で理解できる基礎的な概念ですか？
専門的な学習を必要とせず、日常生活や一般教育の中で自然に身につく知識かどうかを判定してください。

「はい」または「いいえ」のみで回答してください。
"""
            answer = self._call_llm_with_retry(
                [
                    {"role": "system", "content": "あなたは教育専門家です。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                max_tokens=10
            )
            return "はい" in answer

        except Exception:
            return False

    async def extract_main_concepts(self, paper_content: str) -> Dict[str, str]:
        """
        論文から主要な専門概念を抽出

        Args:
            paper_content: 論文のテキスト内容

        Returns:
            {概念名: 補足情報} のディクショナリ（補足不要なら空文字列）
        """
        try:
            # GPT-4のトークン制限を考慮（約128k tokens = 約40-50万文字）
            # 日本語は1文字約1.5-2トークンとして計算
            # 安全のため30万文字（約60kトークン）を上限とする
            max_chars = 300000

            if len(paper_content) > max_chars:
                print(f"警告: 論文が{len(paper_content)}文字あるため、{max_chars}文字に切り詰めました")
                paper_content_to_use = paper_content[:max_chars]
            else:
                paper_content_to_use = paper_content
                print(f"論文全文を使用: {len(paper_content)}文字")

            prompt = f"""
以下の論文全文から、理解するために必要な主要な専門概念を10〜15個抽出してください。
情報科学分野の論文で、一般読者が理解しにくいと思われる技術用語や概念を選んでください。
論文全体を通して重要な概念を選定してください。
必ず論文中に明示的に登場する用語のみを抽出してください。論文に書かれていない関連用語を推測して追加しないでください。

論文内容:
{paper_content_to_use}

出力はJSONオブジェクト形式で返してください。キーは概念名（単一の単語）、値は補足情報（概念名だけでは何を指すか特定しにくい場合に短い一般的な説明を付ける。不要なら空文字列）です。
補足情報には論文固有の内容や論文中の具体例を含めないでください。あくまで一般的な定義や説明にしてください。
例: {{"機械学習": "", "勾配降下法": "", "BLEU": "機械翻訳の評価指標"}}
不正な例: {{"機械学習とは、データから学習する方法です。": "", "ニューラルネットワーク（NN）": "", "モジュール": "システムを構成する機能単位（例：抽出・推定・生成）"}}
"""

            concepts_dict = self._call_llm_json_with_retry([
                {"role": "system", "content": "あなたは情報科学分野の専門家です。"},
                {"role": "user", "content": prompt}
            ])

            # 概念名の正規化（括弧内の説明を除去）
            normalized = {}
            for concept, supplement in concepts_dict.items():
                cleaned = re.sub(r'[（(][^）)]*[）)]', '', concept).strip()
                if cleaned:
                    normalized[cleaned] = supplement.strip() if supplement else ""

            return normalized

        except Exception as e:
            raise Exception(f"概念抽出エラー: {str(e)}")

    async def get_prerequisite_concepts(
        self,
        concept: str,
        context: str,
        existing_concepts: List[str] = None
    ) -> Dict[str, str]:
        """
        ある概念を理解するために必要な前提概念を取得（再帰的処理の基礎）

        Args:
            concept: 対象概念
            context: 論文のコンテキスト
            existing_concepts: 既に質問済みの概念リスト

        Returns:
            {前提概念名: 補足情報} のディクショナリ（重複除去済み）
        """
        try:
            existing_concepts = existing_concepts or []

            # 既出概念を含むプロンプト
            existing_text = ""
            if existing_concepts:
                existing_text = f"""
既に確認済みの概念（これらと重複しない概念のみを挙げてください）:
{', '.join(existing_concepts[:20])}  # 最大20個まで表示
"""

            prompt = f"""
「{concept}」という概念を理解するために必要な前提知識・概念を3個挙げてください。
より基礎的な概念から順に並べてください。
{existing_text}
注意事項:
- 同じ概念の異なる表現は避けてください
- 既出概念と重複や包含関係にあるものは除外してください
- できるだけ簡潔な表現を使用してください

コンテキスト（論文全文）:
{context}

出力はJSONオブジェクト形式で返してください。キーは概念名（単一の単語）、値は補足情報（概念名だけでは何を指すか特定しにくい場合に短い一般的な説明を付ける。不要なら空文字列）です。
補足情報には論文固有の内容や論文中の具体例を含めないでください。あくまで一般的な定義や説明にしてください。
例: {{"確率論": "", "線形代数": "", "TF-IDF": "単語の重要度を測る指標"}}
不正な例: {{"確率論の基礎": "", "統計学（Statistics）": ""}}
"""

            prerequisites_dict = self._call_llm_json_with_retry([
                {"role": "system", "content": "あなたは教育専門家です。"},
                {"role": "user", "content": prompt}
            ])

            # 概念名の正規化（括弧内の説明を除去）
            normalized = {}
            for prereq, supplement in prerequisites_dict.items():
                cleaned = re.sub(r'[（(][^）)]*[）)]', '', prereq).strip()
                if cleaned:
                    normalized[cleaned] = supplement.strip() if supplement else ""

            # 重複除去フィルタリング
            if existing_concepts:
                filtered_keys = self.normalizer.filter_duplicates(list(normalized.keys()), existing_concepts)
                normalized = {k: normalized[k] for k in filtered_keys}

            return normalized

        except Exception as e:
            raise Exception(f"前提概念抽出エラー: {str(e)}")

    async def get_next_prerequisite_question(
        self,
        current_concepts: Dict[str, str],
        knowledge_graph: Dict,
        user_knowledge: List[Dict],
        concept_supplements: Dict[str, str] = None,
        fundamental_concepts: list = None
    ) -> Optional[Dict]:
        """
        次に確認すべき知識質問を生成
        基礎概念と判定されたものはスキップする

        Args:
            current_concepts: {概念名: 補足情報} のディクショナリ
            knowledge_graph: 構築中の知識グラフ
            user_knowledge: ユーザーの回答履歴
            concept_supplements: 前提概念の補足情報
            fundamental_concepts: 基礎概念として判定済みの概念セット

        Returns:
            次の質問（conceptとdescriptionを含む辞書）、または終了時はNone
        """
        concept_supplements = concept_supplements or {}
        fundamental_concepts = fundamental_concepts if fundamental_concepts is not None else []

        # まだ質問していない概念を探す（正規化して比較）
        asked_concepts = set()
        for item in user_knowledge:
            normalized = self.normalizer.normalize_text(item["concept"])
            asked_concepts.add(normalized)

        # 現在の概念（主要概念）から未質問のものを探す（基礎判定なし）
        for concept, supplement in current_concepts.items():
            if self.normalizer.normalize_text(concept) not in asked_concepts:
                desc = f"「{concept}」という概念を理解していますか？"
                if supplement:
                    desc = f"「{concept}」（{supplement}）という概念を理解していますか？"
                return {"concept": concept, "description": desc}

        # 知識グラフ内の前提概念から未質問のものを探す（基礎判定あり）
        for parent, children in knowledge_graph.items():
            for child in children:
                normalized_child = self.normalizer.normalize_text(child)
                if normalized_child in asked_concepts:
                    continue
                if normalized_child in fundamental_concepts:
                    continue

                # 基礎概念か判定
                if await self.is_fundamental(child):
                    fundamental_concepts.append(normalized_child)
                    continue

                supplement = concept_supplements.get(child, "")
                desc = f"「{child}」という概念を理解していますか？（「{parent}」を理解するために必要）"
                if supplement:
                    desc = f"「{child}」（{supplement}）という概念を理解していますか？（「{parent}」を理解するために必要）"
                return {"concept": child, "description": desc}

        # すべて質問済みまたは基礎概念
        return None

    async def update_knowledge_graph(
        self,
        concept: str,
        knowledge_graph: Dict,
        paper_content: str,
        user_knowledge: List[Dict] = None,
        concept_supplements: Dict[str, str] = None,
        concept_depth: Dict[str, int] = None
    ) -> List[str]:
        """
        知識グラフを更新（ユーザーが理解していない概念の前提を追加）
        深さ制限（MAX_DEPTH）を超えた場合は前提概念を追加しない

        Args:
            concept: 理解していない概念
            knowledge_graph: 知識グラフ
            paper_content: 論文内容
            user_knowledge: ユーザーの回答履歴（重複チェック用）
            concept_supplements: 補足情報を格納するディクショナリ（更新される）
            concept_depth: 各概念の深さを記録するディクショナリ

        Returns:
            追加された前提概念のリスト
        """
        if concept_supplements is None:
            concept_supplements = {}
        if concept_depth is None:
            concept_depth = {}

        # 深さ制限チェック
        current_depth = concept_depth.get(concept, 1)
        if current_depth >= self.MAX_DEPTH:
            return []

        if concept not in knowledge_graph:
            # 既出概念リストを作成
            existing_concepts = []
            if user_knowledge:
                existing_concepts = [item["concept"] for item in user_knowledge]

            # 知識グラフ内の全概念も追加
            for parent_concept, children in knowledge_graph.items():
                existing_concepts.append(parent_concept)
                existing_concepts.extend(children)

            # 重複を除去
            existing_concepts = list(set(existing_concepts))

            # 前提概念を取得（既出概念を考慮）
            prerequisites_dict = await self.get_prerequisite_concepts(
                concept,
                paper_content,
                existing_concepts
            )

            # 補足情報を保存
            concept_supplements.update(prerequisites_dict)

            prerequisites = list(prerequisites_dict.keys())
            knowledge_graph[concept] = prerequisites

            # 前提概念の深さを記録（親の深さ + 1）
            for prereq in prerequisites:
                concept_depth[prereq] = current_depth + 1

            return prerequisites
        return []
