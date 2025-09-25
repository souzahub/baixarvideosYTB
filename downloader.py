import yt_dlp
import os
from datetime import datetime
import sys
import threading
import uuid
import tempfile
import shutil
import time
import webbrowser
from flask import Flask, request, render_template_string, send_file, redirect, url_for, flash, jsonify

# Configuração de certificados (corrige SSL em Windows Server sem raízes atualizadas)
try:
    import certifi  # type: ignore
    os.environ.setdefault('SSL_CERT_FILE', certifi.where())
except Exception:
    pass

# Cria app Flask
app = Flask(__name__)
app.secret_key = 'replace-this-with-a-random-secret'

# Usa caminhos relativos ao executável quando empacotado (PyInstaller)
if getattr(sys, 'frozen', False):
	base_dir = os.path.dirname(sys.executable)
else:
	base_dir = os.path.dirname(os.path.abspath(__file__))

# Pastas
# Pasta de downloads persistentes (não usada quando modo efêmero estiver ativo)
output_dir = os.path.join(base_dir, 'downloads')
# Quando empacotado em --onefile, dados adicionados com --add-data
# são extraídos em sys._MEIPASS. Use-o se existir para localizar o ffmpeg.
if hasattr(sys, '_MEIPASS'):
    ffmpeg_dir = os.path.join(sys._MEIPASS, 'intalacao', 'ffmpeg', 'bin')
else:
    ffmpeg_dir = os.path.join(base_dir, 'intalacao', 'ffmpeg', 'bin')
os.makedirs(output_dir, exist_ok=True)

# Estado de progresso por job
job_lock = threading.Lock()
job_state = {}

# Configurações base do yt-dlp
_timestamp_boot = datetime.now().strftime('%Y%m%d_%H%M%S')
ydl_opts_base = {
	'outtmpl': os.path.join(output_dir, f'%(title)s_{_timestamp_boot}.%(ext)s'),
    'format': 'bestvideo+bestaudio/best',
    'merge_output_format': 'mp4',
    'noplaylist': True,
	'quiet': True,
	'no_warnings': True,
	'noprogress': True,
	'ffmpeg_location': ffmpeg_dir,
	'prefer_ffmpeg': True,
    # Permite desativar verificação de certificado via variável de ambiente (em último caso)
    'nocheckcertificate': os.environ.get('DISABLE_CERT_VERIFY', '0') in ('1', 'true', 'True'),
}

# Suporte opcional a proxy HTTP/HTTPS via variável de ambiente PROXY_URL
_proxy = os.environ.get('PROXY_URL')
if _proxy:
	ydl_opts_base['proxy'] = _proxy

HTML_INDEX = """
<!doctype html>
<html lang="pt-br">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Downloader</title>
    <style>
      body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; margin: 0; background: #0f172a; color: #e2e8f0; }
      .container { max-width: 720px; margin: 48px auto; padding: 24px; background: #111827; border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.4); }
      h1 { margin-top: 0; font-size: 24px; }
      form { display: flex; gap: 12px; }
      input[type=text] { flex: 1; padding: 12px 14px; border-radius: 8px; border: 1px solid #334155; background: #0b1220; color: #e2e8f0; }
      button { padding: 12px 18px; border-radius: 8px; border: 0; background: #22c55e; color: #0b1220; font-weight: 700; cursor: pointer; }
      button:disabled { background: #16a34a; opacity: .7; cursor: not-allowed; }
      .help { color: #94a3b8; font-size: 14px; margin-top: 8px; }
      .msg { margin-top: 16px; padding: 12px; border-radius: 8px; }
      .msg.error { background: #7f1d1d; color: #fecaca; }
      .msg.ok { background: #052e1a; color: #bbf7d0; }
      a { color: #60a5fa; }
    </style>
    <script>
      function onSubmitForm(e){
        const btn = document.getElementById('btn');
        btn.disabled = true; btn.textContent = 'Baixando...';
      }
    </script>
  </head>
  <body>
    <div class="container">
      <h1>Baixar Vídeos do Youtube</h1>
      {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
          {% for category, message in messages %}
            <div class="msg {{ 'error' if category == 'error' else 'ok' }}">{{ message }}</div>
          {% endfor %}
        {% endif %}
      {% endwith %}
      <form method="post" action="{{ url_for('start') }}" onsubmit="onSubmitForm(event)">
        <input type="text" name="url" placeholder="Cole a URL do vídeo" autocomplete="on" required>
        <button id="btn" type="submit">Baixar</button>
      </form>
      <!-- <div class="help">O arquivo será salvo em: {{ output_dir }}</div> -->
    </div>
  </body>
  </html>
"""

