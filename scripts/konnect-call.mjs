#!/usr/bin/env node
// konnect-call.mjs - minimal stdio MCP client for Konnect (KiCad MCP server).
//
// Use it when the MCP client in your agent does not refresh its tool list after
// `load_toolset`, or when you want a reproducible request/response record.
// Node built-ins only; no npm install needed.
//
// Usage:
//   node scripts/konnect-call.mjs [options] request.json response.json
//
// Options (each falls back to an environment variable):
//   --exe <path>       Konnect executable              (KONNECT_EXE, required)
//   --config <path>    Konnect config.toml             (KONNECT_CONFIG, required)
//   --client <name>    passed to Konnect as --client   (KONNECT_CLIENT, optional)
//   --timeout <ms>     per-request timeout, default 120000 (KONNECT_TIMEOUT_MS)
//   -h, --help         print this help
//
// request.json:
//   {
//     "toolsets": ["pcb_board"],          // loaded in order with load_toolset
//     "listTools": true,                  // save tools/list (real input schemas)
//     "calls": [{"name": "get_board_info", "arguments": {"board": "/abs/path/x.kicad_pcb"}}],
//     "continueOnError": false            // default: stop at the first isError
//   }
//
// The server runs with the current working directory. Pass absolute design
// paths in every call. response.json records every call and result plus server
// stderr. isError=false only means the call returned: still read the inner
// result (success, source=ipc/file, ipc_available, diagnostics).
// Never auto-replay a timed-out or failed mutation; check the file state first.

import { spawn } from 'node:child_process';
import { createInterface } from 'node:readline';
import { readFile, writeFile, access } from 'node:fs/promises';
import { resolve } from 'node:path';

const USAGE = `Usage: node scripts/konnect-call.mjs [--exe PATH] [--config PATH] [--client NAME] [--timeout MS] request.json response.json

  --exe      Konnect executable (or env KONNECT_EXE)
  --config   Konnect config.toml (or env KONNECT_CONFIG)
  --client   optional value passed as Konnect --client (or env KONNECT_CLIENT)
  --timeout  per-request timeout in ms, default 120000 (or env KONNECT_TIMEOUT_MS)

request.json: {"toolsets": [...], "listTools": true, "calls": [{"name": "...", "arguments": {...}}], "continueOnError": false}`;

function fail(message, code = 2) {
  console.error(`konnect-call: ${message}`);
  process.exit(code);
}

function parseArgs(argv) {
  const options = {};
  const positional = [];
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === '-h' || arg === '--help') { console.log(USAGE); process.exit(0); }
    if (['--exe', '--config', '--client', '--timeout'].includes(arg)) {
      const value = argv[++i];
      if (value === undefined || value.startsWith('--')) fail(`${arg} needs a value.\n\n${USAGE}`);
      options[arg.slice(2)] = value;
    } else if (arg.startsWith('--')) {
      fail(`unknown option ${arg}\n\n${USAGE}`);
    } else {
      positional.push(arg);
    }
  }
  return { options, positional };
}

async function requireFile(path, label, hint) {
  try { await access(path); }
  catch { fail(`${label} not found: ${path}\n${hint}`); }
}

const { options, positional } = parseArgs(process.argv.slice(2));
const [requestPath, responsePath] = positional;
if (!requestPath || !responsePath || positional.length > 2) fail(`expected request.json and response.json.\n\n${USAGE}`);

const exeArg = options.exe || process.env.KONNECT_EXE;
const configArg = options.config || process.env.KONNECT_CONFIG;
const client = options.client || process.env.KONNECT_CLIENT || '';
const timeoutMs = Number(options.timeout || process.env.KONNECT_TIMEOUT_MS || 120000);
if (!exeArg) fail('Konnect executable not set. Pass --exe PATH or set KONNECT_EXE to the pinned konnect binary.');
if (!configArg) fail('Konnect config not set. Pass --config PATH or set KONNECT_CONFIG (see scripts/konnect/config.example.toml).');
if (!Number.isFinite(timeoutMs) || timeoutMs <= 0) fail('--timeout / KONNECT_TIMEOUT_MS must be a positive number of milliseconds.');

