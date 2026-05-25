'use client';

import { useState, useEffect } from 'react';
import { getNextQuestion, answerConcept, ConceptQuestion } from '@/lib/api';

interface KnowledgeAssessmentProps {
  sessionId: string;
  onComplete: () => void;
}

export default function KnowledgeAssessment({
  sessionId,
  onComplete,
}: KnowledgeAssessmentProps) {
  const [currentQuestion, setCurrentQuestion] = useState<ConceptQuestion | null>(null);
  const [loading, setLoading] = useState(false);
  const [answeredCount, setAnsweredCount] = useState(0);
  const [error, setError] = useState<string>('');

  // 初回質問取得
  useEffect(() => {
    fetchNextQuestion();
  }, []);

  const fetchNextQuestion = async () => {
    setLoading(true);
    setError('');

    try {
      const response = await getNextQuestion(sessionId);

      if (response.finished || !response.question) {
        // 質問終了、前提文生成へ
        onComplete();
      } else {
        setCurrentQuestion(response.question);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || '質問の取得に失敗しました');
    } finally {
      setLoading(false);
    }
  };

  const handleAnswer = async (understands: boolean) => {
    if (!currentQuestion) return;

    setLoading(true);
    setError('');

    try {
      // 回答を送信
      await answerConcept(sessionId, currentQuestion.concept, understands);
      setAnsweredCount((prev) => prev + 1);

      // 次の質問を取得
      await fetchNextQuestion();
    } catch (err: any) {
      setError(err.response?.data?.detail || '回答の送信に失敗しました');
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-800 mb-2">知識確認</h2>
        <p className="text-gray-600">
          論文を理解するために必要な概念について、あなたの知識を確認します。
        </p>
        <div className="mt-2 text-sm text-gray-500">
          回答済み: {answeredCount} 件
        </div>
      </div>

      {loading && !currentQuestion ? (
        <div className="flex justify-center items-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        </div>
      ) : currentQuestion ? (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
          <h3 className="text-xl font-semibold text-gray-800 mb-4">
            {currentQuestion.description}
          </h3>

          <div className="flex space-x-4">
            <button
              onClick={() => handleAnswer(true)}
              disabled={loading}
              className={`flex-1 py-3 px-6 rounded-lg font-semibold transition-colors ${
                loading
                  ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                  : 'bg-green-500 text-white hover:bg-green-600'
              }`}
            >
              はい、理解しています
            </button>
            <button
              onClick={() => handleAnswer(false)}
              disabled={loading}
              className={`flex-1 py-3 px-6 rounded-lg font-semibold transition-colors ${
                loading
                  ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                  : 'bg-red-500 text-white hover:bg-red-600'
              }`}
            >
              いいえ、分かりません
            </button>
          </div>
        </div>
      ) : null}

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <p className="text-sm text-gray-700">
          <strong>ヒント:</strong>{' '}
          正直に回答してください。理解していない概念については、適切な前提知識を提供します。
        </p>
      </div>
    </div>
  );
}
