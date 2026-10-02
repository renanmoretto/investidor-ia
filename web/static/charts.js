// Fixed order, never cycled: a series keeps its color when the series count changes.
const CHART_COLORS = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300'];
const CHART_SINGLE_COLOR = '#171717';
const CHART_FONT = '"JetBrains Mono", ui-monospace, monospace';

const chartNumber = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 2 });
const chartCompact = new Intl.NumberFormat('pt-BR', { notation: 'compact', maximumFractionDigits: 1 });

function chartValue(value, unit) {
  if (value === null || value === undefined) return '-';
  return unit ? `${chartNumber.format(value)} ${unit}` : chartNumber.format(value);
}

function chartElement(tag, className, text) {
  const el = document.createElement(tag);
  if (className) el.className = className;
  if (text !== undefined) el.textContent = text;
  return el;
}

function chartTable(spec) {
  const table = chartElement('table', 'w-full text-left text-[11px]');
  const head = table.createTHead().insertRow();
  head.appendChild(chartElement('th', 'py-1 pr-3 font-medium text-neutral-400', ''));
  spec.series.forEach((series) => {
    head.appendChild(chartElement('th', 'py-1 pr-3 text-right font-medium text-neutral-400', series.name));
  });
  const body = table.createTBody();
  spec.labels.forEach((label, index) => {
    const row = body.insertRow();
    row.className = 'border-t border-neutral-100';
    row.appendChild(chartElement('td', 'py-1 pr-3 text-neutral-500', label));
    spec.series.forEach((series) => {
      row.appendChild(chartElement('td', 'py-1 pr-3 text-right tabular-nums', chartValue(series.values[index], spec.unit)));
    });
  });
  return table;
}

function renderChart(el) {
  if (el.dataset.rendered) return;
  el.dataset.rendered = 'true';

  const spec = JSON.parse(el.dataset.chart);
  const single = spec.series.length === 1;
  const colors = spec.series.map((_, index) => (single ? CHART_SINGLE_COLOR : CHART_COLORS[index]));

  el.classList.add('rounded-xl', 'border', 'border-neutral-200', 'p-4');
  el.appendChild(chartElement('figcaption', 'text-[13px] font-semibold', spec.title));
  if (spec.unit) el.appendChild(chartElement('p', 'mt-0.5 text-[11px] text-neutral-400', spec.unit));

  const plot = chartElement('div', 'relative mt-3 h-64');
  const canvas = document.createElement('canvas');
  plot.appendChild(canvas);
  el.appendChild(plot);

  const details = chartElement('details', 'mt-3 text-[11px]');
  details.appendChild(chartElement('summary', 'cursor-pointer text-neutral-400 hover:text-neutral-900', 'Ver dados'));
  const tableWrap = chartElement('div', 'mt-2 overflow-x-auto');
  tableWrap.appendChild(chartTable(spec));
  details.appendChild(tableWrap);
  el.appendChild(details);

  if (!window.Chart) {
    console.warn('chart library not loaded, showing the data table only', spec.title);
    plot.remove();
    details.open = true;
    return;
  }

  const ticks = { color: '#737373', font: { family: CHART_FONT, size: 10 } };
  new Chart(canvas, {
    type: spec.type,
    data: {
      labels: spec.labels,
      datasets: spec.series.map((series, index) => ({
        label: series.name,
        data: series.values,
        borderColor: colors[index],
        backgroundColor: colors[index],
        borderWidth: spec.type === 'line' ? 2 : 0,
        pointRadius: 3,
        pointHoverRadius: 5,
        pointBorderColor: '#ffffff',
        pointBorderWidth: 1,
        spanGaps: true,
        borderRadius: 4,
        maxBarThickness: 28,
      })),
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 250 },
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: {
          display: !single,
          position: 'bottom',
          labels: { color: '#525252', font: { family: CHART_FONT, size: 11 }, usePointStyle: true, boxHeight: 6 },
        },
        tooltip: {
          backgroundColor: '#171717',
          titleFont: { family: CHART_FONT, size: 11 },
          bodyFont: { family: CHART_FONT, size: 11 },
          padding: 10,
          callbacks: {
            label: (item) => ` ${item.dataset.label}: ${chartValue(item.parsed.y, spec.unit)}`,
          },
        },
      },
      scales: {
        x: { grid: { display: false }, border: { color: '#e5e5e5' }, ticks },
        y: {
          grid: { color: '#f0f0f0' },
          border: { display: false },
          ticks: { ...ticks, callback: (value) => chartCompact.format(value) },
        },
      },
    },
  });
}

function renderCharts(root = document) {
  root.querySelectorAll('[data-chart]').forEach(renderChart);
}
