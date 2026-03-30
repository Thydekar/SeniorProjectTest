from flask import Flask, render_template, request, Response, jsonify, stream_with_context
import requests
import json
import io
import os

try:
    from PIL import Image
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

try:
    import fitz  # PyMuPDF
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024  # 32MB max upload

# ── Config ────────────────────────────────────────────────────────────────────
NGROK_URL       = "https://ona-overcritical-extrinsically.ngrok-free.dev"
OLLAMA_CHAT_URL = f"{NGROK_URL}/api/chat"
OLLAMA_TAGS_URL = f"{NGROK_URL}/api/tags"
USERNAME        = "dgeurts"
PASSWORD        = "thaidakar21"
OCR_CONFIG      = r"--oem 3 --psm 6"

MODEL_MAP = {
    "Assignment Generation": "spartan-generator",
    "Assignment Grader":     "spartan-grader",
    "AI Content Detector":   "spartan-detector",
    "Student Chatbot":       "spartan-student",
}

AUTH = (USERNAME, PASSWORD)

TEXT_EXTENSIONS = {
    'txt', 'js', 'html', 'htm', 'css', 'py', 'java', 'c', 'cpp', 'h', 'hpp',
    'json', 'xml', 'md', 'ts', 'tsx', 'jsx', 'php', 'rb', 'go', 'rs',
    'swift', 'kt', 'sql', 'sh', 'bash', 'yaml', 'yml', 'toml', 'ini',
    'cfg', 'conf', 'csv', 'log', 'r', 'scala', 'pl', 'lua', 'dart',
    'vue', 'svelte', 'graphql', 'env', 'makefile', 'dockerfile'
}
IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'tif', 'webp'}


# ── Routes ────────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html', model_map=MODEL_MAP)


@app.route('/api/status')
def check_status():
    statuses = {}
    try:
        resp = requests.get(OLLAMA_TAGS_URL, auth=AUTH, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            available = [m.get('name', '') for m in data.get('models', [])]
            for display_name, model_id in MODEL_MAP.items():
                statuses[model_id] = any(
                    model_id in m or m.startswith(model_id) for m in available
                )
        else:
            for model_id in MODEL_MAP.values():
                statuses[model_id] = False
    except Exception:
        for model_id in MODEL_MAP.values():
            statuses[model_id] = False
    return jsonify(statuses)


@app.route('/api/chat', methods=['POST'])
def chat():
    body = request.get_json(force=True)
    model    = body.get('model', '')
    messages = body.get('messages', [])

    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
    }

    def generate():
        try:
            with requests.post(
                OLLAMA_CHAT_URL,
                json=payload,
                auth=AUTH,
                stream=True,
                timeout=180,
            ) as resp:
                if resp.status_code != 200:
                    err = {"content": f"[ERROR] Server returned {resp.status_code}", "done": True}
                    yield f"data: {json.dumps(err)}\n\n"
                    return
                for line in resp.iter_lines():
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                        content = chunk.get('message', {}).get('content', '')
                        done    = chunk.get('done', False)
                        yield f"data: {json.dumps({'content': content, 'done': done})}\n\n"
                        if done:
                            break
                    except json.JSONDecodeError:
                        continue
        except requests.exceptions.Timeout:
            yield f"data: {json.dumps({'content': '[ERROR] Request timed out.', 'done': True})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'content': f'[ERROR] {str(e)}', 'done': True})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control':   'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection':      'keep-alive',
        }
    )


@app.route('/api/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    f        = request.files['file']
    filename = f.filename or 'unknown'
    ext      = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''

    # ── Text-based file ───────────────────────────────────────────────────────
    if ext in TEXT_EXTENSIONS or ext == 'makefile' or filename.lower() == 'dockerfile':
        try:
            content = f.read().decode('utf-8', errors='replace')
            return jsonify({
                'type':     'text',
                'ext':      ext or 'txt',
                'filename': filename,
                'content':  content,
            })
        except Exception as e:
            return jsonify({'error': f'Could not read file: {e}'}), 400

    # ── Image → OCR ───────────────────────────────────────────────────────────
    elif ext in IMAGE_EXTENSIONS:
        if not OCR_AVAILABLE:
            return jsonify({'error': 'OCR not available (pytesseract/Pillow not installed)'}), 500
        try:
            img  = Image.open(io.BytesIO(f.read()))
            text = pytesseract.image_to_string(img, config=OCR_CONFIG)
            return jsonify({
                'type':     'ocr',
                'filename': filename,
                'content':  text.strip(),
            })
        except Exception as e:
            return jsonify({'error': f'OCR failed: {e}'}), 400

    # ── PDF ───────────────────────────────────────────────────────────────────
    elif ext == 'pdf':
        if not PDF_AVAILABLE:
            return jsonify({'error': 'PDF support not available (PyMuPDF not installed)'}), 500
        try:
            raw = f.read()
            doc = fitz.open(stream=raw, filetype='pdf')
            text = '\n'.join(page.get_text() for page in doc)
            return jsonify({
                'type':     'text',
                'ext':      'pdf',
                'filename': filename,
                'content':  text.strip(),
            })
        except Exception as e:
            return jsonify({'error': f'PDF extraction failed: {e}'}), 400

    else:
        return jsonify({'error': f'Unsupported file type: .{ext}'}), 400


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, port=port, threaded=True)
