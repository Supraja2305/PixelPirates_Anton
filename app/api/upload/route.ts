/**
 * POST /api/upload
 * Complete rewrite — fixes:
 *   1. max_tokens was 3000; large policy docs hit the limit and truncate the JSON mid-array
 *   2. TypeScript error: escapeControlChars used before defined (moved to top-level)
 *   3. findBalancedArray moved to top-level (no nested function declarations)
 *   4. Detects truncation via stop_reason and returns a clear error
 */

import { NextRequest, NextResponse } from 'next/server';
import Anthropic from '@anthropic-ai/sdk';

// ─── Anthropic client ─────────────────────────────────────────────────────────

function getClient(): Anthropic {
  const key = process.env.ANTHROPIC_API_KEY;
  if (!key) {
    throw new Error('ANTHROPIC_API_KEY is not set. Add it to .env.local and restart.');
  }
  return new Anthropic({ apiKey: key });
}

// ─── Extraction prompt ────────────────────────────────────────────────────────

const EXTRACTION_PROMPT = `You are a medical policy extraction engine. Extract structured coverage criteria from a payer policy document.

Your output must have EXACTLY TWO parts with no extra text:

PART 1 — A valid JSON array only (no markdown fences, no preamble):
[{"drug_name":string,"brand_names":string[],"j_code":string|null,"payer":string,"policy_id":string|null,"effective_date":string|null,"coverage_status":"covered"|"pa_required"|"step_therapy"|"not_covered"|"unknown","prior_auth_required":boolean,"prior_auth_form":string|null,"covered_indications":string[],"excluded_indications":string[],"step_therapy_required":boolean,"step_therapy_details":string|null,"site_of_care_restriction":string|null,"quantity_limits":string|null,"source_page":string|null,"source_quote":null}]

JSON rules — CRITICAL:
- "source_quote" must always be the literal null. Never put text there.
- No literal newlines inside string values. No unescaped double-quotes inside string values.
- Missing fields = null, never "".
- One object per drug per payer.
- Compact JSON (no extra whitespace) to stay within token limits.

PART 2 — Immediately after the ] close the JSON, then on the very next line:
QUOTES
drug_name|payer|One verbatim sentence. Any characters fine here including "quotes".

No blank lines between Part 1 and Part 2.`;

// ─── Escape control chars inside JSON strings ─────────────────────────────────
// Fixes literal \n \r \t that appear inside string values and break JSON.parse.
// Defined at top level so parseJSON can call it without hoisting issues.

function escapeControlChars(raw: string): string {
  let out = '';
  let inString = false;
  let escaped = false;

  for (let i = 0; i < raw.length; i++) {
    const ch = raw[i];

    if (escaped) {
      out += ch;
      escaped = false;
      continue;
    }
    if (ch === '\\') {
      out += ch;
      escaped = true;
      continue;
    }
    if (ch === '"') {
      inString = !inString;
      out += ch;
      continue;
    }
    if (inString) {
      if (ch === '\n') { out += '\\n'; continue; }
      if (ch === '\r') { out += '\\r'; continue; }
      if (ch === '\t') { out += '\\t'; continue; }
    }
    out += ch;
  }
  return out;
}

// ─── Balanced bracket finder ──────────────────────────────────────────────────
// Uses a depth counter to find the exact ] that closes the opening [.
// Much more reliable than lastIndexOf(']') which grabs the wrong bracket
// when the QUOTES section or other content follows the JSON array.

function findBalancedArray(input: string): string | null {
  const start = input.indexOf('[');
  if (start === -1) return null;

  let depth = 0;
  let inString = false;
  let escaped = false;

  for (let i = start; i < input.length; i++) {
    const ch = input[i];

    if (escaped) { escaped = false; continue; }
    if (ch === '\\' && inString) { escaped = true; continue; }
    if (ch === '"') { inString = !inString; continue; }

    if (!inString) {
      if (ch === '[') depth++;
      if (ch === ']') {
        depth--;
        if (depth === 0) return input.slice(start, i + 1);
      }
    }
  }
  return null; // no balanced array found (likely truncated response)
}

