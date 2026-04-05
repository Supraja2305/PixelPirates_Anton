/**
 * ChatMessage Component
 * Renders AI responses with full markdown: **bold**, *italic*,
 * blockquotes (> ...), bullet/numbered lists, inline code.
 * Fixes raw asterisk display in AI responses.
 */
import { cn } from '@/lib/utils';
import type { ChatMessage as ChatMessageType } from '@/types';

interface ChatMessageProps {
  message: ChatMessageType;
}

// ─── Inline parser: **bold**, *italic*, `code` ────────────────────────────────

function parseInline(text: string): React.ReactNode[] {
  const segments = text.split(/(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g);
  return segments.map((seg, i) => {
    if (seg.startsWith('**') && seg.endsWith('**'))
      return <strong key={i} className="font-semibold text-ink">{seg.slice(2, -2)}</strong>;
    if (seg.startsWith('*') && seg.endsWith('*'))
      return <em key={i}>{seg.slice(1, -1)}</em>;
    if (seg.startsWith('`') && seg.endsWith('`'))
      return <code key={i} className="px-1.5 py-0.5 rounded bg-off-white border border-border-light font-mono text-xs">{seg.slice(1, -1)}</code>;
    return seg;
  });
}

// ─── Block renderer ───────────────────────────────────────────────────────────

function MarkdownContent({ text }: { text: string }) {
  const lines = text.split('\n');
  const nodes: React.ReactNode[] = [];
  let listItems: React.ReactNode[] = [];
  let k = 0;

  const flushList = () => {
    if (!listItems.length) return;
    nodes.push(<ul key={k++} className="mt-1.5 mb-1.5 flex flex-col gap-1.5 pl-0.5">{listItems}</ul>);
    listItems = [];
  };

  for (const line of lines) {
    const t = line.trim();

    // Blockquote — > "quote" — payer, policy, page
    if (t.startsWith('> ')) {
      flushList();
      const body = t.slice(2);
      const dashIdx = body.indexOf(' — ');
      nodes.push(
        <blockquote key={k++} className="mt-2.5 border-l-[3px] border-accent-blue bg-blue-50/50 rounded-r-lg px-3.5 py-2.5">
          {dashIdx !== -1 ? (
            <>
              <p className="text-sm text-ink italic leading-relaxed">&ldquo;{body.slice(0, dashIdx).replace(/^"|"$/g, '')}&rdquo;</p>
              <p className="text-xs text-accent-blue font-medium mt-1">— {body.slice(dashIdx + 3)}</p>
            </>
          ) : (
            <p className="text-sm text-ink italic leading-relaxed">{body}</p>
          )}
        </blockquote>
      );
      continue;
    }

    // Bullet list — - item or • item
    if (/^[-•*]\s+/.test(t)) {
      listItems.push(
        <li key={k++} className="flex gap-2 text-sm text-ink leading-relaxed">
          <span className="w-1.5 h-1.5 rounded-full bg-accent-blue flex-shrink-0 mt-[7px]" />
          <span>{parseInline(t.replace(/^[-•*]\s+/, ''))}</span>
        </li>
      );
      continue;
    }

    // Numbered list — 1. item
    const numMatch = t.match(/^(\d+)\.\s+(.*)/);
    if (numMatch) {
      listItems.push(
        <li key={k++} className="flex gap-2 text-sm text-ink leading-relaxed">
          <span className="flex-shrink-0 w-5 h-5 rounded-full bg-accent-blue/10 text-accent-blue text-xs font-bold flex items-center justify-center mt-0.5">
            {numMatch[1]}
          </span>
          <span>{parseInline(numMatch[2])}</span>
        </li>
      );
      continue;
    }

    // Empty line = break
    if (!t) { flushList(); nodes.push(<div key={k++} className="h-1.5" />); continue; }

    // Plain paragraph
    flushList();
    nodes.push(<p key={k++} className="text-sm leading-relaxed text-ink">{parseInline(t)}</p>);
  }

  flushList();
  return <div className="flex flex-col gap-1">{nodes}</div>;
}

// ─── Main component ───────────────────────────────────────────────────────────

export function ChatMessage({ message }: ChatMessageProps) {
  const isAI = message.role === 'ai';

  return (
    <div className={cn('flex gap-3 animate-in fade-in slide-in-from-bottom-2', isAI ? 'justify-start' : 'justify-end')}>

      {isAI && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-accent-blue flex items-center justify-center mt-0.5">
          <span className="text-white text-xs font-bold">Rx</span>
        </div>
      )}

      <div className={cn('max-w-[85%] md:max-w-[72%]', isAI ? 'order-2' : 'order-1')}>
        <div className={cn(
          'rounded-xl px-4 py-3',
          isAI ? 'bg-white border border-border-light border-l-[3px] border-l-accent-blue' : 'bg-accent-blue text-white'
        )}>
          {isAI
            ? <MarkdownContent text={message.content} />
            : <p className="text-sm leading-relaxed">{message.content}</p>
          }
        </div>

        {/* Inline citation rendered from source_citation field */}
        {message.citation && (
          <div className="mt-2 ml-0.5 rounded-lg bg-blue-50 border border-accent-blue/20 px-3 py-2">
            <p className="text-accent-blue text-[10px] font-semibold uppercase tracking-wider mb-1">Policy citation</p>
            <p className="text-muted-text text-xs italic leading-relaxed">&ldquo;{message.citation.quote}&rdquo;</p>
          </div>
        )}
      </div>

      {!isAI && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-navy/10 border border-navy/20 flex items-center justify-center order-2 mt-0.5">
          <span className="text-navy text-xs font-semibold">U</span>
        </div>
      )}
    </div>
  );
}