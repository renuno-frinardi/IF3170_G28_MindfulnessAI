import { createViewer } from '../viewer3d.js';
import { drawLineChart } from '../charts.js';

const $ = id => document.getElementById(id);

const app = {
 envelope: null,
 runIndex: 0,
 which: 'final',
 chartIndex: 0,
 colorMode: 'value',
 highlightId: null,
};

const examples = ['hc_steepest', 'hc_sideways', 'hc_stochastic', 'hc_restart', 'sa', 'ga'];

const STATE_LABELS = { init: 'Initial', final: 'Final', best: 'Best' };

const EXAMPLE_TAILS = {
 HC_STEEPEST: '50',
 HC_SIDEWAYS: '50 100',
 HC_STOCHASTIC: '1000',
 HC_RESTART: '10 50',
 SA: '100 0.95 0.01',
 GA: '',
};

let viewer = null;

function format(value) {
 if (value === null || value === undefined) return '—';
 if (Array.isArray(value)) return value.map(format).join(', ');
 if (typeof value === 'number') return value.toLocaleString(undefined, { maximumFractionDigits: 4 });
 return String(value);
}

function element(tag, text, className) {
 const node = document.createElement(tag);
 if (text !== undefined) node.textContent = text;
 if (className) node.className = className;
 return node;
}

function status(message, error = false) {
 $('status').textContent = message;
 $('status').classList.toggle('error', error);
}

function attempt(action) {
 return async () => {
  try {
   await action();
  } catch (e) {
   status(e.message, true);
  }
 };
}

async function request(url, options) {
 const response = await fetch(url, options);
 if (!response.ok) {
  let message = `Request gagal (${response.status}).`;
  try {
   message = (await response.json()).error || message;
  } catch {}
  throw Error(message);
 }
 return response;
}

function selectedRun() {
 return app.envelope?.runs[app.runIndex];
}

function selectedState() {
 return selectedRun()?.states[app.which];
}

function button(text, action, active) {
 const b = element('button', text);
 b.addEventListener('click', action);
 if (active !== undefined) b.setAttribute('aria-pressed', String(active));
 return b;
}

function tableHeader(table, labels) {
 const head = element('thead');
 const row = element('tr');
 for (const label of labels) row.append(element('th', label));
 head.append(row);
 const body = element('tbody');
 table.replaceChildren(head, body);
 return body;
}

function definitionList(values) {
 const dl = element('dl');
 for (const { label, value } of values) {
  dl.append(element('dt', label), element('dd', format(value)));
 }
 return dl;
}

// Reject file import yang rusak
function validateEnvelope(env) {
 const isNumber = value => typeof value === 'number' && Number.isFinite(value);

 if (env?.schema_version !== 1 || !env.meta || !Array.isArray(env.runs) || !env.runs.length) {
  throw Error('Result not supported. Expected schema_version 1 dan runs array yang tidak kosong.');
 }

 for (const [i, run] of env.runs.entries()) {
  if (!run.states?.init || !run.states?.final || !run.labels ||
      !Array.isArray(run.charts) || !Array.isArray(run.notes) || !Array.isArray(run.stats)) {
   throw Error(`Run ${i + 1}: states, labels, charts, atau metrics tidak lengkap.`);
  }

  for (const [key, state] of Object.entries(run.states)) {
   const validTruck = state.truck &&
    ['w', 'l', 'h', 'capacity'].every(k => isNumber(state.truck[k]) && state.truck[k] > 0);
   if (!validTruck || !Array.isArray(state.packages)) {
    throw Error(`Run ${i + 1}/${key}: truck atau package list tidak valid.`);
   }

   const ids = new Set();
   for (const p of state.packages) {
    const validDims = Array.isArray(p.dims) && p.dims.length === 3 &&
     p.dims.every(v => isNumber(v) && v > 0);
    const validPos = p.pos === null ||
     (Array.isArray(p.pos) && p.pos.length === 3 && p.pos.every(Number.isInteger));
    if (typeof p.id !== 'string' || ids.has(p.id) || !validDims ||
        !validPos || !isNumber(p.value) || !isNumber(p.weight)) {
     throw Error(`Run ${i + 1}/${key}, package ${p.id ?? '?'}: geometry atau metadata tidak valid.`);
    }
    ids.add(p.id);
   }

   if (typeof state.feasible !== 'boolean' || !Array.isArray(state.violations)) {
    throw Error(`Run ${i + 1}/${key}: info feasibility tidak ada.`);
   }
  }

  for (const chart of run.charts) {
   if (!Array.isArray(chart.lines)) throw Error(`Run ${i + 1}: chart lines tidak ada.`);
   for (const line of chart.lines) {
    const validCoords = Array.isArray(line.x) && Array.isArray(line.y) &&
     line.x.length === line.y.length &&
     line.x.every(isNumber) &&
     line.y.every(v => v === null || isNumber(v));
    if (!validCoords) throw Error(`Run ${i + 1}: koordinat chart tidak valid.`);
   }
  }
 }
}

