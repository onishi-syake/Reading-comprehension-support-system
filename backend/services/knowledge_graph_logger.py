import json
import os
from datetime import datetime
from typing import Dict, List, Optional
import logging

class KnowledgeGraphLogger:
    """知識グラフのロギングシステム"""

    def __init__(self, log_dir: str = "logs"):
        """
        Args:
            log_dir: ログファイルを保存するディレクトリ
        """
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)

        # 標準のPythonロガーも設定
        self.logger = logging.getLogger(__name__)
        handler = logging.FileHandler(os.path.join(log_dir, "system.log"))
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def save_knowledge_graph(
        self,
        session_id: str,
        knowledge_graph: Dict,
        user_knowledge: List[Dict],
        metadata: Optional[Dict] = None
    ) -> str:
        """
        知識グラフをJSON形式でログファイルに保存

        Args:
            session_id: セッションID
            knowledge_graph: 知識グラフデータ
            user_knowledge: ユーザーの知識回答履歴
            metadata: その他のメタデータ

        Returns:
            保存したファイルパス
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"knowledge_graph_{session_id[:8]}_{timestamp}.json"
        filepath = os.path.join(self.log_dir, filename)

        log_data = {
            "session_id": session_id,
            "timestamp": timestamp,
            "knowledge_graph": knowledge_graph,
            "user_knowledge": user_knowledge,
            "metadata": metadata or {},
            "statistics": self._calculate_statistics(knowledge_graph, user_knowledge)
        }

        # JSONファイルとして保存
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)

        self.logger.info(f"Knowledge graph saved: {filename}")
        return filepath

    def log_graph_update(
        self,
        session_id: str,
        concept: str,
        prerequisites: List[str],
        action: str = "update"
    ):
        """
        知識グラフの更新をログに記録

        Args:
            session_id: セッションID
            concept: 対象概念
            prerequisites: 前提概念リスト
            action: 実行アクション（update/add/remove等）
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        update_log = {
            "timestamp": timestamp,
            "session_id": session_id[:8],
            "action": action,
            "concept": concept,
            "prerequisites": prerequisites
        }

        # 更新履歴ログファイル
        update_log_file = os.path.join(self.log_dir, "graph_updates.jsonl")
        with open(update_log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(update_log, ensure_ascii=False) + '\n')

        self.logger.info(f"Graph update: {action} - {concept} -> {prerequisites}")

    def _calculate_statistics(
        self,
        knowledge_graph: Dict,
        user_knowledge: List[Dict]
    ) -> Dict:
        """
        知識グラフの統計情報を計算

        Args:
            knowledge_graph: 知識グラフ
            user_knowledge: ユーザー知識履歴

        Returns:
            統計情報の辞書
        """
        total_concepts = len(set([item["concept"] for item in user_knowledge]))
        understood = sum(1 for item in user_knowledge if item.get("understands", False))
        not_understood = total_concepts - understood

        # グラフの深さを計算
        max_depth = 0
        if knowledge_graph:
            max_depth = max(len(prerequisites) for prerequisites in knowledge_graph.values())

        return {
            "total_concepts_asked": total_concepts,
            "concepts_understood": understood,
            "concepts_not_understood": not_understood,
            "understanding_rate": f"{(understood/total_concepts*100):.1f}%" if total_concepts > 0 else "0%",
            "graph_size": len(knowledge_graph),
            "max_prerequisite_depth": max_depth
        }

    def load_knowledge_graph(self, filepath: str) -> Dict:
        """
        保存された知識グラフを読み込む

        Args:
            filepath: 読み込むファイルパス

        Returns:
            知識グラフデータ
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.logger.info(f"Knowledge graph loaded from: {filepath}")
        return data

    def get_session_logs(self, session_id: str) -> List[str]:
        """
        特定セッションのログファイル一覧を取得

        Args:
            session_id: セッションID

        Returns:
            ログファイルパスのリスト
        """
        session_prefix = session_id[:8]
        files = []

        for filename in os.listdir(self.log_dir):
            if filename.startswith(f"knowledge_graph_{session_prefix}"):
                files.append(os.path.join(self.log_dir, filename))

        return sorted(files)