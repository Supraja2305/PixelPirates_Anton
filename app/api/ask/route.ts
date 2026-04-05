/**
 * POST /api/ask
 * Answers questions using:
 *   1. Uploaded policy data (primary source — always cited first)
 *   2. Web search for credible online sources (CMS, payer sites) when needed
 *
 * Body: { question: string, policies: ExtractedDrug[] }
 * Returns: { answer: string, source_citation: string | null }
 */

import { NextRequest, NextResponse } from 'next/server';
import Anthropic from '@anthropic-ai/sdk';

function getClient(): Anthropic {
  const key = process.env.ANTHROPIC_API_KEY;
  if (!key) throw new Error('ANTHROPIC_API_KEY is not set in .env.local');
  return new Anthropic({ apiKey: key });
}

// ─── System prompt ────────────────────────────────────────────────────────────

const SYSTEM_PROMPT = `You are Rx, a pharmaceutical coverage analyst at Anton Rx.
You answer questions about drug coverage using two sources of truth:

PRIMARY: Structured policy data extracted from the user's uploaded payer documents.
SECONDARY: Online search for credible medical insurance policy sources (CMS.gov, payer 
  coverage portals, FDA drug information, peer-reviewed coverage guidelines).

Answer format — follow this structure every time:

1. DIRECT ANSWER: One clear sentence. Yes/No when applicable + the key condition.
2. DETAIL: 2–4 sentences. Name the payer. Bold key terms:
   **prior authorization**, **step therapy**, **covered indications**, **site of care**.
3. CITATION: If from uploaded policy — blockquote format:
   > "[exact source_quote from the document]" — [payer], [policy_id], [source_page]
   If from web search — cite the source URL and organization name.

Rules:
- Always lead with the uploaded policy data if it contains the answer.
- Use web search to supplement when: (a) the uploaded docs don't cover the question,
  (b) the user asks about a payer not in the loaded docs, or (c) the question is 
  about general medical benefit coverage standards.
- If comparing payers: bullet list, one bullet per payer.
- Never speculate. If data is missing: "Not found in loaded policies — here's what 
  I found online:" and then cite the web source.
- Be direct and confident. If Aetna requires 3 prior drug failures, say it plainly 
  and note that's unusually restrictive compared to industry norms.`;

// ─── Format uploaded policies ─────────────────────────────────────────────────

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function formatPolicies(policies: any[]): string {
  return policies.map((p, i) => {
    const indications = Array.isArray(p.covered_indications)
      ? p.covered_indications.join('; ') : (p.covered_indications ?? 'Not specified');
    const excluded = Array.isArray(p.excluded_indications)
      ? p.excluded_indications.join('; ') : (p.excluded_indications ?? 'None');

    return [
      `[Policy ${i + 1}]`,
      `Drug: ${p.drug_name ?? 'Unknown'} (brands: ${(p.brand_names ?? []).join(', ') || 'N/A'})`,
      `J-code: ${p.j_code ?? 'N/A'}`,
      `Payer: ${p.payer ?? 'Unknown'}`,
      `Policy ID: ${p.policy_id ?? 'N/A'}`,
      `Effective: ${p.effective_date ?? 'N/A'}`,
      `Coverage status: ${p.coverage_status ?? 'unknown'}`,
      `PA required: ${p.prior_auth_required ?? 'unknown'}`,
      `PA form: ${p.prior_auth_form ?? 'N/A'}`,
      `Covered indications: ${indications}`,
      `Excluded indications: ${excluded}`,
      `Step therapy required: ${p.step_therapy_required ?? 'unknown'}`,
      `Step therapy details: ${p.step_therapy_details ?? 'N/A'}`,
      `Site of care restriction: ${p.site_of_care_restriction ?? 'None'}`,
      `Quantity limits: ${p.quantity_limits ?? 'None'}`,
      `Source page: ${p.source_page ?? 'N/A'}`,
      `Source quote: "${p.source_quote ?? ''}"`,
      `File: ${p.source_file ?? 'unknown'}`,
    ].join('\n');
  }).join('\n\n');
}

// ─── Route ────────────────────────────────────────────────────────────────────

export async function POST(req: NextRequest) {
  try {
    const client = getClient();

    const body = await req.json();
    const { question, policies } = body as {
      question: string;
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      policies: any[];
    };

    if (!policies?.length) {
      return NextResponse.json({ error: 'Upload a policy PDF first.' }, { status: 400 });
    }
    if (!question?.trim()) {
      return NextResponse.json({ error: 'Question is required' }, { status: 400 });
    }

    const policyContext = formatPolicies(policies);

    const userPrompt = `Here is the structured data extracted from the user's uploaded policy documents:

${policyContext}

---
User question: ${question}

Instructions:
1. Check the uploaded policy data above FIRST. If it contains the answer, cite the source_quote directly.
2. If the uploaded data doesn't fully answer the question (e.g. different drug, different payer), 
   use web search to find the answer from credible sources: CMS.gov, payer coverage portals, 
   clinical guidelines, or FDA drug information.
3. Always tell the user which source you're drawing from.`;

    // Call Claude with web_search tool enabled
    const message = await client.messages.create({
      model: 'claude-sonnet-4-6',
      max_tokens: 800,
      system: SYSTEM_PROMPT,
      tools: [
        {
          type: 'web_search_20250305' as const,
          name: 'web_search',
        },
      ],
      messages: [{ role: 'user', content: userPrompt }],
    });

    // Collect all text blocks — cast via unknown to avoid SDK union type predicate mismatch
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const textBlocks = (message.content as any[])
      .filter((b) => b.type === 'text' && typeof b.text === 'string')
      .map((b) => b.text as string)
      .join('\n')
      .trim();

    const response = textBlocks || 'No response generated.';

    // Extract blockquote citation: > "quote" — meta
    const quoteMatch = response.match(/^>\s*"(.+?)"\s*—\s*(.+)$/m);
    if (quoteMatch) {
      const citationLine = quoteMatch[0];
      const answer = response.replace(citationLine, '').trim();
      const source = `${quoteMatch[1]} — ${quoteMatch[2]}`;
      return NextResponse.json({ answer, source_citation: source });
    }

    // Fallback: SOURCE: label format
    if (response.includes('SOURCE:')) {
      const idx = response.lastIndexOf('SOURCE:');
      return NextResponse.json({
        answer: response.slice(0, idx).trim(),
        source_citation: response.slice(idx + 'SOURCE:'.length).trim(),
      });
    }

    return NextResponse.json({ answer: response, source_citation: null });

  } catch (err: unknown) {
    if (err instanceof Anthropic.APIError && err.status === 401) {
      return NextResponse.json(
        { error: 'Invalid API key — set ANTHROPIC_API_KEY in .env.local and restart.' },
        { status: 500 }
      );
    }
    const msg = err instanceof Error ? err.message : 'Unknown error';
    console.error('[/api/ask]', msg);
    return NextResponse.json({ error: msg }, { status: 500 });
  }
}