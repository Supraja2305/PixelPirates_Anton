import anthropic
import pdfplumber
import json
import os
import re
import base64
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

policy_store = []

def extract_text_from_pdf(pdf_path: str) -> str:
    text = ''
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + '\n'
    except Exception as e:
        print(f"Error reading PDF: {e}")
    return text
def extract_text_from_file(file_path: str) -> str:
    """
    Handles PDF, HTML, TXT, PNG, JPG, DOCX files.
    Returns extracted text for Claude to process.
    """
    ext = Path(file_path).suffix.lower()

    # ── Plain text / HTML ──
    if ext in ['.txt', '.html', '.htm']:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()

    # ── Word documents ──
    elif ext in ['.docx']:
        try:
            import docx
            doc = docx.Document(file_path)
            return '\n'.join([p.text for p in doc.paragraphs])
        except ImportError:
            raise Exception("Run: pip install python-docx")

    # ── Images (PNG, JPG) — send to Claude vision ──
    elif ext in ['.png', '.jpg', '.jpeg']:
        with open(file_path, 'rb') as f:
            image_data = base64.standard_b64encode(f.read()).decode('utf-8')
        media_type = 'image/png' if ext == '.png' else 'image/jpeg'
        message = client.messages.create(
            model='claude-sonnet-4-5',
            max_tokens=3000,
            messages=[{
                'role': 'user',
                'content': [
                    {
                        'type': 'image',
                        'source': {
                            'type': 'base64',
                            'media_type': media_type,
                            'data': image_data,
                        }
                    },
                    {
                        'type': 'text',
                        'text': 'Extract ALL text from this medical policy document image. Return only the raw text, nothing else.'
                    }
                ]
            }]
        )
        return message.content[0].text

    # ── PDF ──
    elif ext == '.pdf':
        return extract_text_from_pdf(file_path)

    else:
        raise Exception(f"Unsupported file type: {ext}")

EXTRACTION_PROMPT = '''
You are an expert at reading health insurance medical benefit drug policy documents. 
Extract the following fields from the policy text and return ONLY valid JSON. 
No explanation, no markdown code fences, just raw JSON.

Fields to extract:
- payer, drug_name, drug_generic, hcpcs_code, coverage_status, pa_required, 
  step_therapy_required, step_therapy_detail, covered_indications, pa_criteria, 
  specialist_required, specialist_type, site_of_care_restrictions, 
  auth_duration_initial, auth_duration_renewal, effective_date, source_pa_sentence

Policy text:
{policy_text}
'''

def extract_policy_data(pdf_path: str) -> dict:
    raw_text = extract_text_from_file(pdf_path)
    if not raw_text.strip():
        raise ValueError("The PDF appears to be empty or unreadable.")

    truncated_text = raw_text[:80000]

    message = client.messages.create(
        model='claude-sonnet-4-5',
        max_tokens=2000,
        messages=[{'role': 'user', 'content': EXTRACTION_PROMPT.format(policy_text=truncated_text)}]
    )

    response_text = message.content[0].text.strip()

    # Robust JSON extraction (removes markdown backticks if Claude adds them)
    try:
        start_idx = response_text.find('{')
        end_idx = response_text.rfind('}') + 1
        json_str = response_text[start_idx:end_idx]
        result = json.loads(json_str)
        result['source_file'] = os.path.basename(pdf_path)
        return result
    except Exception as e:
        raise Exception(f"AI returned invalid data format: {str(e)}")

def store_policy(policy: dict):
    policy_store.append(policy)

def get_all_policies() -> list:
    return policy_store

def format_policies_for_context(policies: list) -> str:
    context = ''
    for p in policies:
        criteria = '; '.join(p.get('pa_criteria', [])) if isinstance(p.get('pa_criteria'), list) else 'N/A'
        context += f"\n---\nPayer: {p.get('payer')} | Drug: {p.get('drug_name')}\nPA Required: {p.get('pa_required')}\nCriteria: {criteria}\n"
    return context

def answer_policy_question(question: str, policies: list) -> dict:
    policy_context = format_policies_for_context(policies)
    prompt = f"Answer the user's question using this data:\n{policy_context}\nQuestion: {question}\nEnd with: SOURCE: [relevant sentence]"
    
    message = client.messages.create(
        model='claude-sonnet-4-5',
        max_tokens=800,
        messages=[{'role': 'user', 'content': prompt}]
    )

    response = message.content[0].text.strip()
    if 'SOURCE:' in response:
        parts = response.split('SOURCE:')
        return {'answer': parts[0].strip(), 'source_citation': parts[1].strip()}
    return {'answer': response, 'source_citation': None}
def format_policies_for_context(policies: list) -> str:
    """
    Takes a list of policy dictionaries (from the database)
    and formats them as readable text for Claude.
    """
    context = ''
    for p in policies:
        criteria = '; '.join(p.get('pa_criteria', [])) or 'Not specified'
        context += f'''
---
Payer: {p.get('payer', 'Unknown')}
Drug: {p.get('drug_name')} ({p.get('drug_generic')})
HCPCS Code: {p.get('hcpcs_code', 'Not listed')}
Coverage status: {p.get('coverage_status')}
PA required: {p.get('pa_required')}
Step therapy required: {p.get('step_therapy_required')}
Step therapy detail: {p.get('step_therapy_detail', 'N/A')}
PA criteria: {criteria}
Specialist required: {p.get('specialist_required')} — {p.get('specialist_type', 'N/A')}
Auth duration (initial): {p.get('auth_duration_initial', 'Not stated')}
Auth duration (renewal): {p.get('auth_duration_renewal', 'Not stated')}
Effective date: {p.get('effective_date', 'Not stated')}
Key PA sentence: "{p.get('source_pa_sentence', '')}"
'''
    return context


def answer_policy_question(question: str, policies: list) -> dict:
    """
    question: the user's plain-English question string
    policies: list of policy dicts fetched from the database
    returns: dict with 'answer' and 'source_citation' keys
    """
    # Format all policy data as readable text
    policy_context = format_policies_for_context(policies)

    prompt = f'''
You are a medical benefit drug policy analyst.
Answer the user's question clearly using only the policy data below.

Rules:
- Be specific — name the payer when comparing payers
- If policies differ across payers, explain the difference clearly
- Keep your answer under 150 words
- End your answer with exactly this format:
  SOURCE: [paste the most relevant sentence from the policy data]
- If the data does not contain the answer, say so clearly

Policy data:
{policy_context}

Question: {question}
'''

    message = client.messages.create(
        model='claude-sonnet-4-6',
        max_tokens=600,
        messages=[{'role': 'user', 'content': prompt}]
    )

    response = message.content[0].text.strip()

    # Split the answer from the source citation
    if 'SOURCE:' in response:
        parts = response.split('SOURCE:')
        answer = parts[0].strip()
        source = parts[1].strip()
    else:
        answer = response
        source = None

    return {
        'answer': answer,
        'source_citation': source
    }
