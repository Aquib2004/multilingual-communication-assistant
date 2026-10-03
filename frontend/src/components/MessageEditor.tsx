interface MessageEditorProps {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  maxLength?: number;
}

export function MessageEditor({
  value,
  onChange,
  disabled = false,
  maxLength = 5000,
}: MessageEditorProps) {
  /**
   * The source message editor.
   *
   * The privacy warning is always visible, not only after a warning is raised:
   * the cheapest way to stop someone pasting a child's name is to say so
   * before they type it.
   */
  const remaining = maxLength - value.length;

  return (
    <div>
      <label className="field-label" htmlFor="source-message">
        Your message
      </label>
      <textarea
        id="source-message"
        data-testid="message-editor"
        className="field-input min-h-[10rem] font-normal"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        disabled={disabled}
        maxLength={maxLength}
        placeholder="Paste the message you plan to send to families…"
        aria-describedby="message-editor-help privacy-warning"
      />
      <div className="mt-1 flex items-start justify-between gap-4">
        <p id="message-editor-help" className="text-xs text-slate-600">
          Use placeholders instead of real details, for example{' '}
          <code className="rounded bg-slate-100 px-1">[FAMILY NAME]</code> or{' '}
          <code className="rounded bg-slate-100 px-1">[PHONE]</code>.
        </p>
        <span className="shrink-0 text-xs text-slate-500">{remaining} left</span>
      </div>

      <p
        id="privacy-warning"
        data-testid="privacy-warning"
        className="mt-2 rounded-md bg-amber-50 px-3 py-2 text-xs text-amber-900 ring-1 ring-inset ring-amber-600/20"
      >
        Do not enter real student or family names, phone numbers, email addresses, or student IDs.
        This tool is for fictional or de-identified content.
      </p>
    </div>
  );
}