HTML_STATUS = """
<!doctype html>
<html lang="pt-br">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Progresso do download</title>
    <style>
      body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; margin: 0; background: #0f172a; color: #e2e8f0; }
      .container { max-width: 720px; margin: 48px auto; padding: 24px; background: #111827; border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.4); }
      h1 { margin-top: 0; font-size: 22px; }
      .bar { width: 100%; height: 16px; background: #0b1220; border: 1px solid #334155; border-radius: 8px; overflow: hidden; }
      .fill { height: 100%; background: linear-gradient(90deg, #22c55e, #86efac); width: 0%; transition: width .3s ease; }
      .row { margin-top: 12px; color: #94a3b8; }
      .ok { color: #bbf7d0; }
      a { color: #60a5fa; }
      .btn { display: inline-block; margin-top: 16px; padding: 10px 14px; background: #1f2937; border-radius: 8px; color: #e5e7eb; text-decoration: none; }
    </style>
    <script>
      const jobId = '{{ job_id }}';
      let finished = false;
      async function poll(){
        if(finished) return;
        try{
          const res = await fetch('/progress/' + jobId + '?_=' + Date.now());
          const data = await res.json();
          const pct = Math.max(0, Math.min(100, Math.floor((data.percent || 0))));
          document.getElementById('fill').style.width = pct + '%';
          document.getElementById('pct').textContent = pct + '%';
          document.getElementById('status').textContent = data.status || '...';
          document.getElementById('speed').textContent = data.speed || '';
          document.getElementById('eta').textContent = data.eta || '';
          if(data.status === 'finished'){
            finished = true;
            document.getElementById('done').style.display = 'block';
            document.getElementById('link').href = '/file/' + encodeURIComponent(jobId);
            document.getElementById('fname').textContent = data.filename;
          } else if(data.status === 'error'){
            finished = true;
            document.getElementById('err').style.display = 'block';
            document.getElementById('errmsg').textContent = data.error || 'Erro desconhecido';
          }
        }catch(e){}
        if(!finished) setTimeout(poll, 800);
      }
      window.addEventListener('load', poll);
    </script>
  </head>
  <body>
    <div class="container">
      <h1>Baixando...</h1>
      <div class="bar"><div id="fill" class="fill"></div></div>
      <div class="row"><strong id="pct">0%</strong> — <span id="status">iniciando</span></div>
      <div class="row">Velocidade: <span id="speed"></span> | ETA: <span id="eta"></span></div>
      <div id="done" class="row ok" style="display:none">✅ Concluído: <strong id="fname"></strong><br>
        <a id="link" class="btn" href="#">Baixar arquivo</a> <a class="btn" href="/">Novo download</a>
      </div>
      <div id="err" class="row" style="display:none">❌ <span id="errmsg"></span> — <a class="btn" href="/">Tentar novamente</a></div>
    </div>
  </body>
  </html>
"""

@app.route('/', methods=['GET'])
def index():
	return render_template_string(HTML_INDEX, output_dir=output_dir)


