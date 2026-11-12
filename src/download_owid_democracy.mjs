import { createHash } from 'node:crypto';
import { readFile, mkdir, writeFile, rename, stat } from 'node:fs/promises';
import path from 'node:path';

const root = path.resolve('data/owid_democracy');
const pageHtml = await readFile(path.join(root, 'source_page.html'), 'utf8');
const explorerHtml = await readFile(path.join(root, 'explorer_page.html'), 'utf8');

const linkedChartSlugs = [...new Set(
  [...pageHtml.matchAll(/(?:href|src)="([^"]*\/grapher\/[^"?#]+)[^"]*"/g)]
    .map((match) => match[1].split('/').at(-1))
    .filter((slug) => slug && !slug.endsWith('.png') && /^[a-z0-9-]+$/.test(slug))
)];
const searchPages = await Promise.all([0, 1, 2].map(async (page) =>
  JSON.parse(await readFile(path.join(root, `search_page_${page}.json`), 'utf8'))
));
const searchHits = searchPages.flatMap((page) => page.results);
if (searchPages[0].nbHits !== searchHits.length) throw new Error('Incomplete Democracy search catalog');
const taggedChartSlugs = searchHits.filter((hit) => hit.type === 'chart').map((hit) => hit.slug);
const chartSlugs = [...new Set([...linkedChartSlugs, ...taggedChartSlugs])];

const programMatch = explorerHtml
  .slice(explorerHtml.indexOf('const explorerProgram ='))
  .match(/"program":\s*("(?:\\.|[^"\\])*")/);
if (!programMatch) throw new Error('Could not locate the embedded democracy explorer catalog');
const explorerProgram = JSON.parse(programMatch[1]);
const programLines = explorerProgram.split('\n');
const start = programLines.indexOf('graphers');
const end = programLines.findIndex((line, i) => i > start && !line.startsWith('\t') && line.trim());
if (start < 0 || end < 0) throw new Error('Could not parse explorer graphers');
const explorerViews = programLines.slice(start + 2, end)
  .map((line) => line.split('\t'))
  .filter((parts) => parts[8] && parts[9] && parts[10])
  .map((parts, i) => ({
    number: i + 1,
    dataset: parts[8].replace(/\u00ad/g, ''),
    metric: parts[9].replace(/\u00ad/g, ''),
    submetric: parts[10].replace(/\u00ad/g, ''),
    rawMetric: parts[9],
    rawSubmetric: parts[10],
  }));

function slugify(value) {
  return value.toLowerCase().normalize('NFKD').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 70);
}

const jobs = [];
for (const slug of chartSlugs) {
  jobs.push({
    kind: 'chart_csv', slug,
    url: `https://ourworldindata.org/grapher/${slug}.csv`,
    file: `charts/${slug}.csv`,
  });
  jobs.push({
    kind: 'chart_metadata', slug,
    url: `https://ourworldindata.org/grapher/${slug}.metadata.json`,
    file: `metadata/${slug}.metadata.json`,
  });
}
for (const view of explorerViews) {
  const params = new URLSearchParams({
    Dataset: view.dataset,
    Metric: view.rawMetric,
    'Sub-metric': view.rawSubmetric,
  });
  const stem = `${String(view.number).padStart(3, '0')}_${slugify(view.dataset)}__${slugify(view.metric)}__${slugify(view.submetric)}`;
  jobs.push({
    kind: 'explorer_csv',
    dataset: view.dataset,
    metric: view.metric,
    submetric: view.submetric,
    url: `https://ourworldindata.org/explorers/democracy.csv?${params}`,
    file: `explorer/${stem}.csv`,
  });
}

await Promise.all(['charts', 'metadata', 'explorer'].map((folder) => mkdir(path.join(root, folder), { recursive: true })));
await writeFile(path.join(root, 'catalog.json'), JSON.stringify({
  sourcePage: 'https://ourworldindata.org/democracy',
  explorerPage: 'https://ourworldindata.org/explorers/democracy',
  searchApi: 'https://ourworldindata.org/api/search?type=charts&topics=Democracy',
  searchHitCount: searchHits.length,
  linkedChartCount: linkedChartSlugs.length,
  taggedChartCount: new Set(taggedChartSlugs).size,
  chartCount: chartSlugs.length,
  explorerViewCount: explorerViews.length,
  explorerSourceFamilies: [...new Set(explorerViews.map((view) => view.dataset))],
  jobs,
}, null, 2));

