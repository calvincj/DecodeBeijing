const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface Term {
  id: number;
  term_zh: string;
  term_en: string | null;
  category: string;
  description: string | null;
  first_seen_date: string | null;
  added_by: string;
  total_mentions: number;
  first_year: number | null;
  last_year: number | null;
}

export interface Document {
  id: number;
  title_zh: string;
  title_en: string | null;
  meeting_date: string;
  source_url: string;
  word_count_zh: number | null;
  meeting_type: string | null;
  meeting_category: string | null;
}

export interface DocumentDetail extends Document {
  raw_text_zh: string;
}

export interface DocumentTerm {
  term_zh: string;
  term_en: string | null;
  category: string;
  frequency: number;
}

export interface FrequencyPoint {
  document_id: number;
  title_zh: string;
  meeting_date: string;
  frequency: number;
  context_snippets: string[] | null;
  first_char_position: number | null;
  doc_word_count: number | null;
  meeting_category: string | null;
}

export interface FramingPoint {
  document_id: number;
  meeting_date: string;
  attitude: "promoting" | "cautioning" | "stabilizing" | "neutral";
  key_phrase: string | null;
  explanation: string | null;
}

export interface Candidate {
  id: number;
  document_id: number;
  term_zh: string;
  term_en: string | null;
  category: string;
  signal: string;
  significance: string | null;
  frequency: number | null;
  prior_avg: number | null;
  context: string | null;
  created_at: string;
}

export interface Gap {
  last_seen_date: string;
  gap_start_date: string;
  gap_end_date: string | null;
  gap_length_days: number | null;
  meetings_missed: number;
}

export interface RankingPoint {
  document_id: number;
  title_zh: string;
  meeting_date: string;
  list_name_zh: string;
  position: number;
  raw_text_zh: string;
}

export interface CompareResult {
  term_a: { id: number; term_zh: string; term_en: string | null };
  term_b: { id: number; term_zh: string; term_en: string | null };
  series: {
    document_id: number;
    title_zh: string;
    meeting_date: string;
    freq_a: number;
    freq_b: number;
  }[];
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`API ${path} → ${res.status}`);
  return res.json();
}

export const api = {
  terms: ()                         => get<Term[]>("/terms/"),
  documents: ()                     => get<Document[]>("/documents/"),
  document: (id: number)            => get<DocumentDetail>(`/documents/${id}`),
  documentTerms: (id: number)       => get<DocumentTerm[]>(`/documents/${id}/terms`),
  frequency: (id: number)           => get<FrequencyPoint[]>(`/terms/${id}/frequency`),
  gaps: (id: number)                => get<Gap[]>(`/terms/${id}/gaps`),
  rankings: (id: number)            => get<RankingPoint[]>(`/terms/${id}/rankings`),
  compare: (a: number, b: number)   => get<CompareResult>(`/terms/compare?a=${a}&b=${b}`),
  candidates: ()                    => get<Candidate[]>("/candidates/"),
  framing: (id: number)            => get<FramingPoint[]>(`/terms/${id}/framing`),
  searchFrequency: (q: string)     => get<FrequencyPoint[]>(`/terms/search/frequency?q=${encodeURIComponent(q)}`),
};
