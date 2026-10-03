/**
 * The Communication Workspace state machine.
 *
 * This hook is the single owner of the BRIDGE workflow in the UI. It enforces
 * the same rule the backend does: translation is only offered once the revised
 * source has been approved, so the gate cannot be skipped by clicking through.
 */

import { useCallback, useMemo, useState } from 'react';

import { ApiError, api } from '@/services/api';
import type {
  Message,
  RewriteResponse,
  RiskLevel,
  Translation,
  VerificationReport,
} from '@/types';

export interface WorkspaceDraft {
  sourceMessage: string;
  audience: string;
  purpose: string;
  action: string;
  deadline: string;
  contactPath: string;
  tone: string;
  riskLevel: RiskLevel;
  targetLanguages: string[];
  locale: string;
}

export const EMPTY_DRAFT: WorkspaceDraft = {
  sourceMessage: '',
  audience: 'families',
  purpose: '',
  action: '',
  deadline: '',
  contactPath: '',
  tone: 'warm, respectful, direct',
  riskLevel: 'routine',
  targetLanguages: ['es', 'hi'],
  locale: 'en-US',
};

export type WorkspaceStep =
  | 'idle'
  | 'rewriting'
  | 'approving'
  | 'translating'
  | 'verifying'
  | 'error';

export interface WorkspaceState {
  draft: WorkspaceDraft;
  setDraft: (patch: Partial<WorkspaceDraft>) => void;
  step: WorkspaceStep;
  error: string | null;
  clearError: () => void;
  message: Message | null;
  rewrite: RewriteResponse | null;
  translations: Translation[];
  report: VerificationReport | null;
  /** True once a human has approved the revised source. */
  isApproved: boolean;
  /** True when translation is offered. Mirrors the backend's own rule. */
  canTranslate: boolean;
  canVerify: boolean;
  runRewrite: () => Promise<void>;
  approve: (reviewer?: string) => Promise<void>;
  reject: (notes: string) => Promise<void>;
  translate: () => Promise<void>;
  verify: (translationId: string) => Promise<void>;
  reset: () => void;
}

function messageFromError(error: unknown): string {
  if (error instanceof ApiError) return error.userMessage;
  if (error instanceof Error) return error.message;
  return 'Something went wrong. Please try again.';
}

export function useWorkspace(): WorkspaceState {
  const [draft, setDraftState] = useState<WorkspaceDraft>(EMPTY_DRAFT);
  const [step, setStep] = useState<WorkspaceStep>('idle');
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<Message | null>(null);
  const [rewrite, setRewrite] = useState<RewriteResponse | null>(null);
  const [translations, setTranslations] = useState<Translation[]>([]);
  const [report, setReport] = useState<VerificationReport | null>(null);

  const setDraft = useCallback((patch: Partial<WorkspaceDraft>) => {
    setDraftState((current) => ({ ...current, ...patch }));
  }, []);

  const clearError = useCallback(() => setError(null), []);

  const isApproved =
    message?.state === 'approved' ||
    message?.state === 'translated' ||
    message?.state === 'verified' ||
    message?.state === 'escalated';

  const canTranslate =
    Boolean(message?.id) && isApproved && draft.targetLanguages.length >= 2;
  const canVerify = translations.length > 0;


  /**
   * Rewrite, creating the workspace on the first call.
   *
   * The source is saved first so the revision, the approval, and everything
   * downstream attach to one durable record rather than to browser state.
   */
  const runRewrite = useCallback(async () => {
    if (!draft.sourceMessage.trim()) {
      setError('Write your message before improving it.');
      return;
    }
    setStep('rewriting');
    setError(null);
    try {
      let current = message;
      if (!current) {
        current = await api.createMessage({
          source_message: draft.sourceMessage,
          audience: draft.audience,
          purpose: draft.purpose,
          action: draft.action,
          deadline: draft.deadline,
          contact_path: draft.contactPath,
          tone: draft.tone,
          risk_level: draft.riskLevel,
          target_languages: draft.targetLanguages,
          locale: draft.locale,
        });
      }
      const result = await api.rewriteMessage({ message_id: current.id });
      setMessage(current);
      setRewrite(result);
      // Re-read the workspace so the new revision and its state are current.
      setMessage(await api.getMessage(current.id));
    } catch (err) {
      setError(messageFromError(err));
    } finally {
      setStep('idle');
    }
  }, [draft, message]);

  const approve = useCallback(
    async (reviewer?: string) => {
      if (!message) return;
      setStep('approving');
      setError(null);
      try {
        const updated = await api.approveMessage(message.id, {
          approved: true,
          reviewer: reviewer || undefined,
        });
        setMessage(updated);
        setReport(null);
      } catch (err) {
        setError(messageFromError(err));
      } finally {
        setStep('idle');
      }
    },
    [message],
  );

  const reject = useCallback(
    async (notes: string) => {
      if (!message) return;
      setStep('approving');
      setError(null);
      try {
        const updated = await api.rejectMessage(message.id, notes);
        setMessage(updated);
        setRewrite(null);
      } catch (err) {
        setError(messageFromError(err));
      } finally {
        setStep('idle');
      }
    },
    [message],
  );

  const translate = useCallback(async () => {
    if (!message) return;
    if (!isApproved) {
      // Mirrors the backend's gate so the user gets a clear explanation rather
      // than a bare 409.
      setError('Approve the improved message before translating it.');
      return;
    }
    setStep('translating');
    setError(null);
    try {
      const batch = await api.createTranslations({
        message_id: message.id,
        target_languages: draft.targetLanguages,
        locale: draft.locale,
        tone: draft.tone,
      });
      setTranslations(batch.translations);
      setMessage(await api.getMessage(message.id));
    } catch (err) {
      setError(messageFromError(err));
    } finally {
      setStep('idle');
    }
  }, [draft, isApproved, message]);

  const verify = useCallback(async (translationId: string) => {
    setStep('verifying');
    setError(null);
    try {
      setReport(await api.verifyTranslation(translationId));
    } catch (err) {
      setError(messageFromError(err));
    } finally {
      setStep('idle');
    }
  }, []);

  const reset = useCallback(() => {
    setDraftState(EMPTY_DRAFT);
    setMessage(null);
    setRewrite(null);
    setTranslations([]);
    setReport(null);
    setError(null);
    setStep('idle');
  }, []);

  return useMemo(
    () => ({
      draft,
      setDraft,
      step,
      error,
      clearError,
      message,
      rewrite,
      translations,
      report,
      isApproved,
      canTranslate,
      canVerify,
      runRewrite,
      approve,
      reject,
      translate,
      verify,
      reset,
    }),
    [
      draft, setDraft, step, error, clearError, message, rewrite, translations,
      report, isApproved, canTranslate, canVerify, runRewrite, approve, reject,
      translate, verify, reset,
    ],
  );
}

