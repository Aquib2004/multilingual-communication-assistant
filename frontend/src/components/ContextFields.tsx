import type { RiskLevel } from '@/types';

const AUDIENCES = [
  { value: 'families', label: 'Families' },
  { value: 'caregivers', label: 'Caregivers' },
  { value: 'community', label: 'Community members' },
  { value: 'staff', label: 'Staff' },
  { value: 'partners', label: 'Partner organisations' },
];

const TONES = [
  { value: 'warm, respectful, direct', label: 'Warm, respectful, direct' },
  { value: 'formal', label: 'Formal' },
  { value: 'friendly and brief', label: 'Friendly and brief' },
];

const RISKS: Array<{ value: RiskLevel; label: string; help: string }> = [
  { value: 'routine', label: 'Routine', help: 'Welcome note, event reminder, or update.' },
  {
    value: 'moderate',
    label: 'Moderate consequence',
    help: 'Permission, schedule change, or participation instructions.',
  },
  {
    value: 'high',
    label: 'High consequence',
    help: 'Safety, health, legal rights, discipline, or disability services.',
  },
];

interface SelectProps {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: Array<{ value: string; label: string }>;
  help?: string;
  disabled?: boolean;
}

function Select({ id, label, value, onChange, options, help, disabled }: SelectProps) {
  /** A labelled select, shared by the single-choice context fields. */
  return (
    <div>
      <label className="field-label" htmlFor={id}>
        {label}
      </label>
      <select
        id={id}
        className="field-input"
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
        aria-describedby={help ? `${id}-help` : undefined}
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      {help ? (
        <p id={`${id}-help`} className="mt-1 text-xs text-slate-600">
          {help}
        </p>
      ) : null}
    </div>
  );
}

export interface ContextPatch {
  audience?: string;
  purpose?: string;
  action?: string;
  deadline?: string;
  contactPath?: string;
  tone?: string;
  riskLevel?: RiskLevel;
}

interface ContextFieldsProps {
  audience: string;
  purpose: string;
  action: string;
  deadline: string;
  contactPath: string;
  tone: string;
  riskLevel: RiskLevel;
  disabled?: boolean;
  onChange: (patch: ContextPatch) => void;
}

export function ContextFields({
  audience,
  purpose,
  action,
  deadline,
  contactPath,
  tone,
  riskLevel,
  disabled = false,
  onChange,
}: ContextFieldsProps) {
  /**
   * BRIDGE step B: "Begin with purpose".
   *
   * The translator works from this context rather than the message text alone,
   * so these fields are part of the workflow, not optional metadata.
   */
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <Select
        id="audience"
        label="Audience"
        value={audience}
        disabled={disabled}
        onChange={(value) => onChange({ audience: value })}
        options={AUDIENCES}
      />
      <Select
        id="tone"
        label="Tone"
        value={tone}
        disabled={disabled}
        onChange={(value) => onChange({ tone: value })}
        options={TONES}
      />

      <div className="sm:col-span-2">
        <label className="field-label" htmlFor="purpose">
          Purpose
        </label>
        <input
          id="purpose"
          data-testid="purpose-input"
          className="field-input"
          value={purpose}
          disabled={disabled}
          placeholder="Invite families to an information evening"
          onChange={(event) => onChange({ purpose: event.target.value })}
        />
      </div>

      <div>
        <label className="field-label" htmlFor="action">
          Requested action
        </label>
        <input
          id="action"
          className="field-input"
          value={action}
          disabled={disabled}
          placeholder="RSVP using the link"
          onChange={(event) => onChange({ action: event.target.value })}
        />
      </div>

      <div>
        <label className="field-label" htmlFor="deadline">
          Deadline
        </label>
        <input
          id="deadline"
          className="field-input"
          value={deadline}
          disabled={disabled}
          placeholder="October 3"
          onChange={(event) => onChange({ deadline: event.target.value })}
        />
        <p className="mt-1 text-xs text-slate-600">
          A vague phrase like &ldquo;soon&rdquo; cannot be translated into a date.
        </p>
      </div>

      <div className="sm:col-span-2">
        <label className="field-label" htmlFor="contact">
          Contact path
        </label>
        <input
          id="contact"
          className="field-input"
          value={contactPath}
          disabled={disabled}
          placeholder="Call [PROGRAM OFFICE] at [PHONE], or email [EMAIL]"
          onChange={(event) => onChange({ contactPath: event.target.value })}
        />
        <p className="mt-1 text-xs text-slate-600">
          Tell families how to ask a question or request an interpreter.
        </p>
      </div>

      <div className="sm:col-span-2">
        <label className="field-label" htmlFor="risk">
          Risk level
        </label>
        <select
          id="risk"
          data-testid="risk-select"
          className="field-input"
          value={riskLevel}
          disabled={disabled}
          onChange={(event) => onChange({ riskLevel: event.target.value as RiskLevel })}
          aria-describedby="risk-help"
        >
          {RISKS.map((risk) => (
            <option key={risk.value} value={risk.value}>
              {risk.label}
            </option>
          ))}
        </select>
        <p id="risk-help" className="mt-1 text-xs text-slate-600">
          {RISKS.find((risk) => risk.value === riskLevel)?.help}
        </p>
      </div>
    </div>
  );
}