const results = [];
let cursor = 0;
let finished = 0;

async function fetchJob(job) {
  const destination = path.join(root, job.file);
  try {
    const existing = await stat(destination);
    if (existing.size > 20) {
      const buffer = await readFile(destination);
      return result(job, buffer, 'existing');
    }
  } catch {}

  let lastError;
  for (let attempt = 1; attempt <= 4; attempt++) {
    try {
      const response = await fetch(job.url, { headers: { 'User-Agent': 'capstone-democracy-dataset-download/1.0' } });
      if (!response.ok) {
        const body = await response.text();
        if (body.includes('non-redistributable data')) {
          return { ...job, status: 'restricted', httpStatus: response.status, reason: 'OWID says this CSV contains non-redistributable data' };
        }
        throw new Error(`HTTP ${response.status}: ${body.slice(0, 120)}`);
      }
      const buffer = Buffer.from(await response.arrayBuffer());
      if (buffer.length < 20) throw new Error('Empty or suspiciously small response');
      if (job.kind.endsWith('csv')) {
        const header = buffer.subarray(0, Math.min(buffer.length, 400)).toString('utf8').split(/\r?\n/)[0];
        if (!header.startsWith('Entity,Code,Year,')) throw new Error(`Unexpected CSV header: ${header.slice(0, 100)}`);
      } else {
        JSON.parse(buffer.toString('utf8'));
      }
      const temporary = `${destination}.part`;
      await writeFile(temporary, buffer);
      await rename(temporary, destination);
      return result(job, buffer, 'downloaded');
    } catch (error) {
      lastError = error;
      await new Promise((resolve) => setTimeout(resolve, attempt * 700));
    }
  }
  return { ...job, status: 'failed', error: String(lastError) };
}

function result(job, buffer, status) {
  return {
    ...job,
    status,
    bytes: buffer.length,
    sha256: createHash('sha256').update(buffer).digest('hex'),
    header: job.kind.endsWith('csv') ? buffer.subarray(0, Math.min(buffer.length, 500)).toString('utf8').split(/\r?\n/)[0] : undefined,
  };
}

async function worker() {
  while (true) {
    const index = cursor++;
    if (index >= jobs.length) return;
    const item = await fetchJob(jobs[index]);
    results[index] = item;
    finished++;
    if (finished % 20 === 0 || finished === jobs.length) {
      console.log(`${finished}/${jobs.length} complete; restricted: ${results.filter((r) => r?.status === 'restricted').length}; failures: ${results.filter((r) => r?.status === 'failed').length}`);
      await writeFile(path.join(root, 'manifest.json'), JSON.stringify({
        generatedAt: new Date().toISOString(),
        total: jobs.length,
        completed: finished,
        results: results.filter(Boolean),
      }, null, 2));
    }
  }
}

console.log(`Downloading ${chartSlugs.length} charts (CSV + metadata) and ${explorerViews.length} explorer views`);
await Promise.all(Array.from({ length: 8 }, () => worker()));
const failures = results.filter((r) => r.status === 'failed');
const restricted = results.filter((r) => r.status === 'restricted');
const columns = ['kind', 'dataset', 'metric', 'submetric', 'slug', 'file', 'url', 'status', 'bytes', 'sha256', 'header', 'reason', 'error'];
const csvCell = (value) => `"${String(value ?? '').replaceAll('"', '""')}"`;
await writeFile(path.join(root, 'index.csv'), [
  columns.join(','),
  ...results.map((item) => columns.map((column) => csvCell(item[column])).join(',')),
].join('\n') + '\n');
console.log(`Finished: ${results.length - restricted.length - failures.length} successful, ${restricted.length} restricted, ${failures.length} failed`);
if (failures.length) {
  failures.forEach((failure) => console.error(`${failure.file}: ${failure.error}`));
  process.exitCode = 1;
}