function loadEnvelope(env) {
 validateEnvelope(env);
 app.envelope = env;

 const winner = env.meta.winner_index;
 app.runIndex = Number.isInteger(winner) && winner >= 0 && winner < env.runs.length ? winner : 0;
 app.which = 'final';
 app.chartIndex = 0;
 app.highlightId = null;
 render();
}

function renderSummary() {
 const meta = app.envelope.meta;
 const parameters = Object.entries(meta.params || {})
  .map(([key, value]) => `${key}: ${format(value)}`)
  .join(' / ');

 $('summary').replaceChildren(
  element('h2', meta.title),
  definitionList([
   { label: 'Parameters', value: parameters },
   { label: 'Base seed', value: meta.seed },
   { label: 'Source', value: meta.source },
   { label: 'Runs', value: app.envelope.runs.length },
  ]),
 );
}

function renderRuns() {
 const { runs, meta } = app.envelope;
 const isGa = meta.algo === 'GA';
 const showIterations = isGa || (meta.algo === 'HC' && meta.variant !== 'HC_RESTART');
 const columns = [
  'Run',
  ...(isGa ? ['Population'] : ['Seed']),
  'Final objective',
  ...(showIterations ? ['Iterations'] : []),
  'Search duration (s)',
 ];

 const body = tableHeader($('runs-table'), columns);

 runs.forEach((run, i) => {
  if (isGa && (i === 0 || run.group !== runs[i - 1].group)) {
   const row = element('tr', undefined, 'group');
   const title = element('th', `Configuration ${run.group + 1}`);
   title.colSpan = columns.length;
   row.append(title);
   body.append(row);
  }

  const row = element('tr', undefined, i === app.runIndex ? 'selected' : '');
  const cell = element('td');
  const pick = button(run.label, () => {
   app.runIndex = i;
   app.chartIndex = 0;
   if (!run.states[app.which]) app.which = 'final';
   render();
  });
  pick.className = 'row-button';
  cell.append(pick);
  if (isGa && i === meta.winner_index) {
   cell.append(element('span', 'Best of nine', 'best-marker'));
  }
  row.append(cell);

  const values = [
   ...(isGa ? [run.config?.population_size] : [run.seed]),
   run.final_value,
   ...(showIterations ? [run.iterations] : []),
   run.duration,
  ];
  for (const value of values) row.append(element('td', format(value)));
  body.append(row);
 });

 const run = selectedRun();
 const notes = element('ul', undefined, 'notes');
 const states = ['init', 'final'].map(key => {
  const details = element('details');
  const content = element('pre');
  content.textContent = run.state_texts?.[key] ?? JSON.stringify(run.states[key], null, 2);
  const title = `${key === 'init' ? 'Initial' : 'Final'} state: ${run.labels[key]}`;
  details.append(element('summary', title), content);
  return details;
 });

 for (const note of run.notes) notes.append(element('li', note));
 $('run-details').replaceChildren(...states, definitionList(run.stats), notes);
}

function renderStateTabs() {
 $('state-tabs').replaceChildren(
  ...Object.keys(selectedRun().states).map(key =>
   button(STATE_LABELS[key] || key, () => {
    app.which = key;
    renderState();
   }, app.which === key),
  ),
 );
}

