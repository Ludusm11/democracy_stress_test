const $ = id => document.getElementById(id);
const data = {};
const coreIds = ['vdem', 'freedom', 'turnout', 'economy', 'eurobarometer'];
const colors = ['#245f91', '#c45d3f'];
const loading = {};
let view = 'scenario';

async function fetchJson(name) {
  const response = await fetch('data/' + name + '.json?v=site2');
  if (!response.ok) throw new Error(name + ': HTTP ' + response.status);
  return response.json();
}
function ensure(ids) {
  return Promise.all(ids.map(id => data[id] || (loading[id] ||= fetchJson(id).then(rows => { data[id] = rows; }))));
}

function option(select, value, label) {
  const node = document.createElement('option');
  node.value = value;
  node.textContent = label;
  select.append(node);
}

function catalog(id) { return data.catalog.find(item => item.id === id); }
function metric(dataset, key) { return catalog(dataset).metrics.find(item => item.key === key); }
function scenario() { return data.scenarios.find(item => item.id === $('scenario-select').value); }
function currentEpisode() { return scenario().episodes[Number($('episode-select').value) || 0]; }
function episodeWindow(episode) { return [episode.start - 5, Math.min(2026, (episode.end ?? 2025) + 5)]; }
function displayDate(row) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(row.date || '')) return String(row.year);
  return new Date(row.date + 'T00:00:00Z').toLocaleDateString('en-GB', {day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC'});
}
function number(value, unit) {
  const digits = unit === 'score (0–1)' ? 3 : unit === 'score (0–10)' ? 2 : 1;
  return value.toFixed(digits) + (unit === '%' ? '%' : '');
}
function dataRows(spec, country, group = spec.group || '') {
  return (data[spec.dataset] || []).filter(row => row.country === country && row.metric === spec.metric && (!group || row.group === group))
    .sort((a, b) => position(a) - position(b));
}
function position(row) {
  if (row.date && /^\d{4}-\d{2}-\d{2}$/.test(row.date)) {
    const time = Date.parse(row.date + 'T00:00:00Z');
    const first = Date.UTC(row.year, 0, 1);
    const next = Date.UTC(row.year + 1, 0, 1);
    if (Number.isFinite(time)) return row.year + (time - first) / (next - first);
  }
  return row.year;
}
function chartSvg(series, meta, from, to, marked = null) {
  const all = series.flatMap(item => item.rows);
  if (!all.length) return '';
  const W = 760, H = 330, left = 68, right = 22, top = 38, bottom = 51;
  const values = all.flatMap(row => [row.value, row.low, row.high].filter(Number.isFinite));
  const low = Math.min(...values), high = Math.max(...values);
  const pad = Math.max((high - low) * 0.08, meta.unit === 'score (0–1)' ? 0.02 : 1);
  const ymin = meta.axisMin == null ? Math.min(0, low - pad) : Math.min(meta.axisMin, low);
  let ymax = meta.axisMax == null ? Math.max(0, high + pad) : Math.max(meta.axisMax, high);
  if (ymax <= ymin) ymax = ymin + 1;
  const x = year => left + (year - from) / (to + 1 - from) * (W - left - right);
  const y = value => H - bottom - (value - ymin) / (ymax - ymin) * (H - top - bottom);
  const label = series.map(s => s.name).join(' and ') + ': ' + meta.label + ' by year';
  let svg = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${escapeHtml(label)}"><rect width="${W}" height="${H}" fill="white"/>`;
  if (marked && !marked.openEnded && marked.end > marked.start) {
    const start = Math.max(from, marked.start), end = Math.min(to, marked.end);
    if (start < end) svg += `<rect class="episode-band" data-start-year="${start}" data-end-year="${end}" x="${x(start)}" y="${top}" width="${x(end) - x(start)}" height="${H - top - bottom}" fill="#ffe7dc"/>`;
  }
  const span = to - from + 1;
  const gridStep = span <= 40 ? 1 : span <= 80 ? 2 : 5;
  const labelStep = span <= 16 ? 1 : span <= 30 ? 2 : span <= 45 ? 5 : span <= 80 ? 10 : 20;
  for (let year = from; year <= to + 1; year += gridStep) {
    const major = (year - from) % labelStep === 0;
    svg += `<line x1="${x(year)}" x2="${x(year)}" y1="${top}" y2="${H - bottom}" stroke="${major ? '#cedae3' : '#e3eaf0'}" stroke-width="${major ? 1.2 : 1}"/>`;
  }
  if ((to + 1 - from) % gridStep !== 0) svg += `<line x1="${x(to + 1)}" x2="${x(to + 1)}" y1="${top}" y2="${H - bottom}" stroke="#cedae3"/>`;
  for (let i = 0; i <= 4; i++) {
    const value = ymin + (ymax - ymin) * i / 4;
    svg += `<line x1="${left}" x2="${W - right}" y1="${y(value)}" y2="${y(value)}" stroke="#cbd8e2"/><text x="${left - 9}" y="${y(value) + 4}" text-anchor="end" fill="#5b6975" font-size="12">${escapeHtml(number(value, meta.unit))}</text>`;
  }
  const years = [];
  for (let year = from; year <= to; year += labelStep) years.push(year);
  if (to - years.at(-1) > labelStep / 2) years.push(to);
  years.forEach(year => { svg += `<text class="year-label" x="${x(year)}" y="${H - 25}" text-anchor="middle" fill="#455968" font-size="14">${year}</text>`; });
  svg += `<text x="${(left + W - right) / 2}" y="${H - 5}" text-anchor="middle" fill="#344552" font-size="12">Year</text><text x="${left}" y="21" fill="#344552" font-size="12">${escapeHtml(meta.label)} · ${escapeHtml(meta.unit)}</text>`;
  if (marked) {
    const start = Math.max(from, marked.start);
    const end = marked.end == null ? start : Math.min(to, marked.end);
    if (start <= to) {
      if (!marked.openEnded && end > start) {
        svg += `<line class="episode-edge" x1="${x(start)}" x2="${x(start)}" y1="${top}" y2="${H - bottom}" stroke="#bf583b" stroke-width="2" pointer-events="none"/>`;
        svg += `<line class="episode-edge" x1="${x(end)}" x2="${x(end)}" y1="${top}" y2="${H - bottom}" stroke="#bf583b" stroke-width="2" pointer-events="none"/>`;
      } else {
        svg += `<line class="episode-marker" x1="${x(start)}" x2="${x(start)}" y1="${top}" y2="${H - bottom}" stroke="#bf583b" stroke-width="3" pointer-events="none"/>`;
      }
      const markerLabel = marked.openEnded ? `from ${start}` : end === start ? String(start) : end === start + 1 ? `${start}–${String(end).slice(-2)}` : `${start}–${end}`;
      svg += `<text x="${x(start) + 6}" y="${top + 16}" fill="#913d29" font-size="12" font-weight="700">${markerLabel}</text>`;
    }
  }
  svg += `<line class="chart-cursor" x1="${left}" x2="${left}" y1="${top}" y2="${H - bottom}" stroke="#245f91" stroke-width="1.5" stroke-dasharray="4 3" visibility="hidden" pointer-events="none"/>`;
  series.forEach((item, index) => {
    const color = colors[index % colors.length];
    const rows = item.rows.filter(row => position(row) >= from && position(row) < to + 1);
    if (item.mode === 'line' && rows.length > 1) {
      svg += `<polyline fill="none" stroke="${color}" stroke-width="2.5" points="${rows.map(row => x(position(row)) + ',' + y(row.value)).join(' ')}"/>`;
    }
    rows.forEach(row => {
      if (Number.isFinite(row.low) && Number.isFinite(row.high)) {
        const px = x(position(row));
        svg += `<line x1="${px}" x2="${px}" y1="${y(row.low)}" y2="${y(row.high)}" stroke="${color}" stroke-opacity=".38" stroke-width="3"/>`;
      }
      const detail = item.name + ' · ' + displayDate(row) + ' · ' + number(row.value, meta.unit) + (Number.isFinite(row.low) ? ' · V-Dem interval ' + number(row.low, meta.unit) + '–' + number(row.high, meta.unit) : '');
      svg += `<circle cx="${x(position(row))}" cy="${y(row.value)}" r="3.8" fill="${color}" data-detail="${escapeHtml(detail)}" tabindex="0" aria-label="${escapeHtml(detail)}"><title>${escapeHtml(detail)}</title></circle>`;
    });
  });
  return svg + '</svg>';
}
function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, char => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[char]));
}
function makeChartInteractive(graph) {
  const svg = graph.querySelector('svg');
  const points = [...svg.querySelectorAll('circle[data-detail]')];
  const cursor = svg.querySelector('.chart-cursor');
  const readout = document.createElement('p');
  readout.className = 'point-readout';
  readout.textContent = 'Move over a point to read it. Click to keep it selected.';
  graph.append(readout);
  let active = null;
  let pinned = false;

  function clear() {
    if (active) {
      active.setAttribute('r', '3.8');
      active.removeAttribute('stroke');
      active.removeAttribute('stroke-width');
    }
    active = null;
    cursor.setAttribute('visibility', 'hidden');
    readout.textContent = 'Move over a point to read it. Click to keep it selected.';
    readout.classList.remove('pinned');
  }
  function show(point, pin) {
    if (active && active !== point) {
      active.setAttribute('r', '3.8');
      active.removeAttribute('stroke');
      active.removeAttribute('stroke-width');
    }
    active = point;
    pinned = pin;
    point.setAttribute('r', '6.5');
    point.setAttribute('stroke', '#18354c');
    point.setAttribute('stroke-width', '2');
    cursor.setAttribute('x1', point.getAttribute('cx'));
    cursor.setAttribute('x2', point.getAttribute('cx'));
    cursor.setAttribute('visibility', 'visible');
    readout.textContent = (pin ? 'Selected · ' : 'Point · ') + point.dataset.detail;
    readout.classList.toggle('pinned', pin);
  }
  function nearest(event) {
    const matrix = svg.getScreenCTM();
    if (!matrix) return null;
    const screen = svg.createSVGPoint();
    screen.x = event.clientX;
    screen.y = event.clientY;
    const location = screen.matrixTransform(matrix.inverse());
    let best = null, distance = 35;
    for (const point of points) {
      const d = Math.hypot(Number(point.getAttribute('cx')) - location.x, Number(point.getAttribute('cy')) - location.y);
      if (d < distance) { best = point; distance = d; }
    }
    return best;
  }
  svg.addEventListener('pointermove', event => {
    if (pinned) return;
    const point = nearest(event);
    if (point) show(point, false);
    else clear();
  });
  svg.addEventListener('pointerleave', () => { if (!pinned) clear(); });
  svg.addEventListener('click', event => {
    const point = nearest(event);
    if (!point) return;
    if (pinned && point === active) { pinned = false; clear(); }
    else show(point, true);
  });
  svg.addEventListener('focusin', event => {
    if (points.includes(event.target)) show(event.target, false);
  });
  svg.addEventListener('keydown', event => {
    if (!points.includes(event.target) || !['Enter', ' '].includes(event.key)) return;
    event.preventDefault();
    show(event.target, true);
  });
}
function legend(series) {
  const node = document.createElement('div');
  node.className = 'legend';
  series.forEach((s, i) => {
    const entry = document.createElement('span');
    entry.innerHTML = '<i style="background:' + colors[i] + '"></i>';
    entry.append(document.createTextNode(s.name + ' (' + s.rows.length + ')'));
    node.append(entry);
  });
  return node;
}
function chartCard(spec, country, from, to, marked = null, compare = '') {
  const inWindow = rows => rows.filter(row => row.year >= from && row.year <= to);
  const rows = inWindow(dataRows(spec, country));
  const item = catalog(spec.dataset), measure = metric(spec.dataset, spec.metric);
  const series = [{name: country, rows, mode: item.chart}];
  const compareRows = compare && compare !== country ? inWindow(dataRows(spec, compare)) : [];
  if (compareRows.length) series.push({name: compare, rows: compareRows, mode: item.chart});
  const card = document.createElement('article');
  card.className = 'chart-card';
  const h = document.createElement('h3');
  h.textContent = measure.label + (spec.group ? ' · ' + spec.group : '');
  const p = document.createElement('p');
  p.textContent = item.source + ' · ' + measure.unit + (compare && compare !== country && !compareRows.length ? ' · no ' + compare + ' figure in this source' : '');
  card.append(h, p);
  if (rows.length) {
    const graph = document.createElement('div');
    graph.innerHTML = chartSvg(series, measure, from, to, marked);
    makeChartInteractive(graph);
    card.append(graph, legend(series));
  } else {
    const empty = document.createElement('p');
    empty.className = 'empty';
    empty.textContent = 'No observations in this period. Browse the full dataset in Explore data.';
    card.append(empty);
  }
  return card;
}

