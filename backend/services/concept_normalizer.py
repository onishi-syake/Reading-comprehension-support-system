import re
from typing import List, Dict, Set, Tuple
from difflib import SequenceMatcher
import unicodedata

class ConceptNormalizer:
    """概念の正規化と重複検出システム（文字列処理ベース）"""

    def __init__(self, similarity_threshold: float = 0.7):
        """
        Args:
            similarity_threshold: 類似度の閾値（0-1）
        """
        self.similarity_threshold = similarity_threshold

    def normalize_text(self, text: str) -> str:
        """
        テキストの正規化（小文字化、記号除去、空白統一）

        Args:
            text: 正規化するテキスト

        Returns:
            正規化されたテキスト
        """
        # Unicode正規化
        text = unicodedata.normalize('NFKC', text)

        # 括弧内の補足説明を除去
        text = re.sub(r'[（(][^）)]*[）)]', '', text)

        # 記号を空白に置換
        text = re.sub(r'[／/・、。\s]+', ' ', text)

        # 前後の空白を除去
        text = text.strip()

        # 英語は小文字化
        words = []
        for word in text.split():
            if re.match(r'^[A-Za-z]+$', word):
                words.append(word.lower())
            else:
                words.append(word)

        return ' '.join(words)

    def calculate_similarity(self, text1: str, text2: str) -> float:
        """
        2つのテキストの類似度を計算

        Args:
            text1: 比較テキスト1
            text2: 比較テキスト2

        Returns:
            類似度スコア（0-1）
        """
        # 正規化
        norm1 = self.normalize_text(text1)
        norm2 = self.normalize_text(text2)

        # 完全一致
        if norm1 == norm2:
            return 1.0

        # 部分文字列チェック（片方が他方を含む場合）
        if norm1 in norm2 or norm2 in norm1:
            # 長さの比率で調整（短い方が長い方の60%以上なら高い類似度）
            length_ratio = min(len(norm1), len(norm2)) / max(len(norm1), len(norm2))
            return 0.85 if length_ratio >= 0.6 else 0.75

        # 文字列類似度（Ratcliff/Obershelp）
        return SequenceMatcher(None, norm1, norm2).ratio()

    def is_duplicate(self, concept: str, existing_concepts: List[str]) -> Tuple[bool, str]:
        """
        概念が既存概念と重複しているかチェック（完全一致のみ）

        Args:
            concept: チェックする概念
            existing_concepts: 既存の概念リスト

        Returns:
            (重複フラグ, 重複している既存概念)
        """
        norm_concept = self.normalize_text(concept)

        for existing in existing_concepts:
            norm_existing = self.normalize_text(existing)

            # 完全一致のみチェック（正規化後）
            # 括弧内の補足を除去した後で一致すれば重複とみなす
            if norm_concept == norm_existing:
                return True, existing

        return False, ""

    def _check_containment(self, text1: str, text2: str) -> bool:
        """
        包含関係をチェック（単純な部分文字列ではなく、意味的な包含）

        Args:
            text1: テキスト1
            text2: テキスト2

        Returns:
            包含関係がある場合True
        """
        # 単語単位で分割
        words1 = set(text1.split())
        words2 = set(text2.split())

        # 片方の単語がもう片方に全て含まれている場合
        if words1.issubset(words2) or words2.issubset(words1):
            return True

        # 主要な単語（3文字以上）が共通している場合
        significant_words1 = {w for w in words1 if len(w) >= 3}
        significant_words2 = {w for w in words2 if len(w) >= 3}

        if significant_words1 and significant_words2:
            intersection = significant_words1 & significant_words2
            # 共通単語が片方の70%以上を占める場合
            if len(intersection) >= len(significant_words1) * 0.7 or \
               len(intersection) >= len(significant_words2) * 0.7:
                return True

        return False

    def filter_duplicates(self, new_concepts: List[str], existing_concepts: List[str]) -> List[str]:
        """
        新しい概念リストから重複を除去

        Args:
            new_concepts: 新しい概念のリスト
            existing_concepts: 既存概念のリスト

        Returns:
            重複を除去した概念リスト
        """
        filtered = []
        all_existing = existing_concepts.copy()

        for concept in new_concepts:
            is_dup, _ = self.is_duplicate(concept, all_existing)
            if not is_dup:
                filtered.append(concept)
                all_existing.append(concept)  # 新たに追加した概念も考慮

        return filtered

    def merge_similar_concepts(self, concepts: List[str]) -> Dict[str, List[str]]:
        """
        類似概念をグループ化

        Args:
            concepts: 概念リスト

        Returns:
            {代表概念: [類似概念リスト]}の辞書
        """
        groups = {}
        processed = set()

        for i, concept1 in enumerate(concepts):
            if concept1 in processed:
                continue

            group = [concept1]
            processed.add(concept1)

            for j, concept2 in enumerate(concepts[i+1:], i+1):
                if concept2 in processed:
                    continue

                similarity = self.calculate_similarity(concept1, concept2)
                if similarity >= self.similarity_threshold:
                    group.append(concept2)
                    processed.add(concept2)

            # 最も短い概念を代表とする
            representative = min(group, key=lambda x: len(x))
            groups[representative] = group

        return groups

    def get_canonical_form(self, concept: str, existing_concepts: List[str]) -> str:
        """
        概念の正規形を取得（既存概念との統一）

        Args:
            concept: 正規化する概念
            existing_concepts: 既存概念リスト

        Returns:
            正規形の概念名
        """
        # 既存概念と重複している場合は既存の形式を使用
        is_dup, existing = self.is_duplicate(concept, existing_concepts)
        if is_dup:
            return existing

        # 括弧を除去した短い形式を優先
        normalized = self.normalize_text(concept)
        if len(normalized) < len(concept):
            return normalized

        return concept