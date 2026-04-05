import json
from ai_engine import extract_policy_data

print('Testing Cigna PDF...')
result = extract_policy_data('pdfs/cigna_adalimumab.pdf')
print(json.dumps(result, indent=2))

print('\nTesting UHC PDF...')
result2 = extract_policy_data('pdfs/uhc_adalimumab.pdf')
print(json.dumps(result2, indent=2))

from ai_engine import answer_policy_question

# Pretend these came from the database
# In real usage Person 2 fetches these
mock_policies = [
    extract_policy_data('pdfs/cigna_adalimumab.pdf'),
    extract_policy_data('pdfs/uhc_adalimumab.pdf')
]

# Test the 3 demo queries
questions = [
    'Which health plans cover adalimumab?',
    'What prior authorization criteria does Cigna require for adalimumab?',
    'How does Cigna step therapy differ from UnitedHealthcare?'
]

for q in questions:
    print(f'\nQ: {q}')
    result = answer_policy_question(q, mock_policies)
    print(f'A: {result["answer"]}')
    print(f'Source: {result["source_citation"]}')