function setView(next) {
  view = next;
  $('scenario-view').hidden = next !== 'scenario';
  $('explore-view').hidden = next !== 'explore';
  for (const [name, id] of [['scenario', 'scenario-tab'], ['explore', 'explore-tab']]) {
    const tab = $(id);
    tab.classList.toggle('active', name === next);
    if (name === next) tab.setAttribute('aria-current', 'page');
    else tab.removeAttribute('aria-current');
  }
  history.replaceState(null, '', '#' + next);
}
function updateScenarioChoices() {
  const selected = scenario();
  const select = $('episode-select');
  select.replaceChildren();
  selected.episodes.forEach((episode, i) => option(select, String(i), episode.label));
  renderScenario();
}
function renderScenario() {
  const selected = scenario();
  const episode = currentEpisode();
  $('scenario-code').textContent = selected.id + ' · ' + selected.phase + ' · France case study';
  $('scenario-title').textContent = selected.title;
  $('scenario-trigger').textContent = selected.trigger;
  $('scenario-focus').textContent = selected.focus;
  $('scenario-gap').textContent = selected.gap;
  $('episode-heading').textContent = 'Reference episode · ' + episode.label;
  const isLine = episode.openEnded || episode.start === episode.end;
  $('episode-key').classList.toggle('is-line', isLine);
  const timing = episode.openEnded ? `Red line marks the start in ${episode.start}; no end year is specified.`
    : isLine ? `Red line marks ${episode.start}.`
    : `Red band runs from the ${episode.start} gridline to the ${episode.end} gridline.`;
  $('episode-timing').textContent = `${timing} Dates are year-level unless a source reports a day. Timing alone does not establish causation.`;
  const baseline = $('baseline');
  baseline.replaceChildren();
  const baselineSpecs = [{dataset: 'vdem', metric: 'v2x_polyarchy'}, ...selected.charts.slice(0, 3)]
    .filter((spec, index, list) => list.findIndex(other => other.dataset === spec.dataset && other.metric === spec.metric && other.group === spec.group) === index);
  baselineSpecs.forEach(spec => {
    const rows = dataRows(spec, 'France');
    const last = rows.at(-1), measure = metric(spec.dataset, spec.metric);
    const card = document.createElement('article');
    card.className = 'baseline-card';
    const title = document.createElement('h3');
    title.textContent = measure.label + (spec.group ? ' · ' + spec.group : '');
    const value = document.createElement('strong');
    value.textContent = last ? number(last.value, measure.unit) : 'No data';
    const note = document.createElement('p');
    note.textContent = last ? displayDate(last) + ' · ' + catalog(spec.dataset).source + (Number.isFinite(last.low) ? ' · uncertainty ' + number(last.low, measure.unit) + '–' + number(last.high, measure.unit) : '') : catalog(spec.dataset).source;
    card.append(title, value, note);
    if (last) {
      const context = [];
      const eu = dataRows(spec, 'European Union').find(row => last.date ? row.date === last.date : row.year === last.year);
      if (eu) context.push('EU: ' + number(eu.value, measure.unit));
      const previous = spec.dataset === 'turnout' ? rows.filter(row => row.year < last.year).at(-1) : rows.at(-2); // turnout: previous election, not the other round
      if (previous) {
        const change = last.value - previous.value;
        const digits = measure.unit === 'score (0–1)' ? 3 : 1;
        context.push('Previous (' + displayDate(previous) + '): ' + number(previous.value, measure.unit) + ', ' + (change >= 0 ? '+' : '−') + Math.abs(change).toFixed(digits));
      }
      if (context.length) {
        const extra = document.createElement('p');
        extra.className = 'context';
        extra.textContent = context.join(' · ');
        card.append(extra);
      }
    }
    baseline.append(card);
  });
  const references = $('episode-charts');
  const [from, to] = episodeWindow(episode);
  const available = selected.charts.filter(spec => dataRows(spec, episode.country).some(row => row.year >= from && row.year <= to));
  references.replaceChildren(...available.map(spec => chartCard(spec, episode.country, from, to, episode, $('episode-compare').value)));
  if (!available.length) references.textContent = 'No prepared indicators have observations in this period.';
  const sources = new Set(available.map(spec => spec.dataset)).size;
  const missing = selected.charts.length - available.length;
  $('episode-coverage').textContent = `${available.length} chart${available.length === 1 ? '' : 's'} from ${sources} dataset${sources === 1 ? '' : 's'}${missing ? ` · ${missing} other relevant indicators have no observations in this period` : ''}.`;
  updateExtraGroup();
}

