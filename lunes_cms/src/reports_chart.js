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
(function () {
    var BAR_COLOR = "#1d4e8a";
    var LINE_COLOR = "#d97706";
    var AXIS_COLOR = "#999";
    var GRID_COLOR = "#eee";
    var TEXT_COLOR = "#444";

    function renderReportsChart(canvas, data) {
        var ctx = canvas.getContext("2d");
        var dpr = window.devicePixelRatio || 1;
        var cssWidth = canvas.clientWidth || canvas.parentNode.clientWidth || 600;
        var cssHeight = canvas.clientHeight || 360;
        canvas.width = Math.round(cssWidth * dpr);
        canvas.height = Math.round(cssHeight * dpr);
        ctx.setTransform(1, 0, 0, 1, 0, 0);
        ctx.scale(dpr, dpr);
        ctx.clearRect(0, 0, cssWidth, cssHeight);

        var labels = data.labels || [];
        var barValues = (data.bar && data.bar.values) || [];
        var lineValues = (data.line && data.line.values) || [];
        var n = labels.length;

        var padding = { top: 28, right: 56, bottom: 40, left: 56 };
        var chartWidth = cssWidth - padding.left - padding.right;
        var chartHeight = cssHeight - padding.top - padding.bottom;

        if (n === 0) {
            ctx.fillStyle = TEXT_COLOR;
            ctx.font = "14px sans-serif";
            ctx.textAlign = "center";
            ctx.fillText("No data in selected range", cssWidth / 2, cssHeight / 2);
            return;
        }

        var maxBar = Math.max(1, Math.max.apply(null, barValues.length ? barValues : [0]));
        var maxLine = Math.max(1, Math.max.apply(null, lineValues.length ? lineValues : [0]));
        // Round axes up to nicer numbers so the gridlines are readable.
        maxBar = niceMax(maxBar);
        maxLine = niceMax(maxLine);

        // Gridlines + Y-axis labels (left = bar count, right = avg duration seconds).
        var ySteps = 4;
        ctx.font = "11px sans-serif";
        for (var i = 0; i <= ySteps; i++) {
            var y = padding.top + chartHeight - (chartHeight * i) / ySteps;
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
        var slot = chartWidth / n;
        var barWidth = Math.max(2, slot - 4);
        ctx.fillStyle = BAR_COLOR;
        for (var bi = 0; bi < n; bi++) {
            var v = barValues[bi] || 0;
            var bh = (v / maxBar) * chartHeight;
            var bx = padding.left + slot * bi + (slot - barWidth) / 2;
            var by = padding.top + chartHeight - bh;
            ctx.fillRect(bx, by, barWidth, bh);
        }

        // Line + points.
        ctx.strokeStyle = LINE_COLOR;
        ctx.lineWidth = 2;
        ctx.beginPath();
        for (var li = 0; li < n; li++) {
            var lv = lineValues[li] || 0;
            var lx = padding.left + slot * li + slot / 2;
            var ly = padding.top + chartHeight - (lv / maxLine) * chartHeight;
            if (li === 0) {
                ctx.moveTo(lx, ly);
            } else {
                ctx.lineTo(lx, ly);
            }
        }
        ctx.stroke();
        ctx.fillStyle = LINE_COLOR;
        for (var pi = 0; pi < n; pi++) {
            var pv = lineValues[pi] || 0;
            var px = padding.left + slot * pi + slot / 2;
            var py = padding.top + chartHeight - (pv / maxLine) * chartHeight;
            ctx.beginPath();
            ctx.arc(px, py, 3, 0, Math.PI * 2);
            ctx.fill();
        }

        // X-axis labels (sample to avoid overlap on long ranges).
        ctx.fillStyle = TEXT_COLOR;
        ctx.textAlign = "center";
        var stride = Math.max(1, Math.ceil(n / 8));
        for (var xi = 0; xi < n; xi += stride) {
            var lx2 = padding.left + slot * xi + slot / 2;
            ctx.fillText(labels[xi], lx2, padding.top + chartHeight + 18);
        }

        // Legend (top-left, simple horizontal layout).
        ctx.font = "12px sans-serif";
        ctx.textAlign = "left";
        var legendY = 6;
        var cursor = padding.left;
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

    function niceMax(value) {
        if (value <= 1) return 1;
        var pow10 = Math.pow(10, Math.floor(Math.log10(value)));
        var normalized = value / pow10;
        var nice;
        if (normalized <= 1) nice = 1;
        else if (normalized <= 2) nice = 2;
        else if (normalized <= 5) nice = 5;
        else nice = 10;
        return nice * pow10;
    }

    window.renderReportsChart = renderReportsChart;
    document.dispatchEvent(new Event("reports-chart-ready"));
})();