// ─── JSON parser with fallback chain ─────────────────────────────────────────

function parseJSON(jsonStr: string): Record<string, unknown>[] {
  // Strip markdown fences if model added them despite instructions
  const clean = jsonStr
    .replace(/^```(?:json)?\s*/im, '')
    .replace(/\n?```\s*$/im, '')
    .trim();

  // Attempt 1: find balanced array and parse directly
  const arrStr = findBalancedArray(clean);
  if (arrStr) {
    try {
      const parsed = JSON.parse(arrStr);
      if (Array.isArray(parsed) && parsed.length > 0) return parsed;
    } catch (_) {
      // fall through to attempt 2
    }

    // Attempt 2: same array string but with control chars escaped
    try {
      const parsed = JSON.parse(escapeControlChars(arrStr));
      if (Array.isArray(parsed) && parsed.length > 0) return parsed;
    } catch (_) {
      // fall through to attempt 3
    }
  }

  // Attempt 3: single-object fallback (model returned {} instead of [{}])
  const objStart = clean.indexOf('{');
  const objEnd   = clean.lastIndexOf('}') + 1;
  if (objStart !== -1 && objEnd > 0) {
    try {
      return [JSON.parse(clean.slice(objStart, objEnd))];
    } catch (_) {
      try {
        return [JSON.parse(escapeControlChars(clean.slice(objStart, objEnd)))];
      } catch (_2) {
        // fall through to error
      }
    }
  }

  // All attempts failed — include preview in message for diagnosis
  throw new Error(
    `PARSE_FAILED: ${clean.slice(0, 300).replace(/\n/g, ' ')}`
  );
}

// ─── QUOTES section parser ────────────────────────────────────────────────────

function parseQuotes(raw: string): Map<string, string> {
  const map = new Map<string, string>();
  const idx = raw.search(/\nQUOTES\s*\n/i);
  if (idx === -1) return map;

  const section = raw.slice(raw.indexOf('\n', idx) + 1);
  for (const line of section.split('\n')) {
    const t = line.trim();
    if (!t) continue;
    const f = t.indexOf('|');
    const s = t.indexOf('|', f + 1);
    if (f === -1 || s === -1) continue;
    const drug  = t.slice(0, f).trim().toLowerCase();
    const payer = t.slice(f + 1, s).trim().toLowerCase();
    const quote = t.slice(s + 1).trim();
    if (drug && payer && quote) map.set(`${drug}|${payer}`, quote);
  }
  return map;
}

// ─── Full response parser ─────────────────────────────────────────────────────

function parseResponse(raw: string): Record<string, unknown>[] {
  // Split on QUOTES separator so the JSON parser never sees the plaintext section
  const sepIdx   = raw.search(/\nQUOTES\s*\n/i);
  const jsonPart = sepIdx !== -1 ? raw.slice(0, sepIdx) : raw;

  let policies: Record<string, unknown>[];
  try {
    policies = parseJSON(jsonPart);
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    const preview = msg.startsWith('PARSE_FAILED: ')
      ? msg.slice('PARSE_FAILED: '.length)
      : msg.slice(0, 300);
    throw new Error(`Could not read the AI response as JSON. Preview: "${preview}"`);
  }

  // Merge source quotes back in
  const quoteMap = parseQuotes(raw);
  for (const p of policies) {
    const key = `${String(p.drug_name ?? '').toLowerCase()}|${String(p.payer ?? '').toLowerCase()}`;
    const quote = quoteMap.get(key);
    if (quote) p.source_quote = quote;
  }

  return policies;
}

// ─── Text extractors ──────────────────────────────────────────────────────────

