'use client';

import { useState } from 'react';
import { uploadFile, extractConcepts } from '@/lib/api';

interface PDFUploadProps {
  onUploadComplete: (sessionId: string) => void;
  onOcrNotice?: (message: string) => void;
}

export default function PDFUpload({ onUploadComplete, onOcrNotice }: PDFUploadProps) {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>('');

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0];
      const ext = selectedFile.name.split('.').pop()?.toLowerCase();
      if (ext && ['pdf', 'docx', 'txt'].includes(ext)) {
        setFile(selectedFile);
        setError('');
      } else {
        setError('PDF、Word(.docx)、またはテキストファイルを選択してください');
        setFile(null);
      }
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setError('ファイルを選択してください');
      return;
    }

    setLoading(true);
    setError('');

    try {
      // 前回の通知をクリア
      if (onOcrNotice) {
        onOcrNotice('');
      }

      // ファイルアップロード
      const uploadResponse = await uploadFile(file);
      const sessionId = uploadResponse.session_id;

      // OCR使用時はユーザーに通知
      if (uploadResponse.method === 'ocr' && onOcrNotice) {
        onOcrNotice(uploadResponse.message);
      }

      // 概念抽出
      await extractConcepts(sessionId);

      // 次のステップへ
      onUploadComplete(sessionId);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'アップロードに失敗しました');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-800 mb-4">
          論文ファイルをアップロード
        </h2>
        <p className="text-gray-600 mb-6">
          理解を支援したい情報科学論文のファイルを選択してください。（PDF / Word / テキスト）
        </p>
      </div>

      <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:border-blue-400 transition-colors">
        <input
          type="file"
          accept=".pdf,.docx,.txt"
          onChange={handleFileChange}
          className="hidden"
          id="pdf-upload"
        />
        <label
          htmlFor="pdf-upload"
          className="cursor-pointer flex flex-col items-center"
        >
          <svg
            className="w-16 h-16 text-gray-400 mb-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
            />
          </svg>
          <span className="text-lg text-gray-600">
            {file ? file.name : 'クリックしてファイルを選択（PDF / Word / テキスト）'}
          </span>
          <span className="text-sm text-gray-400 mt-2">
            または、ファイルをドラッグ&ドロップ
          </span>
        </label>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      <button
        onClick={handleUpload}
        disabled={!file || loading}
        className={`w-full py-3 px-6 rounded-lg font-semibold text-white transition-colors ${
          !file || loading
            ? 'bg-gray-300 cursor-not-allowed'
            : 'bg-blue-600 hover:bg-blue-700'
        }`}
      >
        {loading ? (
          <span className="flex items-center justify-center">
            <svg
              className="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              ></circle>
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              ></path>
            </svg>
            処理中...
          </span>
        ) : (
          'アップロードして次へ'
        )}
      </button>
    </div>
  );
}
