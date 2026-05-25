'use client';

import { useState } from 'react';
import PDFUpload from '@/components/PDFUpload';
import KnowledgeAssessment from '@/components/KnowledgeAssessment';
import PrerequisiteText from '@/components/PrerequisiteText';

type Step = 'upload' | 'assessment' | 'result';

export default function Home() {
  const [step, setStep] = useState<Step>('upload');
  const [sessionId, setSessionId] = useState<string>('');
  const [ocrNotice, setOcrNotice] = useState<string>('');

  const handleUploadComplete = (newSessionId: string) => {
    setSessionId(newSessionId);
    setStep('assessment');
  };

  const handleAssessmentComplete = () => {
    setStep('result');
  };

  const handleReset = () => {
    setSessionId('');
    setOcrNotice('');
    setStep('upload');
  };

  return (
    <main className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-8">
      <div className="max-w-4xl mx-auto">
        <header className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-800 mb-2">
            読解支援システム
          </h1>
          <p className="text-gray-600">
            情報科学論文の理解を支援します
          </p>
        </header>

        {/* ステップインジケーター */}
        <div className="flex justify-center mb-8">
          <div className="flex items-center space-x-4">
            <StepIndicator
              number={1}
              label="PDF入力"
              active={step === 'upload'}
              completed={step === 'assessment' || step === 'result'}
            />
            <div className="w-12 h-1 bg-gray-300" />
            <StepIndicator
              number={2}
              label="知識確認"
              active={step === 'assessment'}
              completed={step === 'result'}
            />
            <div className="w-12 h-1 bg-gray-300" />
            <StepIndicator
              number={3}
              label="前提知識文"
              active={step === 'result'}
              completed={false}
            />
          </div>
        </div>

        {/* メインコンテンツ */}
        <div className="bg-white rounded-lg shadow-xl p-8">
          {ocrNotice && (
            <div className="bg-yellow-50 border border-yellow-200 text-yellow-800 px-4 py-3 rounded mb-4">
              {ocrNotice}
            </div>
          )}

          {step === 'upload' && (
            <PDFUpload
              onUploadComplete={handleUploadComplete}
              onOcrNotice={setOcrNotice}
            />
          )}

          {step === 'assessment' && sessionId && (
            <KnowledgeAssessment
              sessionId={sessionId}
              onComplete={handleAssessmentComplete}
            />
          )}

          {step === 'result' && sessionId && (
            <PrerequisiteText sessionId={sessionId} onReset={handleReset} />
          )}
        </div>
      </div>
    </main>
  );
}

function StepIndicator({
  number,
  label,
  active,
  completed
}: {
  number: number;
  label: string;
  active: boolean;
  completed: boolean;
}) {
  return (
    <div className="flex flex-col items-center">
      <div
        className={`w-10 h-10 rounded-full flex items-center justify-center font-bold ${
          active
            ? 'bg-blue-600 text-white'
            : completed
            ? 'bg-green-500 text-white'
            : 'bg-gray-300 text-gray-600'
        }`}
      >
        {completed ? '✓' : number}
      </div>
      <span className="text-xs mt-1 text-gray-600">{label}</span>
    </div>
  );
}
