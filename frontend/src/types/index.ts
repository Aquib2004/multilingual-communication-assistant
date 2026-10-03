/**
 * API types mirroring the backend Pydantic schemas.
 *
 * These are declared once here and imported by components. A component must
 * never re-declare an API shape inline, so a backend change surfaces as a
 * TypeScript error rather than as a silent runtime mismatch.
 */

export type RiskLevel = 'routine' | 'moderate' | 'high';

export type MessageState =
  | 'draft'
  | 'revised'
  | 'approved'
  | 'translated'
  | 'verified'
  | 'escalated';

export type VerificationStatus = 'PASS' | 'WARNING' | 'FAIL' | 'REVIEW' | 'ESCALATED';

export type ProtectedItemType =
  | 'date'
  | 'time'
  | 'datetime'
  | 'number'
  | 'money'
  | 'url'
  | 'email'
  | 'phone'
  | 'name'
  | 'program'
  | 'place'
  | 'deadline'
  | 'action'
  | 'condition'
  | 'contact'
  | 'address'
  | 'code';

export interface LanguageInfo {
  code: string;
  name: string;
  english_name: string;
  script: string;
  direction: string;
  reading_level_hint: string;
  term_support: string;
}

export interface LanguagesResponse {
  source: LanguageInfo;
  targets: LanguageInfo[];
  locales: string[];
}

export interface RiskLevelInfo {
  level: RiskLevel;
  label: string;
  description: string;
  examples: string[];
  review_requirements: string[];
}

export interface RiskLevelsResponse {
  levels: RiskLevelInfo[];
}

export interface PIIFinding {
  category: string;
  excerpt: string;
  severity: string;
}

export interface ChangeSummary {
  original: string;
  revised: string;
  reason: string;
}

export interface RewriteResponse {
  message_id: string | null;
  rewritten_message: string;
  changes: ChangeSummary[];
  open_questions: string[];
  reading_level: Record<string, unknown>;
  pii_warnings: PIIFinding[];
  state: MessageState;
  provider: string;
  model: string;
}

export interface ProtectedItem {
  id: string;
  item_type: ProtectedItemType;
  value: string;
  placeholder: string;
  must_match_exactly: boolean;
  start_offset: number | null;
  end_offset: number | null;
  context_sentence: string | null;
  source: string;
}

export interface ProtectedItemInput {
  item_type: ProtectedItemType;
  value: string;
  must_match_exactly: boolean;
}

export interface Translation {
  id: string;
  message_id: string;
  target_language: string;
  language_name: string;
  locale: string | null;
  translated_message: string;
  back_translation: string | null;
  placeholders: Record<string, string>;
  protected_items: Array<Record<string, unknown>>;
  uncertainties: string[];
  terminology_notes: string[];
  provider: string;
  model: string;
  created_at: string;
}

export interface TranslationBatchResponse {
  message_id: string;
  translations: Translation[];
  provider: string;
  model: string;
}

export interface FactCheck {
  item_type: string;
  source: string;
  translated: string | null;
  status: VerificationStatus;
  detail: string | null;
}

export interface BackTranslationPair {
  source_sentence: string;
  back_translated: string | null;
  status: VerificationStatus;
  detail: string | null;
}

export interface ToneAssessment {
  tone: string;
  mechanical_phrases: string[];
  cultural_awkwardness: string[];
  terminology_notes: string[];
  status: VerificationStatus;
}

export interface Issue {
  severity: 'info' | 'warning' | 'error';
  code: string;
  message: string;
}

export interface RiskEvidence {
  category: string;
  matched: string[];
  excerpt: string;
}

export interface VerificationReport {
  id: string;
  message_id: string;
  translation_id: string;
  target_language: string;
  overall_status: VerificationStatus;
  human_review_required: boolean;
  summary: Record<string, number>;
  checks: FactCheck[];
  back_translation: BackTranslationPair[];
  tone_assessment: ToneAssessment;
  issues: Issue[];
  risk: {
    level: RiskLevel;
    declared_by_user: RiskLevel | null;
    evidence: RiskEvidence[];
    review_requirements: string[];
  };
  escalation_note: string | null;
  review_requirements: string[];
  provider: string;
  model: string;
  verified_at: string;
  created_at: string;
}

export interface Message {
  id: string;
  state: MessageState;
  audience: string;
  purpose: string;
  action: string;
  deadline: string;
  contact_path: string;
  tone: string;
  locale: string;
  risk_level: RiskLevel;
  source_message: string;
  revised_message: string | null;
  changes: ChangeSummary[];
  open_questions: string[];
  reading_level: Record<string, unknown> | null;
  approved_message: string | null;
  approved_at: string | null;
  approved_by: string | null;
  reviewer_feedback: string | null;
  target_languages: string[];
  pii_warnings: Array<Record<string, unknown>>;
  protected_items: ProtectedItem[];
  translations: Translation[];
  verification_reports: VerificationReport[];
  created_at: string;
  updated_at: string;
}

export interface MessageListResponse {
  items: Message[];
  total: number;
  limit: number;
  offset: number;
}

export interface ExampleMessage {
  id: string;
  title: string;
  risk_level: RiskLevel;
  category: string;
  target_languages: string[];
  locale: string;
  tone: string;
  audience: string;
  purpose: string;
  action: string;
  deadline: string;
  source_message: string;
}

export interface ExamplesResponse {
  items: ExampleMessage[];
  total: number;
  disclaimer: string;
}

export interface EscalationResponse {
  level: RiskLevel;
  declared_by_user: RiskLevel | null;
  evidence: RiskEvidence[];
  escalation_note: string | null;
  review_requirements: string[];
  ai_output_is_final: boolean;
}

export interface HealthResponse {
  status: string;
  app: string;
  version: string;
  environment: string;
  ai_provider: string;
  database: string;
  timestamp: string;
  details: Record<string, unknown>;
}

/** The standard error envelope returned by the backend. */
export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  };
  request_id?: string;
}