async function updateExtraDataset() {
  const id = $('extra-dataset').value;
  if (id && !data[id]) {
    $('extra-chart').textContent = 'Loading ' + catalog(id).title + '…';
    await ensure([id]);
    if ($('extra-dataset').value !== id) return;
  }
  $('extra-metric-label').hidden = !id;
  const select = $('extra-metric');
  select.replaceChildren();
  if (id) catalog(id).metrics.forEach(item => option(select, item.key, item.label));
  updateExtraGroup();
}
function updateExtraGroup() {
  const id = $('extra-dataset').value;
  const label = $('extra-group-label'), select = $('extra-group');
  const previous = select.value;
  select.replaceChildren();
  if (!id) {
    label.hidden = true;
    $('extra-chart').replaceChildren();
    $('extra-note').textContent = '';
    return;
  }
  const item = catalog(id);
  label.hidden = !item.groupLabel;
  if (item.groupLabel) {
    label.firstChild.textContent = item.groupLabel;
    const episode = currentEpisode();
    const [from, to] = episodeWindow(episode);
    const grouped = new Map();
    data[id].filter(row => row.country === episode.country && row.metric === $('extra-metric').value)
      .forEach(row => {
        const current = grouped.get(row.group) || {inWindow: false, year: 0, value: 0};
        current.inWindow ||= row.year >= from && row.year <= to;
        if (row.year > current.year || row.year === current.year && row.value > current.value) {
          current.year = row.year;
          current.value = row.value;
        }
        grouped.set(row.group, current);
      });
    const groups = [...grouped.keys()].sort((a, b) => Number(grouped.get(b).inWindow) - Number(grouped.get(a).inWindow)
      || grouped.get(b).year - grouped.get(a).year || grouped.get(b).value - grouped.get(a).value || a.localeCompare(b));
    groups.forEach(group => option(select, group, group));
    if (groups.includes(previous)) select.value = previous;
    else if (groups.includes('National parliament')) select.value = 'National parliament';
    else if (groups.includes('Parliamentary')) select.value = 'Parliamentary';
  }
  renderExtra();
}
function renderExtra() {
  const id = $('extra-dataset').value;
  if (!id) return;
  const episode = currentEpisode();
  const [from, to] = episodeWindow(episode);
  const item = catalog(id);
  const spec = {dataset: id, metric: $('extra-metric').value};
  if (item.groupLabel) spec.group = $('extra-group').value;
  $('extra-chart').replaceChildren(chartCard(spec, episode.country, from, to, episode, $('episode-compare').value));
  $('extra-note').textContent = item.note + (id === 'ches' || id === 'ppeg' ? ' This chart shows one selected party or alliance, not total radical vote share.' : '');
}