def _progress_hook_factory(job_id):
	def hook(d):
		with job_lock:
			js = job_state.get(job_id, {})
			status = d.get('status')
			if status == 'downloading':
				total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
				downloaded = d.get('downloaded_bytes') or 0
				percent = (downloaded / total * 100) if total else 0.0
				speed = d.get('speed')
				eta = d.get('eta')
				js.update({
					'status': 'downloading',
					'percent': percent,
					'speed': f"{speed/1024/1024:.2f} MB/s" if speed else None,
					'eta': f"{int(eta)}s" if isinstance(eta, (int, float)) else None,
				})
			elif status == 'finished':
				js.update({'status': 'processing'})
			job_state[job_id] = js
	return hook


def _run_download_job(job_id, url):
	ts = datetime.now().strftime('%Y%m%d_%H%M%S')

	# Pasta temporária por job (arquivo não persiste no servidor)
	job_tmp = tempfile.mkdtemp(prefix=f"job_{job_id}_")
	outtmpl = os.path.join(job_tmp, f'%(title)s_{ts}.%(ext)s')

	ydl_opts = dict(ydl_opts_base)
	ydl_opts['outtmpl'] = outtmpl
	ydl_opts['progress_hooks'] = [_progress_hook_factory(job_id)]

	try:
		with yt_dlp.YoutubeDL(ydl_opts) as ydl:
			info = ydl.extract_info(url, download=True)
			title = info.get('title') or 'Arquivo'
			filename = f"{title}_{ts}.mp4"
			file_path = os.path.join(job_tmp, filename)
			with job_lock:
				job_state[job_id] = {
					'status': 'finished',
					'percent': 100.0,
					'filename': filename,
					'file_path': file_path,
					'job_tmp': job_tmp,
				}
	except Exception as e:
		with job_lock:
			job_state[job_id] = {
				'status': 'error',
				'error': str(e),
			}


@app.route('/start', methods=['POST'])
def start():
	url = (request.form.get('url') or '').strip()
	if not url:
		flash('Informe uma URL válida.', 'error')
		return redirect(url_for('index'))

	job_id = str(uuid.uuid4())
	with job_lock:
		job_state[job_id] = {'status': 'queued', 'percent': 0.0}

	t = threading.Thread(target=_run_download_job, args=(job_id, url), daemon=True)
	t.start()
	return redirect(url_for('status_page', job_id=job_id))


@app.route('/status/<job_id>', methods=['GET'])
def status_page(job_id):
	return render_template_string(HTML_STATUS, job_id=job_id)


@app.route('/progress/<job_id>', methods=['GET'])
def progress(job_id):
	with job_lock:
		data = job_state.get(job_id) or {'status': 'unknown', 'percent': 0}
	return jsonify(data)


@app.route('/file/<job_id>', methods=['GET'])
def serve_file(job_id):
    # Envia o arquivo em memória e apaga após envio
    with job_lock:
        js = job_state.get(job_id)
    if not js or js.get('status') != 'finished':
        return ('Arquivo não disponível', 404)

    file_path = js.get('file_path')
    if not file_path or not os.path.exists(file_path):
        return ('Arquivo não encontrado', 404)

    # send_file com caminho direto
    resp = send_file(file_path, as_attachment=True, download_name=os.path.basename(file_path))

    # Agendar limpeza do temp assim que possível
    def _cleanup():
        try:
            tmp_dir = js.get('job_tmp')
            if tmp_dir and os.path.isdir(tmp_dir):
                shutil.rmtree(tmp_dir, ignore_errors=True)
        finally:
            with job_lock:
                job_state.pop(job_id, None)

    threading.Timer(3.0, _cleanup).start()
    return resp


def open_browser_later():
	try:
		webbrowser.open_new('http://127.0.0.1:5000/')
	except Exception:
		pass


if __name__ == '__main__':
	# Configurável por variáveis de ambiente
	host = os.environ.get('HOST', '0.0.0.0')
	try:
		port = int(os.environ.get('PORT', '5000'))
	except ValueError:
		port = 5000

	# Em modo EXE (frozen) não tenta abrir o navegador automaticamente
	if not getattr(sys, 'frozen', False) and host in ('127.0.0.1', 'localhost'):
		threading.Timer(0.8, open_browser_later).start()

	app.run(host=host, port=port, debug=False)