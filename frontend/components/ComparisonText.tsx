'use client';

import { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkCjkFriendly from 'remark-cjk-friendly';
import { generateComparisonText, ComparisonTask } from '@/lib/api';

// 条件ごとの文言（題名は提案手法とそろえ、結果の見出しと説明だけ変える）
export const COMPARISON_LABELS: Record<
  ComparisonTask,
  { heading: string; description: string; loading: string; filename: string; error: string }
> = {
  simplify: {
    heading: '平易化した文章',
    description: '論文を平易な言葉で書き直した文章を生成しました。',
    loading: '平易化した文章を生成中...',
    filename: '平易化した文章.txt',
    error: '平易化した文章の生成に失敗しました',
  },
  summarize: {
    heading: '要約',
    description: '論文の内容を要約した文章を生成しました。',
    loading: '要約を生成中...',
    filename: '要約.txt',
    error: '要約の生成に失敗しました',
  },
};

interface ComparisonTextProps {
  sessionId: string;
  task: ComparisonTask;
  onReset: () => void;
}

export default function ComparisonText({ sessionId, task, onReset }: ComparisonTextProps) {
  const labels = COMPARISON_LABELS[task];
  const [text, setText] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>('');

  useEffect(() => {
    fetchText();
  }, []);

  const fetchText = async () => {
    setLoading(true);
    setError('');

    try {
      const response = await generateComparisonText(sessionId, task);
      setText(response.text);
    } catch (err: any) {
      setError(err.response?.data?.detail || labels.error);
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = () => {
    const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = labels.filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-800 mb-2">{labels.heading}</h2>
        <p className="text-gray-600">{labels.description}</p>
      </div>

      {loading ? (
        <div className="flex flex-col justify-center items-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mb-4"></div>
          <p className="text-gray-600">{labels.loading}</p>
        </div>
      ) : error ? (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      ) : (
        <>
          {/* 平易化は本文と同じくらいの長さになるため、前提知識文より表示枠を高くしている */}
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-6 max-h-[70vh] overflow-y-auto">
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
                {text}
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
              この文章と元の論文を合わせて読むことで、より深く内容を理解できます。
            </p>
          </div>
        </>
      )}
    </div>
  );
}