async function updateDataset() {
  const id = $('dataset-select').value;
  if (!data[id]) {
    $('explore-chart').textContent = 'Loading ' + catalog(id).title + '…';
    await ensure([id]);
    if ($('dataset-select').value !== id) return;
  }
  const item = catalog(id);
  const metricSelect = $('metric-select');
  metricSelect.replaceChildren();
  item.metrics.forEach(m => option(metricSelect, m.key, m.label));
  const countrySelect = $('country-select');
  countrySelect.replaceChildren();
  item.countries.forEach(country => option(countrySelect, country, country));
  countrySelect.value = item.countries.includes('France') ? 'France' : item.countries[0];
  updateCountry();
}
function updateCountry() {
  const item = catalog($('dataset-select').value);
  const country = $('country-select').value;
  const compare = $('compare-select');
  const old = compare.value;
  compare.replaceChildren();
  option(compare, '', 'No comparison');
  item.countries.filter(value => value !== country).forEach(value => option(compare, value, value));
  if (old && old !== country && item.countries.includes(old)) compare.value = old;
  updateGroup();
}
function updateGroup() {
  const item = catalog($('dataset-select').value);
  const label = $('group-label'), select = $('group-select');
  const old = select.value;
  select.replaceChildren();
  if (!item.groupLabel) { label.hidden = true; renderExplore(); return; }
  label.hidden = false;
  label.firstChild.textContent = item.groupLabel;
  const latestByGroup = new Map();  // group -> its most recent row; list recent and large groups first
  data[item.id].filter(row => row.country === $('country-select').value && row.metric === $('metric-select').value)
    .forEach(row => {
      const current = latestByGroup.get(row.group);
      if (!current || row.year > current.year || row.year === current.year && row.value > current.value) latestByGroup.set(row.group, row);
    });
  const groups = [...latestByGroup.keys()].sort((a, b) => latestByGroup.get(b).year - latestByGroup.get(a).year
    || latestByGroup.get(b).value - latestByGroup.get(a).value || a.localeCompare(b));
  groups.forEach(group => option(select, group, group));
  if (groups.includes(old)) select.value = old;
  else if (groups.includes('National parliament')) select.value = 'National parliament';
  else if (groups.includes('Parliamentary')) select.value = 'Parliamentary';
  else if (groups.length) select.value = groups[0];
  renderExplore();
}
function renderExplore() {
  const item = catalog($('dataset-select').value);
  const measure = metric(item.id, $('metric-select').value);
  const country = $('country-select').value;
  const group = item.groupLabel ? $('group-select').value : '';
  const compare = $('compare-select').value;
  $('dataset-source').textContent = item.source + ' · ' + item.firstYear + '–' + item.lastYear;
  $('dataset-title').textContent = item.title;
  $('dataset-meaning').textContent = measure.meaning;
  $('dataset-note').textContent = item.note;
  $('dataset-link').href = item.url;
  const spec = {dataset: item.id, metric: measure.key, group};
  const series = [{name: country, rows: dataRows(spec, country, group), mode: item.chart}];
  if (compare) series.push({name: compare, rows: dataRows(spec, compare, group), mode: item.chart});
  const all = series.flatMap(s => s.rows);
  const container = $('explore-chart');
  container.replaceChildren();
  if (!all.length) {
    container.textContent = 'No observations for this selection.';
    $('explore-detail').textContent = '';
    return;
  }
  const from = Math.min(...all.map(row => row.year));
  const to = Math.max(...all.map(row => row.year));
  const graph = document.createElement('div');
  graph.innerHTML = chartSvg(series, measure, from, to);
  makeChartInteractive(graph);
  container.append(graph);
  container.append(legend(series));
  const header = 'dataset,measure,unit,country,group,date,year,value,low,high';
  const quote = value => /[",\n]/.test(String(value)) ? '"' + String(value).replace(/"/g, '""') + '"' : String(value);
  const lines = series.flatMap(s => s.rows.map(row => [item.source, measure.label, measure.unit, s.name, row.group, row.date, row.year, row.value, row.low ?? '', row.high ?? ''].map(quote).join(',')));
  const link = $('download-csv');
  if (link.href.startsWith('blob:')) URL.revokeObjectURL(link.href);
  link.href = URL.createObjectURL(new Blob([header + '\n' + lines.join('\n') + '\n'], {type: 'text/csv'}));
  link.download = [item.id, measure.key, country, compare].filter(Boolean).join('_').replace(/[^\w-]+/g, '-') + '.csv';
  $('explore-detail').textContent = 'Horizontal axis: year. Vertical axis: ' + measure.label + ' (' + measure.unit + ').' + (item.id === 'vdem' ? ' The faint vertical marks show V-Dem uncertainty intervals.' : '') + (item.chart === 'dots' ? ' Points are observations; missing years are not filled in.' : '');
}

async function start() {
  try {
    [data.catalog, data.scenarios] = await Promise.all([fetchJson('catalog'), fetchJson('scenarios'), ensure(coreIds)]);
    data.scenarios.forEach(item => option($('scenario-select'), item.id, item.id + ' · ' + item.title + (item.phase === 'Board 1' ? '' : ' · later')));
    data.catalog.forEach(item => option($('dataset-select'), item.id, item.title));
    option($('extra-dataset'), '', 'Choose a dataset');
    data.catalog.forEach(item => option($('extra-dataset'), item.id, item.title));
    updateScenarioChoices();
    updateDataset();
    $('status').hidden = true;
    setView(location.hash === '#explore' ? 'explore' : 'scenario');
  } catch (error) {
    $('status').textContent = 'Could not load the dashboard data: ' + error.message + '. Rebuild the data and refresh the page.';
  }
}

$('scenario-tab').addEventListener('click', () => setView('scenario'));
$('explore-tab').addEventListener('click', () => setView('explore'));
$('scenario-select').addEventListener('change', updateScenarioChoices);
$('episode-select').addEventListener('change', renderScenario);
$('episode-compare').addEventListener('change', renderScenario);
$('extra-dataset').addEventListener('change', updateExtraDataset);
$('extra-metric').addEventListener('change', updateExtraGroup);
$('extra-group').addEventListener('change', renderExtra);
$('dataset-select').addEventListener('change', updateDataset);
$('metric-select').addEventListener('change', updateGroup);
$('country-select').addEventListener('change', updateCountry);
$('group-select').addEventListener('change', renderExplore);
$('compare-select').addEventListener('change', renderExplore);
start();
