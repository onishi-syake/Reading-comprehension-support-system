from openai import AsyncOpenAI
import os

# 比較手法（平易化・要約）のプロンプト
# 提案手法の前提知識文と同じ形（system に役割、【】の見出し、「要件:」の番号付き箇条書き）にそろえている
SYSTEM_PROMPT = "あなたは教育的な説明が得意な技術ライターです。"

TASKS = {
    "simplify": {
        "instruction": "この論文を日本語で平易化してください。",
        "requirements": [
            "情報科学の論文を読み慣れていない大学生でも理解できるようにする",
            "元の文章の意味を保持する",
            "内容を省略せず、本文のすべての部分を平易化する",
            "本文以外のもの（参考文献、謝辞、著者略歴、ヘッダ、ページ番号など）は出力に含めない",
        ],
        "closing": "平易化した文章を生成してください。",
    },
    "summarize": {
        "instruction": "この論文を日本語で要約してください。",
        "requirements": [
            "情報科学の論文を読み慣れていない大学生でも理解できるようにする",
            "文章量を本文の30%程度にする",
            "元の文章の情報のみを使用し、それ以外の内容は生成しない",
            "本文以外のもの（参考文献、謝辞、著者略歴、ヘッダ、ページ番号など）は出力に含めない",
        ],
        "closing": "要約した文章を生成してください。",
    },
}


def build_user_prompt(task: str, paper_content: str) -> str:
    """平易化・要約のユーザメッセージを組み立てる"""
    spec = TASKS[task]
    requirements = "\n".join(
        f"{i}. {text}" for i, text in enumerate(spec["requirements"], start=1)
    )
    return (
        "以下の文章は、情報科学分野の学術論文です。\n"
        f"{spec['instruction']}\n\n"
        "【論文全文】\n"
        f"{paper_content}\n\n"
        "要件:\n"
        f"{requirements}\n\n"
        f"{spec['closing']}"
    )


class ComparisonGenerator:
    """比較手法（平易化・要約）の文章を生成する"""

    def __init__(self):
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        # 提案手法の前提知識文と同じモデル
        self.model = "gpt-5.2"

    async def generate_text(self, task: str, paper_content: str) -> str:
        """
        論文全文を一度に入力し、平易化または要約した文章を生成する

        Args:
            task: "simplify"（平易化）または "summarize"（要約）
            paper_content: 論文から取り出した本文

        Returns:
            生成された文章
        """
        if task not in TASKS:
            raise ValueError(f"未対応の処理です: {task}")

        try:
            # 前提知識文の生成と同じく、安全のため30万文字を上限とする
            max_chars = 300000
            if len(paper_content) > max_chars:
                print(f"警告: 論文が{len(paper_content)}文字あるため、{max_chars}文字に切り詰めました")
                paper_content = paper_content[:max_chars]

            # 出力の上限は指定しない（平易化は本文と同じくらいの長さになるため）
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": build_user_prompt(task, paper_content)},
                ],
                temperature=0,
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            raise Exception(f"{'平易化' if task == 'simplify' else '要約'}の生成エラー: {str(e)}")