function renderState() {
 renderStateTabs();
 const state = selectedState();

 viewer?.setState(state, { colorMode: app.colorMode, highlightId: null });
 $('viewer-caption').textContent =
  (viewer ? '' : 'WebGL tidak tersedia; tabel dan chart tetap jalan. ') +
  selectedRun().labels[app.which] +
  '. Box di samping truck adalah package yang unloaded.';

 const loaded = state.packages.filter(p => p.pos !== null).length;
 const figures = [
  ['Value', state.value],
  ['Weight / capacity', `${format(state.weight)} / ${format(state.truck.capacity)}`],
  ['Loaded / total', `${loaded} / ${state.packages.length}`],
 ].map(([label, value]) => {
  const div = element('div', undefined, 'figure');
  div.append(element('span', label), element('strong', format(value)));
  return div;
 });
 $('key-figures').replaceChildren(...figures);

 const errors = element('ul', undefined, 'notes');
 for (const message of state.violations) errors.append(element('li', message));
 $('feasibility').replaceChildren(
  element('span', state.feasible ? 'Feasible' : 'Infeasible',
   `badge ${state.feasible ? 'ok' : 'error'}`),
  errors,
 );

 const body = tableHeader($('packages-table'),
  ['Id', 'Status', 'Position', 'Size', 'Value', 'Weight', 'Fragile', 'ETA']);

 for (const p of state.packages) {
  const row = element('tr');
  row.tabIndex = 0;

  const values = [
   p.id,
   p.pos === null ? 'Outside' : 'Loaded',
   p.pos,
   p.dims,
   p.value,
   p.weight,
   p.fragile ? 'Yes' : 'No',
   p.eta,
  ];
  for (const value of values) row.append(element('td', format(value)));

  row.addEventListener('mouseenter', () => viewer?.setHighlight(p.id));
  row.addEventListener('mouseleave', () => viewer?.setHighlight(null));
  row.addEventListener('focus', () => viewer?.setHighlight(p.id));
  row.addEventListener('blur', () => viewer?.setHighlight(null));
  body.append(row);
 }
}

function drawSelectedChart() {
 drawLineChart($('chart-canvas'), selectedRun()?.charts[app.chartIndex]);
}

function renderCharts() {
 $('chart-tabs').replaceChildren(
  ...selectedRun().charts.map((chart, i) =>
   button(chart.title, () => {
    app.chartIndex = i;
    renderCharts();
   }, app.chartIndex === i),
  ),
 );
 drawSelectedChart();
}

function render() {
 renderSummary();
 renderRuns();
 renderState();
 renderCharts();
}

async function savedResults(selected) {
 const data = await (await request('/api/results')).json();
 $('saved-select').replaceChildren(
  new Option(data.files.length ? 'Pilih saved result' : 'Belum ada saved result', ''),
  ...data.files.map(f => new Option(f.name, f.name)),
 );
 if (selected) $('saved-select').value = selected;
}

async function loadExample(name) {
 $('input-text').value = await (await request(`/examples/${name}.txt`)).text();
}

export function randomInstance(header, count = 40) {
 if (!(header in EXAMPLE_TAILS)) header = 'HC_STEEPEST';
 const integer = (lo, hi) => lo + Math.floor(Math.random() * (hi - lo + 1));

 let weight = 0;
 const packages = Array.from({ length: count }, () => {
  const w = integer(1, 10);
  weight += w;
  return [
   integer(1, 4), integer(1, 4), integer(1, 4),
   w, integer(1, 100), Math.random() < .2 ? 1 : 0, integer(0, 5),
  ].join(' ');
 });

 const prefix = [header, `8 8 8 ${Math.max(1, Math.floor(weight * .5))}`];
 if (header === 'GA') prefix.push('banyak_iterasi', '10');

 const tail = EXAMPLE_TAILS[header];
 return [...prefix, String(count), ...packages, ...(tail ? [tail] : [])].join('\n') + '\n';
}

