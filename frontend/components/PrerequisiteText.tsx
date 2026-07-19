'use client';

import { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkCjkFriendly from 'remark-cjk-friendly';
import { generatePrerequisiteText } from '@/lib/api';
import ChatBot from './ChatBot';

interface PrerequisiteTextProps {
  sessionId: string;
  onReset: () => void;
}

export default function PrerequisiteText({
  sessionId,
  onReset,
}: PrerequisiteTextProps) {
  const [prerequisiteText, setPrerequisiteText] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>('');

  useEffect(() => {
    fetchPrerequisiteText();
  }, []);

  const fetchPrerequisiteText = async () => {
    setLoading(true);
    setError('');

    try {
      const response = await generatePrerequisiteText(sessionId);
      setPrerequisiteText(response.prerequisite_text);
    } catch (err: any) {
      setError(err.response?.data?.detail || '前提知識文の生成に失敗しました');
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = () => {
    const blob = new Blob([prerequisiteText], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = '前提知識文.txt';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-800 mb-2">前提知識文</h2>
        <p className="text-gray-600">
          あなたの知識レベルに合わせた前提知識の説明を生成しました。
        </p>
      </div>

      {loading ? (
        <div className="flex flex-col justify-center items-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mb-4"></div>
          <p className="text-gray-600">前提知識文を生成中...</p>
        </div>
      ) : error ? (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      ) : (
        <>
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-6 max-h-96 overflow-y-auto">
            <div className="text-gray-800 leading-relaxed text-base">
              <ReactMarkdown
                remarkPlugins={[remarkCjkFriendly]}
                components={{
                  p: ({ children }) => <p className="mb-3 last:mb-0">{children}</p>,
                  ul: ({ children }) => <ul className="list-disc pl-5 mb-3 last:mb-0 space-y-1">{children}</ul>,
                  ol: ({ children }) => <ol className="list-decimal pl-5 mb-3 last:mb-0 space-y-1">{children}</ol>,
                  li: ({ children }) => <li>{children}</li>,
                  strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
                  em: ({ children }) => <em className="italic">{children}</em>,
                  h1: ({ children }) => <h1 className="font-bold text-lg mb-2 mt-3 first:mt-0">{children}</h1>,
                  h2: ({ children }) => <h2 className="font-bold text-base mb-2 mt-3 first:mt-0">{children}</h2>,
                  h3: ({ children }) => <h3 className="font-semibold text-sm mb-1 mt-2 first:mt-0">{children}</h3>,
                  code: ({ children }) => (
                    <code className="bg-gray-200 text-gray-900 px-1 py-0.5 rounded text-xs font-mono">{children}</code>
                  ),
                  a: ({ href, children }) => (
                    <a href={href} target="_blank" rel="noopener noreferrer" className="text-blue-600 underline">
                      {children}
                    </a>
                  ),
                }}
              >
                {prerequisiteText}
              </ReactMarkdown>
            </div>
          </div>

          <div className="flex space-x-4">
            <button
              onClick={handleDownload}
              className="flex-1 py-3 px-6 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 transition-colors"
            >
              テキストとしてダウンロード
            </button>
            <button
              onClick={onReset}
              className="flex-1 py-3 px-6 bg-gray-500 text-white rounded-lg font-semibold hover:bg-gray-600 transition-colors"
            >
              新しい論文を試す
            </button>
          </div>

          <div className="bg-green-50 border border-green-200 rounded-lg p-4">
            <p className="text-sm text-gray-700">
              <strong>次のステップ:</strong>{' '}
              この前提知識を読んだ後、元の論文を読むことで、より深く内容を理解できます。
              右下のチャットから質問もできます。
            </p>
          </div>

          <ChatBot sessionId={sessionId} />
        </>
      )}
    </div>
  );
}
