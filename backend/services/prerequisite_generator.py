from openai import OpenAI
from typing import List, Dict
import os

class PrerequisiteGenerator:
    """前提知識生成システム"""

    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = "gpt-5.2"

    async def generate_text(
        self,
        knowledge_graph: Dict,
        user_knowledge: List[Dict],
        paper_content: str
    ) -> str:
        """
        前提知識文を生成

        Args:
            knowledge_graph: 構築された知識グラフ
            user_knowledge: ユーザーの知識回答
            paper_content: 論文内容

        Returns:
            生成された前提知識文
        """
        try:
            # ユーザーが理解していない概念を抽出
            unknown_concepts = [
                item["concept"]
                for item in user_knowledge
                if not item["understands"]
            ]

            if not unknown_concepts:
                return "すべての概念を理解されているようです。前提知識の補足は不要です。"

            # 知識グラフから前提関係を整理
            prerequisite_structure = self._build_prerequisite_structure(
                unknown_concepts,
                knowledge_graph
            )

            # GPT-4のトークン制限を考慮（約128k tokens = 約40-50万文字）
            # 安全のため30万文字（約60kトークン）を上限とする
            max_chars = 300000

            if len(paper_content) > max_chars:
                print(f"警告: 論文が{len(paper_content)}文字あるため、前提知識生成用に{max_chars}文字に切り詰めました")
                paper_content_to_use = paper_content[:max_chars]
            else:
                paper_content_to_use = paper_content
                print(f"前提知識生成: 論文全文を使用 ({len(paper_content)}文字)")

            prompt = f"""
以下の情報を元に、論文を理解するための前提知識を説明する文章を生成してください。

【読者が理解していない概念】
{', '.join(unknown_concepts)}

【概念間の前提関係】
{prerequisite_structure}

【論文全文（コンテキスト）】
{paper_content_to_use}

要件:
1. 読者が理解している基礎的な知識から始めて、段階的に説明する
2. 各概念を平易な言葉で解説する
3. 概念間のつながりを明確にする
4. 最終的に論文の内容理解に繋がるように構成する
5. 1000〜1500文字程度でまとめる

前提知識文を生成してください。
"""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "あなたは教育的な説明が得意な技術ライターです。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                max_completion_tokens=2000
            )

            prerequisite_text = response.choices[0].message.content.strip()

            return prerequisite_text

        except Exception as e:
            raise Exception(f"前提文生成エラー: {str(e)}")

    def _build_prerequisite_structure(
        self,
        unknown_concepts: List[str],
        knowledge_graph: Dict
    ) -> str:
        """
        前提関係の構造を文字列化

        Args:
            unknown_concepts: 理解していない概念リスト
            knowledge_graph: 知識グラフ

        Returns:
            構造化された前提関係の説明
        """
        structure_lines = []

        for concept in unknown_concepts:
            if concept in knowledge_graph:
                prerequisites = knowledge_graph[concept]
                structure_lines.append(f"「{concept}」を理解するには:")
                for prereq in prerequisites:
                    structure_lines.append(f"  - {prereq}")

        return "\n".join(structure_lines) if structure_lines else "前提関係の情報なし"