async function runFromInput() {
 const seedInput = $('seed').value.trim();
 const seed = seedInput === '' ? null : Number(seedInput);
 const repeats = Number($('repeats').value);

 if (seed !== null && !Number.isSafeInteger(seed)) {
  throw Error('Seed harus safe integer atau dibiarkan kosong untuk seed acak.');
 }
 if (!Number.isInteger(repeats) || repeats < 1 || repeats > 10) {
  throw Error('Repeats harus berupa int dalam rentang 1 sampai 10 (GA selalu menjalankan 9 trials).');
 }

 $('btn-run').disabled = true;
 status('Running. Batch genetic algorithm bisa agak lama.');

 try {
  const body = JSON.stringify({ text: $('input-text').value, seed, repeats });
  if (new Blob([body]).size > 1000000) {
   throw Error('Input melebihi batas 1.000.000 byte. Gunakan input lebih kecil atau CLI.');
  }

  const response = await (
   await request('/api/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body,
   })
  ).json();

  loadEnvelope(response.envelope);
  await savedResults(response.saved_as.split('/').at(-1));
  $('input-panel').open = false;
  status(`Saved ${response.saved_as} dan ${response.saved_txt}. Base seed: ${response.envelope.meta.seed}.`);
 } finally {
  $('btn-run').disabled = false;
 }
}

async function loadSaved() {
 const name = $('saved-select').value;
 if (!name) throw Error('Pilih saved result dulu.');
 loadEnvelope(await (await request('/output/' + encodeURIComponent(name))).json());
 status(`Berhasil load ${name}.`);
}

function download(blob, name) {
 const url = URL.createObjectURL(blob);
 const a = element('a');
 a.href = url;
 a.download = name;
 a.click();
 setTimeout(() => URL.revokeObjectURL(url), 1000);
}

async function init() {
 try {
  viewer = createViewer($('viewer'));
 } catch (e) {
  status(`Inisialisasi 3D gagal: ${e.message}`, true);
 }

 $('btn-png').disabled = !viewer;
 $('btn-reset-cam').disabled = !viewer;
 if (!viewer) {
  $('viewer-caption').textContent = 'WebGL tidak tersedia; tabel dan chart tetap jalan.';
 }

 $('example-select').replaceChildren(
  ...examples.map(name => new Option(name.replaceAll('_', ' '), name)),
 );

 $('example-select').addEventListener('change',
  attempt(() => loadExample($('example-select').value)));
 $('btn-load').addEventListener('click', attempt(loadSaved));
 $('btn-run').addEventListener('click', attempt(runFromInput));

 $('btn-random').addEventListener('click', () => {
  $('input-text').value = randomInstance($('input-text').value.trim().split(/\r?\n/)[0]);
  $('input-panel').open = true;
  status('40 package diacak. Input persisnya akan disimpan bersama result.');
 });

 $('file-open').addEventListener('change', attempt(async () => {
  const file = $('file-open').files[0];
  if (!file) return;
  loadEnvelope(JSON.parse(await file.text()));
  status(`Berhasil load ${file.name}.`);
  $('file-open').value = '';
 }));

 $('color-mode').addEventListener('change', () => {
  app.colorMode = $('color-mode').value;
  viewer?.setColorMode(app.colorMode);
 });

 $('btn-reset-cam').addEventListener('click', () => viewer?.resetCamera());

 $('btn-png').addEventListener('click', attempt(async () => {
  if (!selectedState()) throw Error('Load result dulu sebelum export figure.');
  download(await viewer.toPNG(), `packing-${app.runIndex + 1}-${app.which}.png`);
 }));

 $('btn-chart-png').addEventListener('click', attempt(async () => {
  if (!selectedRun()) throw Error('Load result dulu sebelum export chart.');
  drawSelectedChart();
  const blob = await new Promise(resolve => $('chart-canvas').toBlob(resolve));
  if (!blob) throw Error('Export PNG chart gagal.');
  download(blob, `chart-${app.runIndex + 1}-${app.chartIndex + 1}.png`);
 }));

 new ResizeObserver(drawSelectedChart).observe($('chart-canvas').parentElement);

 $('viewer').addEventListener('webglcontextlost', () => {
  $('btn-png').disabled = true;
  status('Context grafis 3D hilang. Reload halaman untuk restore; tabel dan chart tetap tersedia.', true);
 });

 await Promise.all([savedResults(), loadExample(examples[0])]);
}

if (location.protocol !== 'file:') attempt(init)();
