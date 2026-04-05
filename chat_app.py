import os
import tempfile
from flask import Flask, request, jsonify, render_template_string
from ai_engine import extract_policy_data, answer_policy_question, store_policy, get_all_policies

app = Flask(__name__)

# Full restored HTML including the Welcome/Example Section
HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>Anton Rx — Policy Chat</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: -apple-system, sans-serif; background: #f0f2f5; height: 100vh; display: flex; flex-direction: column; }
    header { background: #1a3c6e; color: white; padding: 14px 24px; flex-shrink: 0; }
    .main { display: flex; flex: 1; overflow: hidden; }
    .sidebar { width: 280px; background: white; border-right: 1px solid #e2e8f0; display: flex; flex-direction: column; }
    .upload-btn-wrap { padding: 16px; }
    .upload-btn { width: 100%; background: #1a3c6e; color: white; border: none; border-radius: 10px; padding: 12px; cursor: pointer; font-weight: 600; }
    .drop-zone { margin: 0 16px 12px; border: 2px dashed #cbd5e1; border-radius: 10px; padding: 16px; text-align: center; color: #94a3b8; font-size: 0.8rem; }
    #upload-status { margin: 0 16px 8px; font-size: 0.8rem; min-height: 20px; }
    .policy-list { flex: 1; overflow-y: auto; padding: 16px; }
    .policy-card { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px; margin-bottom: 8px; font-size: 0.8rem; }
    .chat-area { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
    #messages { flex: 1; overflow-y: auto; padding: 24px; display: flex; flex-direction: column; gap: 16px; }
    
    /* Welcome/Example styling */
    .welcome { text-align: center; padding: 48px 24px; color: #94a3b8; }
    .welcome h2 { font-size: 1.3rem; color: #475569; margin-bottom: 8px; }
    .examples { margin-top: 20px; display: flex; flex-direction: column; gap: 8px; max-width: 500px; margin-left: auto; margin-right: auto; }
    .example-q { background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; font-size: 0.85rem; cursor: pointer; transition: 0.2s; text-align: left; }
    .example-q:hover { background: #eff6ff; border-color: #1a3c6e; color: #1a3c6e; }

    .msg { display: flex; gap: 10px; max-width: 85%; }
    .msg.user { align-self: flex-end; flex-direction: row-reverse; }
    .bubble { padding: 12px; border-radius: 16px; font-size: 0.88rem; background: white; border: 1px solid #e2e8f0; line-height: 1.5; }
    .msg.user .bubble { background: #1a3c6e; color: white; border-bottom-right-radius: 4px; }
    .msg.bot .bubble { border-bottom-left-radius: 4px; }
    .source-block { margin-top: 10px; padding: 8px; background: #f8fafc; border-left: 3px solid #1a3c6e; font-size: 0.75rem; font-style: italic; }
    
    .input-bar { padding: 16px; background: white; border-top: 1px solid #e2e8f0; display: flex; gap: 10px; }
    #question-input { flex: 1; border: 1px solid #e2e8f0; border-radius: 10px; padding: 10px; resize: none; font-family: inherit; }
    #send-btn { background: #1a3c6e; color: white; border: none; border-radius: 10px; padding: 0 20px; cursor: pointer; font-weight: 600; }
  </style>
</head>
<body>
<header><h1>🏥 Anton Rx — Medical Policy Chat</h1></header>
<div class="main">
  <aside class="sidebar">
    <div class="upload-btn-wrap">
      <button class="upload-btn" onclick="document.getElementById('file-input').click()">📄 Upload PDF, Word or PNG</button>
      <input type="file" id="file-input" accept=".pdf,.html,.htm,.txt,.png,.jpg,.jpeg,.docx" multiple style="display:none;" />
    </div>
    <div class="drop-zone" id="drop-zone">or drag &amp; drop PDF, Word, or PNG here</div>
    <div id="upload-status"></div>
    <div class="policy-list" id="policy-cards"></div>
  </aside>

  <div class="chat-area">
    <div id="messages">
      <div class="welcome" id="welcome-screen">
        <h2>Medical Benefit Drug Policy Assistant</h2>
        <p>Upload policy PDFs from the sidebar, then ask questions.</p>
        <div class="examples">
          <button class="example-q" onclick="askExample(this)">Which plans cover adalimumab under the medical benefit?</button>
          <button class="example-q" onclick="askExample(this)">What prior authorization criteria does Cigna require?</button>
          <button class="example-q" onclick="askExample(this)">How does step therapy differ between payers?</button>
        </div>
      </div>
    </div>
    <div class="input-bar">
      <textarea id="question-input" rows="1" placeholder="Ask a question about any uploaded policy..."></textarea>
      <button id="send-btn" onclick="sendQuestion()">Send ↑</button>
    </div>
  </div>
</div>

<script>
  // Restored: Click example to send it
  function askExample(btn) {
    document.getElementById('question-input').value = btn.innerText;
    sendQuestion();
  }

  const fileInput = document.getElementById('file-input');
  fileInput.addEventListener('change', async () => {
    const files = Array.from(fileInput.files);
    for (const file of files) { await uploadFile(file); }
    fileInput.value = '';
  });

  async function uploadFile(file) {
    const status = document.getElementById('upload-status');
    status.innerHTML = `⏳ Processing ${file.name}...`;
    const formData = new FormData();
    formData.append('file', file);
    try {
      const res = await fetch('/upload', { method: 'POST', body: formData });
      const data = await res.json();
      if (data.error) throw new Error(data.error);
      status.style.color = "green";
      status.innerHTML = `✅ ${file.name} loaded`;
      addPolicyCard(data.policy);
    } catch (e) {
      status.style.color = "red";
      status.innerHTML = `❌ Error: ${e.message}`;
    }
  }

  function addPolicyCard(p) {
    const card = document.createElement('div');
    card.className = 'policy-card';
    card.innerHTML = `<strong>${p.drug_name || 'Policy'}</strong><br><small>${p.payer || 'Unknown'}</small>`;
    document.getElementById('policy-cards').appendChild(card);
  }

  async function sendQuestion() {
    const input = document.getElementById('question-input');
    const question = input.value.trim();
    if (!question) return;

    if (document.getElementById('welcome-screen')) document.getElementById('welcome-screen').remove();

    appendMsg('user', question);
    input.value = '';

    try {
      const res = await fetch('/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question })
      });
      const data = await res.json();
      if (data.error) throw new Error(data.error);
      
      let botHtml = data.answer;
      if (data.source_citation) {
        botHtml += `<div class="source-block">Source: ${data.source_citation}</div>`;
      }
      appendMsg('bot', botHtml);
    } catch (e) {
      appendMsg('bot', `<span style="color:red">Error: ${e.message}</span>`);
    }
  }

  function renderMarkdown(text) {
    let t = text
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

    // Tables
    const lines = t.split('\n');
    let out = ''; let inTable = false; let isFirstRow = true;
    for (const line of lines) {
      if (line.trim().startsWith('|')) {
        if (line.match(/^\s*\|[-| :]+\|\s*$/)) { isFirstRow = false; continue; }
        if (!inTable) { out += '<table style="border-collapse:collapse;width:100%;margin:10px 0;font-size:0.82rem;">'; inTable = true; isFirstRow = true; }
        const tag = isFirstRow ? 'th' : 'td';
        const bg = isFirstRow ? '#1a3c6e' : 'white';
        const color = isFirstRow ? 'white' : '#1e293b';
        const cells = line.split('|').slice(1,-1);
        out += '<tr>' + cells.map(c => `<${tag} style="border:1px solid #e2e8f0;padding:6px 10px;background:${bg};color:${color}">${c.trim()}</${tag}>`).join('') + '</tr>';
        isFirstRow = false;
      } else {
        if (inTable) { out += '</table>'; inTable = false; }
        let l = line
          .replace(/^## (.+)/, '<h3 style="margin:10px 0 4px;color:#1a3c6e;font-size:0.95rem">$1</h3>')
          .replace(/^# (.+)/,  '<h2 style="margin:10px 0 4px;color:#1a3c6e">$1</h2>')
          .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
          .replace(/\*(.+?)\*/g, '<em>$1</em>')
          .replace(/^[-•] (.+)/, '<li style="margin-left:16px">$1</li>');
        out += l ? l + (l.startsWith('<h') || l.startsWith('<li') ? '' : '<br/>') : '<br/>';
      }
    }
    if (inTable) out += '</table>';
    return out;
  }

  function appendMsg(role, html) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `msg ${role}`;
    const content = role === 'bot' ? renderMarkdown(html) : `<span>${html.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')}</span>`;
    msgDiv.innerHTML = `<div class="bubble">${content}</div>`;
    const msgBox = document.getElementById('messages');
    msgBox.appendChild(msgDiv);
    msgBox.scrollTop = msgBox.scrollHeight;
  }
</script>
</body>
</html>
"""
@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"error": "No file sent"}), 400

    file = request.files["file"]
    
    ALLOWED = ['.pdf', '.png', '.jpg', '.jpeg', '.docx']
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED:
        return jsonify({"error": f"Unsupported file type: {ext}"}), 400

    # Preserve the real extension so ai_engine knows what type it is
    fd, tmp_path = tempfile.mkstemp(suffix=os.path.splitext(file.filename)[1].lower())
    try:
        os.close(fd)
        file.save(tmp_path)
        policy = extract_policy_data(tmp_path)
        store_policy(policy)
        return jsonify({"policy": policy})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json()
    policies = get_all_policies()
    if not policies:
        return jsonify({"error": "Upload a PDF first."}), 400
    try:
        result = answer_policy_question(data.get("question"), policies)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)