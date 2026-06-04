// Renders a combined bar+line chart on a <canvas> element. Used by the analytics
// reports admin views. Vendored to avoid a CDN runtime dependency; intentionally
// minimal (no zoom, pan, or animation) since the dataset size is bounded by the
// admin's date-range selector.
//
// data shape:
//   {
//     labels: ["2026-01-01", ...],
//     bar:   { label: "Sessions",        values: [12, 8, ...] },
//     line:  { label: "Avg duration (s)", values: [45, 60, ...] }
//   }

interface ChartSeries {
    label: string;
    values: number[];
}

interface ChartData {
    labels: string[];
    bar: ChartSeries;
    line: ChartSeries;
}

const BAR_COLOR = "#1d4e8a";
const LINE_COLOR = "#d97706";
const AXIS_COLOR = "#999";
const GRID_COLOR = "#eee";
const TEXT_COLOR = "#444";

function renderReportsChart(canvas: HTMLCanvasElement, data: ChartData): void {
    const ctx = canvas.getContext("2d")!;
    const dpr = window.devicePixelRatio || 1;
    const cssWidth = canvas.clientWidth || (canvas.parentNode as HTMLElement).clientWidth || 600;
    const cssHeight = canvas.clientHeight || 360;
    canvas.width = Math.round(cssWidth * dpr);
    canvas.height = Math.round(cssHeight * dpr);
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, cssWidth, cssHeight);

    const labels = data.labels || [];
    const barValues = (data.bar && data.bar.values) || [];
    const lineValues = (data.line && data.line.values) || [];
    const n = labels.length;

    const padding = { top: 28, right: 56, bottom: 40, left: 56 };
    const chartWidth = cssWidth - padding.left - padding.right;
    const chartHeight = cssHeight - padding.top - padding.bottom;

    if (n === 0) {
        ctx.fillStyle = TEXT_COLOR;
        ctx.font = "14px sans-serif";
        ctx.textAlign = "center";
        ctx.fillText("No data in selected range", cssWidth / 2, cssHeight / 2);
        return;
    }

    let maxBar = Math.max(1, Math.max(...(barValues.length ? barValues : [0])));
    let maxLine = Math.max(1, Math.max(...(lineValues.length ? lineValues : [0])));
    // Round axes up to nicer numbers so the gridlines are readable.
    maxBar = niceMax(maxBar);
    maxLine = niceMax(maxLine);

    // Gridlines + Y-axis labels (left = bar count, right = avg duration seconds).
    const ySteps = 4;
    ctx.font = "11px sans-serif";
    for (let i = 0; i <= ySteps; i++) {
        const y = padding.top + chartHeight - (chartHeight * i) / ySteps;
        ctx.strokeStyle = GRID_COLOR;
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(padding.left, y);
        ctx.lineTo(padding.left + chartWidth, y);
        ctx.stroke();

        ctx.fillStyle = TEXT_COLOR;
        ctx.textAlign = "right";
        ctx.fillText(String(Math.round((maxBar * i) / ySteps)), padding.left - 6, y + 3);
        ctx.textAlign = "left";
        ctx.fillText(String(Math.round((maxLine * i) / ySteps)), padding.left + chartWidth + 6, y + 3);
    }

    // Axis lines.
    ctx.strokeStyle = AXIS_COLOR;
    ctx.beginPath();
    ctx.moveTo(padding.left, padding.top);
    ctx.lineTo(padding.left, padding.top + chartHeight);
    ctx.lineTo(padding.left + chartWidth, padding.top + chartHeight);
    ctx.stroke();

    // Bars.
    const slot = chartWidth / n;
    const barWidth = Math.max(2, slot - 4);
    ctx.fillStyle = BAR_COLOR;
    for (let bi = 0; bi < n; bi++) {
        const v = barValues[bi] || 0;
        const bh = (v / maxBar) * chartHeight;
        const bx = padding.left + slot * bi + (slot - barWidth) / 2;
        const by = padding.top + chartHeight - bh;
        ctx.fillRect(bx, by, barWidth, bh);
    }

    // Line + points.
    ctx.strokeStyle = LINE_COLOR;
    ctx.lineWidth = 2;
    ctx.beginPath();
    for (let li = 0; li < n; li++) {
        const lv = lineValues[li] || 0;
        const lx = padding.left + slot * li + slot / 2;
        const ly = padding.top + chartHeight - (lv / maxLine) * chartHeight;
        if (li === 0) {
            ctx.moveTo(lx, ly);
        } else {
            ctx.lineTo(lx, ly);
        }
    }
    ctx.stroke();
    ctx.fillStyle = LINE_COLOR;
    for (let pi = 0; pi < n; pi++) {
        const pv = lineValues[pi] || 0;
        const px = padding.left + slot * pi + slot / 2;
        const py = padding.top + chartHeight - (pv / maxLine) * chartHeight;
        ctx.beginPath();
        ctx.arc(px, py, 3, 0, Math.PI * 2);
        ctx.fill();
    }

    // X-axis labels (sample to avoid overlap on long ranges).
    ctx.fillStyle = TEXT_COLOR;
    ctx.textAlign = "center";
    const stride = Math.max(1, Math.ceil(n / 8));
    for (let xi = 0; xi < n; xi += stride) {
        const lx2 = padding.left + slot * xi + slot / 2;
        ctx.fillText(labels[xi], lx2, padding.top + chartHeight + 18);
    }

    // Legend (top-left, simple horizontal layout).
    ctx.font = "12px sans-serif";
    ctx.textAlign = "left";
    const legendY = 6;
    let cursor = padding.left;
    ctx.fillStyle = BAR_COLOR;
    ctx.fillRect(cursor, legendY, 12, 12);
    cursor += 18;
    ctx.fillStyle = TEXT_COLOR;
    ctx.fillText(data.bar.label, cursor, legendY + 10);
    cursor += ctx.measureText(data.bar.label).width + 16;
    ctx.fillStyle = LINE_COLOR;
    ctx.fillRect(cursor, legendY, 12, 12);
    cursor += 18;
    ctx.fillStyle = TEXT_COLOR;
    ctx.fillText(data.line.label, cursor, legendY + 10);
}

function niceMax(value: number): number {
    if (value <= 1) return 1;
    const pow10 = Math.pow(10, Math.floor(Math.log10(value)));
    const normalized = value / pow10;
    let nice: number;
    if (normalized <= 1) nice = 1;
    else if (normalized <= 2) nice = 2;
    else if (normalized <= 5) nice = 5;
    else nice = 10;
    return nice * pow10;
}

window.renderReportsChart = renderReportsChart;
document.dispatchEvent(new Event("reports-chart-ready"));
