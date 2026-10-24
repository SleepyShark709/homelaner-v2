"""Local request-file client for the official REA MCP stdio launcher.

This preserves a single native analysis session instead of re-importing the EXE
for every CLI query. Files contain ordinary JSON-RPC method/params, and every
server response is saved unchanged. No Codex registration/settings are edited.
"""
import argparse
import datetime
import json
import os
from pathlib import Path
import queue
import subprocess
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--node', required=True)
parser.add_argument('--launcher', required=True)
parser.add_argument('--session', default=str(ROOT / 'research/rea-audit/session'))
parser.add_argument('--startup-timeout-ms', type=int, default=1800000)
parser.add_argument('--heap', default='2G')
parser.add_argument('--disabled-analyzers', default='')
args = parser.parse_args()
folder = Path(args.session)
folder.mkdir(parents=True, exist_ok=True)
inbox = folder / 'requests'
outbox = folder / 'responses'
inbox.mkdir(exist_ok=True)
outbox.mkdir(exist_ok=True)
env = os.environ.copy()
env['GHIDRA_INSTALL_DIR'] = str(ROOT / 'tools/rea-runtime/ghidra_12.1.4_PUBLIC')
env['JAVA_HOME'] = str(ROOT / 'tools/rea-runtime/jdk-21.0.12.1+1')
env['PATH'] = str(Path(args.node).parent) + os.pathsep + str(Path(env['JAVA_HOME']) / 'bin') + os.pathsep + env.get('PATH', '')
env['REA_GHIDRA_STARTUP_TIMEOUT_MS'] = str(args.startup_timeout_ms)
env['GHIDRA_HEADLESS_MAXMEM'] = args.heap
if args.disabled_analyzers:
    env['REA_GHIDRA_DISABLED_ANALYZERS'] = args.disabled_analyzers
proc = subprocess.Popen([args.node, args.launcher, 'mcp'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', env=env, cwd=ROOT, creationflags=subprocess.CREATE_NO_WINDOW)
messages = queue.Queue()
def read_stdout():
    for line in proc.stdout:
        try: messages.put(json.loads(line))
        except json.JSONDecodeError:
            with (folder / 'non-json-stdout.log').open('a', encoding='utf-8') as log: log.write(line)
    messages.put({'bridgeEOF': True})
def read_stderr():
    with (folder / 'server-stderr.log').open('a', encoding='utf-8') as log:
        for line in proc.stderr: log.write(line); log.flush()
threading.Thread(target=read_stdout, daemon=True).start()
threading.Thread(target=read_stderr, daemon=True).start()
serial = 0
def status(state, **extra):
    (folder / 'status.json').write_text(json.dumps({'state': state, 'pid': proc.pid, 'updatedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(), **extra}, indent=2), encoding='utf-8')
def send(value):
    proc.stdin.write(json.dumps(value) + '\n'); proc.stdin.flush()
def request(method, params):
    global serial
    serial += 1
    send({'jsonrpc': '2.0', 'id': serial, 'method': method, 'params': params})
    while True:
        message = messages.get(timeout=args.startup_timeout_ms / 1000 + 120)
        if message.get('bridgeEOF'): raise RuntimeError('REA server stdout closed')
        if message.get('id') == serial: return message
        with (folder / 'notifications.jsonl').open('a', encoding='utf-8') as log: log.write(json.dumps(message) + '\n')
try:
    status('initializing')
    result = request('initialize', {'protocolVersion': '2025-06-18', 'capabilities': {}, 'clientInfo': {'name': 'undefeated-readonly-audit', 'version': '1.0'}})
    (outbox / 'initialize.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    if 'error' in result: raise RuntimeError(result['error'])
    send({'jsonrpc': '2.0', 'method': 'notifications/initialized', 'params': {}})
    status('ready')
    print('REA MCP session ready; request files:', inbox, flush=True)
    while proc.poll() is None:
        pending = [path for path in sorted(inbox.glob('*.json')) if not (outbox / path.name).exists()]
        if not pending: time.sleep(0.25); continue
        for path in pending:
            data = json.loads(path.read_text(encoding='utf-8-sig'))
            if data['method'] == 'bridge/shutdown':
                (outbox / path.name).write_text('{"shutdown":true}', encoding='utf-8')
                raise SystemExit(0)
            status('request', request=path.name, method=data['method'], tool=data.get('params', {}).get('name'))
            result = request(data['method'], data.get('params', {}))
            (outbox / path.name).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
            status('ready', lastRequest=path.name)
            print('Saved', path.name, 'error=', 'error' in result or result.get('result', {}).get('isError', False), flush=True)
finally:
    if proc.poll() is None:
        proc.stdin.close()
        try: proc.wait(timeout=15)
        except subprocess.TimeoutExpired: proc.terminate(); proc.wait(timeout=15)
    status('closed', exitCode=proc.returncode)
