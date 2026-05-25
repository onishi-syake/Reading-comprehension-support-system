import axios from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export interface ConceptQuestion {
  concept: string;
  description: string;
}

export interface SessionResponse {
  session_id: string;
  message: string;
  method?: 'pdfplumber' | 'ocr';
}

export interface ConceptsResponse {
  concepts: string[];
}

export interface QuestionResponse {
  finished: boolean;
  question: ConceptQuestion | null;
}

export interface PrerequisiteTextResponse {
  prerequisite_text: string;
}

// ファイルアップロード（PDF / Word）
export const uploadFile = async (file: File): Promise<SessionResponse> => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await api.post('/upload-file', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

// 概念抽出
export const extractConcepts = async (sessionId: string): Promise<ConceptsResponse> => {
  const response = await api.post('/extract-concepts', { session_id: sessionId });
  return response.data;
};

// 次の質問取得
export const getNextQuestion = async (sessionId: string): Promise<QuestionResponse> => {
  const response = await api.post('/get-next-question', { session_id: sessionId });
  return response.data;
};

// 概念への回答
export const answerConcept = async (
  sessionId: string,
  concept: string,
  understands: boolean
): Promise<void> => {
  await api.post('/answer-concept', {
    session_id: sessionId,
    concept,
    understands,
  });
};

// 前提知識文生成
export const generatePrerequisiteText = async (
  sessionId: string
): Promise<PrerequisiteTextResponse> => {
  const response = await api.post('/generate-prerequisite-text', { session_id: sessionId });
  return response.data;
};

export default api;
