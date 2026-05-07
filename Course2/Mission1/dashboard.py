import http.server
import json
import re
import subprocess
from urllib.parse import urlparse

PARTITION_COUNT = 10
PORT = 8080

HTML = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>ZIP Cracker Dashboard</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@latest/tabler-icons.min.css">
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }

  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: #f4f6fb;
    color: #1a1d23;
    min-height: 100vh;
    padding: 24px;
  }

  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 24px;
  }

  .header-left h1 {
    font-size: 20px;
    font-weight: 600;
    color: #1a1d23;
  }

  .header-left p {
    font-size: 13px;
    color: #6b7280;
    margin-top: 2px;
  }

  .clock {
    font-size: 13px;
    color: #6b7280;
    background: #fff;
    border: 0.5px solid #e5e7eb;
    border-radius: 8px;
    padding: 6px 14px;
  }

  .stats-row {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    margin-bottom: 20px;
  }

  .stat-card {
    background: #fff;
    border: 0.5px solid #e5e7eb;
    border-radius: 12px;
    padding: 16px 20px;
  }

  .stat-label {
    font-size: 12px;
    color: #6b7280;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 6px;
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .stat-value {
    font-size: 26px;
    font-weight: 600;
    color: #1a1d23;
  }

  .stat-value.success { color: #16a34a; }
  .stat-value.running { color: #2563eb; }

  .password-banner {
    display: none;
    background: #f0fdf4;
    border: 1.5px solid #86efac;
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 20px;
    align-items: center;
    gap: 16px;
  }

  .password-banner.show { display: flex; }

  .banner-icon {
    width: 44px;
    height: 44px;
    background: #dcfce7;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 22px;
    color: #16a34a;
    flex-shrink: 0;
  }

  .banner-label {
    font-size: 12px;
    color: #16a34a;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .banner-password {
    font-size: 28px;
    font-weight: 700;
    color: #15803d;
    letter-spacing: 0.15em;
    font-family: 'SF Mono', 'Fira Code', monospace;
  }

  .section-title {
    font-size: 13px;
    font-weight: 600;
    color: #374151;
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .grid {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 10px;
    margin-bottom: 20px;
  }

  .node {
    background: #fff;
    border: 0.5px solid #e5e7eb;
    border-radius: 10px;
    padding: 14px;
    transition: border-color 0.2s, box-shadow 0.2s;
  }

  .node.running {
    border-color: #93c5fd;
    box-shadow: 0 0 0 3px #eff6ff;
  }

  .node.found {
    border-color: #86efac;
    box-shadow: 0 0 0 3px #f0fdf4;
  }

  .node.stopped {
    background: #fafafa;
    border-color: #f3f4f6;
  }

  .node-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 10px;
  }

  .node-id {
    font-size: 12px;
    font-weight: 600;
    color: #374151;
    font-family: 'SF Mono', 'Fira Code', monospace;
  }

  .badge {
    font-size: 10px;
    font-weight: 600;
    padding: 2px 7px;
    border-radius: 20px;
    letter-spacing: 0.04em;
  }

  .badge-running { background: #dbeafe; color: #1d4ed8; }
  .badge-found   { background: #dcfce7; color: #15803d; }
  .badge-stopped { background: #f3f4f6; color: #9ca3af; }
  .badge-waiting { background: #f9fafb; color: #d1d5db; }

  .node-prefix {
    font-size: 10px;
    color: #9ca3af;
    font-family: 'SF Mono', 'Fira Code', monospace;
    margin-bottom: 8px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .progress-track {
    height: 6px;
    background: #f3f4f6;
    border-radius: 99px;
    margin-bottom: 8px;
    overflow: hidden;
  }

  .progress-fill {
    height: 100%;
    border-radius: 99px;
    background: #3b82f6;
    transition: width 1.2s ease;
  }

  .node.found .progress-fill { background: #22c55e; }
  .node.stopped .progress-fill { background: #d1d5db; }

  .node-meta {
    display: flex;
    justify-content: space-between;
  }

  .node-attempts {
    font-size: 11px;
    color: #6b7280;
    font-family: 'SF Mono', 'Fira Code', monospace;
  }

  .node-speed {
    font-size: 11px;
    color: #6b7280;
  }

  .log-card {
    background: #fff;
    border: 0.5px solid #e5e7eb;
    border-radius: 12px;
    overflow: hidden;
  }

  .log-header {
    padding: 12px 16px;
    border-bottom: 0.5px solid #f3f4f6;
    font-size: 12px;
    font-weight: 600;
    color: #374151;
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .log-body {
    padding: 12px 16px;
    max-height: 180px;
    overflow-y: auto;
    font-family: 'SF Mono', 'Fira Code', monospace;
    font-size: 11.5px;
    line-height: 1.9;
    color: #6b7280;
  }

  .log-body::-webkit-scrollbar { width: 4px; }
  .log-body::-webkit-scrollbar-thumb { background: #e5e7eb; border-radius: 4px; }

  .log-found { color: #16a34a; font-weight: 600; }
  .log-progress { color: #2563eb; }

  .dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: #22c55e;
    animation: blink 1.4s infinite;
    display: inline-block;
  }

  @keyframes blink {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.3; }
  }
</style>
</head>
<body>
<h2 class="sr-only">ZIP Cracker 분산 탐색 대시보드</h2>

<header>
  <div class="header-left">
    <h1><i class="ti ti-lock-open" style="font-size:18px; vertical-align:-2px; margin-right:6px; color:#3b82f6" aria-hidden="true"></i>ZIP Cracker Dashboard</h1>
    <p>분산 브루트포스 실시간 모니터</p>
  </div>
  <div class="clock" id="clock">--:--:--</div>
</header>

<div id="password-banner" class="password-banner">
  <div class="banner-icon"><i class="ti ti-check" aria-hidden="true"></i></div>
  <div>
    <div class="banner-label">암호 해제 완료</div>
    <div class="banner-password" id="banner-pw">------</div>
  </div>
</div>

<div class="stats-row">
  <div class="stat-card">
    <div class="stat-label"><i class="ti ti-server" style="font-size:14px" aria-hidden="true"></i> 실행 중</div>
    <div class="stat-value running" id="stat-running">0</div>
  </div>
  <div class="stat-card">
    <div class="stat-label"><i class="ti ti-refresh" style="font-size:14px" aria-hidden="true"></i> 총 시도</div>
    <div class="stat-value" id="stat-total">0</div>
  </div>
  <div class="stat-card">
    <div class="stat-label"><i class="ti ti-speedboat" style="font-size:14px" aria-hidden="true"></i> 전체 속도</div>
    <div class="stat-value" id="stat-speed">0/s</div>
  </div>
  <div class="stat-card">
    <div class="stat-label"><i class="ti ti-clock" style="font-size:14px" aria-hidden="true"></i> 경과 시간</div>
    <div class="stat-value" id="stat-elapsed">0s</div>
  </div>
</div>

<div class="section-title">
  <span class="dot"></span> 컨테이너 상태
</div>
<div class="grid" id="grid"></div>

<div class="log-card">
  <div class="log-header">
    <i class="ti ti-terminal" style="font-size:14px" aria-hidden="true"></i> 실시간 로그
  </div>
  <div class="log-body" id="log-body"></div>
</div>

<script>
function fmt(n) {
  if (n >= 1000000) return (n/1000000).toFixed(1) + 'M';
  if (n >= 1000) return (n/1000).toFixed(1) + 'K';
  return String(Math.round(n));
}

let logLines = [];
let prevSpeeds = {};

setInterval(() => {
  document.getElementById('clock').textContent = new Date().toLocaleTimeString('ko-KR');
}, 1000);

async function poll() {
  try {
    const res = await fetch('/api/status');
    const containers = await res.json();
    render(containers);
  } catch(e) {}
}

function render(containers) {
  const totalAttempts = containers.reduce((s, c) => s + (c.repeat_count || 0), 0);
  const running = containers.filter(c => c.state === 'running').length;
  const maxElapsed = Math.max(...containers.map(c => c.elapsed || 0));
  const found = containers.find(c => c.state === 'found');

  const totalSpeed = containers.reduce((s, c) => {
    return s + (c.elapsed > 0 ? Math.round(c.repeat_count / c.elapsed) : 0);
  }, 0);

  document.getElementById('stat-running').textContent = running;
  document.getElementById('stat-total').textContent = fmt(totalAttempts);
  document.getElementById('stat-speed').textContent = fmt(totalSpeed) + '/s';
  document.getElementById('stat-elapsed').textContent = maxElapsed.toFixed(1) + 's';

  if (found) {
    document.getElementById('password-banner').classList.add('show');
    document.getElementById('banner-pw').textContent = found.password;
    document.getElementById('stat-running').textContent = 'CRACKED';
    document.getElementById('stat-running').classList.add('success');
  }

  const grid = document.getElementById('grid');
  grid.innerHTML = containers.map(c => {
    const total = (c.total_prefixes || 1) * 46656;
    const pct = Math.min((c.repeat_count / total) * 100, 100).toFixed(1);
    const speed = c.elapsed > 0 ? Math.round(c.repeat_count / c.elapsed) : 0;

    let badgeClass = 'badge-waiting', badgeText = 'WAIT', nodeClass = '';
    if (c.state === 'running') { badgeClass = 'badge-running'; badgeText = 'RUN'; nodeClass = 'running'; }
    if (c.state === 'found')   { badgeClass = 'badge-found';   badgeText = 'FOUND'; nodeClass = 'found'; }
    if (c.state === 'stopped') { badgeClass = 'badge-stopped'; badgeText = 'DONE'; nodeClass = 'stopped'; }

    return `<div class="node ${nodeClass}">
      <div class="node-header">
        <span class="node-id">NODE ${String(c.index).padStart(2,'0')}</span>
        <span class="badge ${badgeClass}">${badgeText}</span>
      </div>
      <div class="node-prefix">${c.prefix_range || '---'}</div>
      <div class="progress-track">
        <div class="progress-fill" style="width:${pct}%"></div>
      </div>
      <div class="node-meta">
        <span class="node-attempts">${fmt(c.repeat_count || 0)}</span>
        <span class="node-speed">${fmt(speed)}/s</span>
      </div>
    </div>`;
  }).join('');

  containers.forEach(c => {
    if (c.state === 'found') {
      const line = { text: `[NODE ${c.index}] 암호 해제 성공 → ${c.password}`, cls: 'log-found' };
      if (!logLines.find(l => l.text === line.text)) logLines.unshift(line);
    } else if (c.repeat_count > 0) {
      const speed = c.elapsed > 0 ? Math.round(c.repeat_count / c.elapsed) : 0;
      const line = { text: `[NODE ${c.index}] ${fmt(c.repeat_count)}회 시도 | ${fmt(speed)}/s | ${c.elapsed.toFixed(1)}s`, cls: 'log-progress', key: c.index };
      logLines = logLines.filter(l => l.key !== c.index);
      logLines.unshift(line);
    }
  });

  document.getElementById('log-body').innerHTML = logLines.slice(0, 40).map(l =>
    `<div class="${l.cls}">&gt; ${l.text}</div>`
  ).join('');
}

setInterval(poll, 2000);
poll();
</script>
</body>
</html>"""


PASSWORD_FILE = 'output/password.txt'


def read_password_file():
    try:
        with open(PASSWORD_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            return content if len(content) == 6 else None
    except (FileNotFoundError, OSError):
        return None


def parse_container_logs(index):
    try:
        result = subprocess.run(
            ['docker', 'logs', f'cracker_{index}'],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
        )
        logs = result.stdout + result.stderr
    except Exception:
        return {'index': index, 'state': 'waiting', 'repeat_count': 0,
                'elapsed': 0, 'prefix_range': None, 'total_prefixes': None,
                'password': None}

    status = {
        'index': index,
        'state': 'waiting',
        'repeat_count': 0,
        'elapsed': 0.0,
        'prefix_range': None,
        'total_prefixes': None,
        'password': None,
    }

    for line in logs.split('\n'):
        if '분산 암호 해제 시작' in line:
            status['state'] = 'running'

        m = re.search(r'담당 prefix: (\w+) ~ (\w+) \((\d+)개\)', line)
        if m:
            status['prefix_range'] = f"{m.group(1)} ~ {m.group(2)}"
            status['total_prefixes'] = int(m.group(3))

        m = re.search(r'반복 회수: (\d+) \| 진행 시간: ([\d.]+)초', line)
        if m:
            status['repeat_count'] = int(m.group(1))
            status['elapsed'] = float(m.group(2))

        m = re.search(r'비밀번호: (\w+)', line)
        if m:
            status['password'] = m.group(1)
            status['state'] = 'found'

        if '다른 컨테이너가 정답을 찾아 중단' in line or '담당 구간 탐색 완료' in line:
            status['state'] = 'stopped'

    return status


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        path = urlparse(self.path).path

        if path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML.encode('utf-8'))

        elif path == '/api/status':
            statuses = [parse_container_logs(i) for i in range(PARTITION_COUNT)]
            file_password = read_password_file()
            has_found = any(s['state'] == 'found' for s in statuses)
            if file_password and not has_found:
                statuses[0]['state'] = 'found'
                statuses[0]['password'] = file_password
            body = json.dumps(statuses, ensure_ascii=False).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(body)

        else:
            self.send_response(404)
            self.end_headers()


if __name__ == '__main__':
    server = http.server.ThreadingHTTPServer(('0.0.0.0', PORT), Handler)
    print(f'대시보드 실행 중 → http://localhost:{PORT}')
    print('종료: Ctrl+C')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n종료')