const executable = resolve(exeArg);
const config = resolve(configArg);
await requireFile(executable, 'Konnect executable', 'Download the pinned release asset and verify its SHA256 first.');
await requireFile(config, 'Konnect config', 'Copy scripts/konnect/config.example.toml and fill in local paths.');

let request;
try { request = JSON.parse(await readFile(requestPath, 'utf8')); }
catch (error) { fail(`cannot read request ${requestPath}: ${error.message}`); }
if (request === null || typeof request !== 'object' || Array.isArray(request)) fail('request.json must be a JSON object.');

const serverArgs = [...(client ? ['--client', client] : []), '--config', config];
const child = spawn(executable, serverArgs, {
  cwd: process.cwd(), windowsHide: true, stdio: ['pipe', 'pipe', 'pipe'],
  env: { ...process.env },
});
let sequence = 0;
const pending = new Map();
const output = { executable, args: serverArgs, cwd: process.cwd(), calls: [] };
let stderr = '';
child.stderr.on('data', data => { stderr += data; });
function failPending(error) {
  for (const { reject, timer } of pending.values()) { clearTimeout(timer); reject(error); }
  pending.clear();
}
child.on('error', failPending);
child.stdin.on('error', failPending);
child.on('exit', (code, signal) => failPending(new Error(`Server exited: ${code ?? signal}`)));
const lines = createInterface({ input: child.stdout });
lines.on('line', line => {
  let message;
  try { message = JSON.parse(line); }
  catch { failPending(new Error(`Non-JSON server stdout: ${line.slice(0, 200)}`)); return; }
  if (message.id === undefined) return; // Server notifications.
  const item = pending.get(message.id);
  if (!item) return;
  pending.delete(message.id);
  clearTimeout(item.timer);
  if (message.error) item.reject(new Error(JSON.stringify(message.error)));
  else item.resolve(message.result);
});
function rpc(method, params) {
  const id = ++sequence;
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      pending.delete(id);
      reject(new Error(`Timed out after ${timeoutMs} ms: ${method}${params?.name ? ` ${params.name}` : ''}`));
    }, timeoutMs);
    pending.set(id, { resolve, reject, timer });
    child.stdin.write(JSON.stringify({ jsonrpc: '2.0', id, method, params }) + '\n');
  });
}
try {
  output.initialize = await rpc('initialize', {
    protocolVersion: '2025-03-26', capabilities: {},
    clientInfo: { name: 'pcb-agent-workflow-konnect-call', version: '1.0.0' },
  });
  child.stdin.write(JSON.stringify({ jsonrpc: '2.0', method: 'notifications/initialized' }) + '\n');
  for (const name of request.toolsets || []) {
    const result = await rpc('tools/call', { name: 'load_toolset', arguments: { name } });
    output.calls.push({ name: 'load_toolset', arguments: { name }, result });
    if (result.isError) throw new Error(`Unable to load toolset: ${name}`);
  }
  if (request.listTools) output.tools = await rpc('tools/list', {});
  for (const call of request.calls || []) {
    const result = await rpc('tools/call', call);
    output.calls.push({ ...call, result });
    console.log(`${call.name}: ${result.isError ? 'ERROR' : 'returned (inspect evidence)'}`);
    if (result.isError && !request.continueOnError) throw new Error(`Tool failed: ${call.name}`);
  }
} catch (error) {
  output.error = String(error);
  console.error(`konnect-call: ${output.error}`);
  process.exitCode = 1;
} finally {
  child.stdin.end();
  if (child.exitCode === null && child.signalCode === null) {
    await Promise.race([
      new Promise(resolve => child.once('exit', resolve)),
      new Promise(resolve => setTimeout(resolve, 1500)),
    ]);
    if (child.exitCode === null && child.signalCode === null) child.kill();
  }
  lines.close();
  output.stderr = stderr;
  await writeFile(responsePath, JSON.stringify(output, null, 2) + '\n');
}
