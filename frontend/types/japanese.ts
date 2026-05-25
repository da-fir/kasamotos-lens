export type ContextType = "sign" | "menu" | "notice" | "letter" | "other";

export interface Token {
  surface: string;       // 食べる  (as it appears in text)
  reading: string;       // たべる  (hiragana reading, source for furigana)
  romaji: string;        // taberu
  pos: string;           // verb | noun | particle | adjective | etc
  base_form: string;     // dictionary form
  meaning: string;       // English meaning of this token
  jlpt_level: string | null;
}

export interface Sentence {
  original: string;
  romaji: string;
  meaning: string;
  nuance: string;
  grammar_pattern: string | null;
  tokens: Token[];
}

export interface AnalysisResult {
  id: string;
  raw_text: string;
  context_type: ContextType;
  sentences: Sentence[];
  created_at: string;
}