async function extractTextFromPdf(buffer: Buffer): Promise<string> {
  try {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const pdfParse = require('pdf-parse') as (buf: Buffer) => Promise<{ text: string }>;
    const result   = await pdfParse(buffer);
    return result.text ?? '';
  } catch (_err) {
    return ''; // pdf-parse not installed — caller falls back to Claude document API
  }
}

async function extractTextFromDocx(buffer: Buffer): Promise<string> {
  try {
    const mammoth = await import('mammoth');
    const result  = await mammoth.extractRawText({ buffer });
    return result.value ?? '';
  } catch (_err) {
    throw new Error('DOCX support requires: npm install mammoth');
  }
}

// ─── Route ────────────────────────────────────────────────────────────────────

export async function POST(req: NextRequest) {
  try {
    const client = getClient();

    const formData = await req.formData();
    const file     = formData.get('file') as File | null;

    if (!file) {
      return NextResponse.json({ error: 'No file uploaded' }, { status: 400 });
    }

    const ext = file.name.split('.').pop()?.toLowerCase() ?? '';
    if (!['pdf', 'png', 'jpg', 'jpeg', 'docx'].includes(ext)) {
      return NextResponse.json(
        { error: `Unsupported file type: .${ext}. Allowed: PDF, PNG, JPG, DOCX` },
        { status: 400 }
      );
    }

    const bytes  = await file.arrayBuffer();
    const buffer = Buffer.from(bytes);

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let messageContent: any[];

    if (ext === 'pdf') {
      const text = await extractTextFromPdf(buffer);
      if (text.trim().length > 100) {
        // Fast path: text already extracted, send as plain text
        messageContent = [
          { type: 'text', text: `${EXTRACTION_PROMPT}\n\nPolicy text:\n${text.slice(0, 40000)}` },
        ];
      } else {
        // Scanned PDF: send as document for Claude vision
        const base64 = buffer.toString('base64');
        messageContent = [
          {
            type: 'document',
            source: { type: 'base64', media_type: 'application/pdf', data: base64 },
          },
          { type: 'text', text: EXTRACTION_PROMPT },
        ];
      }
    } else if (['png', 'jpg', 'jpeg'].includes(ext)) {
      const base64    = buffer.toString('base64');
      const mediaType = ext === 'png' ? 'image/png' : 'image/jpeg';
      messageContent  = [
        { type: 'image', source: { type: 'base64', media_type: mediaType, data: base64 } },
        { type: 'text', text: EXTRACTION_PROMPT },
      ];
    } else {
      const text     = await extractTextFromDocx(buffer);
      messageContent = [
        { type: 'text', text: `${EXTRACTION_PROMPT}\n\nPolicy text:\n${text.slice(0, 40000)}` },
      ];
    }

    const message = await client.messages.create({
      model: 'claude-sonnet-4-6',
      max_tokens: 8192,  // ← KEY FIX: was 3000; large policy docs need 4000–6000+ tokens
      messages: [{ role: 'user', content: messageContent }],
    });

    // Detect response truncation before attempting to parse
    if (message.stop_reason === 'max_tokens') {
      return NextResponse.json(
        { error: 'Policy document is too large to extract in one pass. Try uploading a single-drug section of the policy.' },
        { status: 422 }
      );
    }

    const raw = (message.content[0] as { type: string; text: string }).text.trim();
    console.log(`[/api/upload] stop_reason=${message.stop_reason} length=${raw.length}`);

    const policies = parseResponse(raw);
    policies.forEach((p) => { p.source_file = file.name; });

    return NextResponse.json({ policies });

  } catch (err: unknown) {
    if (err instanceof Anthropic.APIError) {
      const hint = err.status === 401
        ? 'Invalid API key — set ANTHROPIC_API_KEY in .env.local and restart.'
        : `Anthropic API error ${err.status}: ${err.message}`;
      return NextResponse.json({ error: hint }, { status: 500 });
    }
    const msg = err instanceof Error ? err.message : 'Unknown error';
    console.error('[/api/upload]', msg);
    return NextResponse.json({ error: msg }, { status: 500 });
  }
}