const $ = (id) => document.getElementById(id);
const fmt = (n) => (n == null ? "—" : Number(n).toLocaleString("en-IN", { maximumFractionDigits: 2 }));
const inr = (n) => (n == null ? "—" : "₹" + fmt(n));
const cls = (n) => (n > 0 ? "pos" : n < 0 ? "neg" : "");

async function api(path, opts) {
  const r = await fetch(path, opts);
  return r.json();
}
const post = (path, body) =>
  api(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: body ? JSON.stringify(body) : undefined });

// --- controls ---
$("btnStart").onclick = () => post("/api/start");
$("btnStop").onclick = () => post("/api/stop");
$("btnStep").onclick = () => post("/api/step");
$("btnPanic").onclick = () => {
  if (confirm("Flatten ALL positions and engage the kill switch?")) post("/api/panic");
};
$("btnSummary").onclick = async () => {
  $("aiOutput").textContent = "Thinking…";
  const d = await api("/api/ai/summary");
  $("aiOutput").textContent = d.summary;
};
$("btnRisk").onclick = async () => {
  $("aiOutput").textContent = "Thinking…";
  const d = await api("/api/ai/risk");
  $("aiOutput").textContent = d.commentary;
};
$("btnAsk").onclick = async () => {
  const q = $("aiInput").value.trim();
  if (!q) return;
  $("aiOutput").textContent = "Thinking…";
  const d = await post("/api/ai/ask", { question: q });
  $("aiOutput").textContent = d.answer;
};
$("aiInput").addEventListener("keydown", (e) => { if (e.key === "Enter") $("btnAsk").click(); });

// --- equity chart ---
let chart;
function initChart() {
  const ctx = $("equityChart").getContext("2d");
  chart = new Chart(ctx, {
    type: "line",
    data: { labels: [], datasets: [{ data: [], borderColor: "#4d9fff", backgroundColor: "rgba(77,159,255,.08)", fill: true, tension: 0.25, pointRadius: 0, borderWidth: 2 }] },
    options: {
      animation: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: "#8a93a6", maxTicksLimit: 6 }, grid: { color: "#1c2333" } },
        y: { ticks: { color: "#8a93a6" }, grid: { color: "#1c2333" } },
      },
    },
  });
}
async function refreshChart() {
  const data = await api("/api/equity?limit=300");
  chart.data.labels = data.map((d) => new Date(d.ts).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" }));
  chart.data.datasets[0].data = data.map((d) => d.equity);
  chart.update();
}

// --- render status ---
function renderStatus(s) {
  $("liveDot").className = "dot" + (s.running ? " on" : "");
  const mb = $("modeBadge");
  mb.textContent = s.mode.toUpperCase();
  mb.className = "badge " + s.mode;
  $("dataBadge").textContent = "data: " + s.data_source;
  $("marketBadge").textContent = s.market_open ? "market OPEN" : "market closed";

  $("kpiEquity").textContent = inr(s.equity);
  $("kpiCash").textContent = inr(s.cash);
  const pnl = $("kpiPnl");
  pnl.textContent = inr(s.day_realized_pnl);
  pnl.className = cls(s.day_realized_pnl);
  $("kpiPositions").textContent = s.open_positions.length + " / " + s.limits.max_open_positions;
  $("kpiStrategy").textContent = s.strategy;

  const banner = $("blockBanner");
  if (s.block_reason) {
    banner.hidden = false;
    banner.textContent = "TRADING BLOCKED — " + s.block_reason;
  } else {
    banner.hidden = true;
  }

  const pb = $("posTable").querySelector("tbody");
  pb.innerHTML = s.open_positions.length
    ? s.open_positions.map((p) => `<tr><td>${p.symbol}</td><td>${p.qty}</td><td>${fmt(p.avg_price)}</td><td>${fmt(p.last_price)}</td><td class="${cls(p.unrealized_pnl)}">${fmt(p.unrealized_pnl)}</td></tr>`).join("")
    : `<tr><td colspan="5" class="muted">No open positions</td></tr>`;

  const L = s.limits;
  $("limitsList").innerHTML = `
    <li><span>Max per-trade value</span><b>${inr(L.max_trade_value)}</b></li>
    <li><span>Max open positions</span><b>${L.max_open_positions}</b></li>
    <li><span>Daily loss limit</span><b>${inr(L.daily_loss_limit)}</b></li>
    <li><span>Stop-loss</span><b>${(L.stop_loss_pct * 100).toFixed(1)}%</b></li>
    <li><span>Take-profit</span><b>${(L.take_profit_pct * 100).toFixed(1)}%</b></li>
    <li><span>Last loop</span><b>${s.last_loop_note}</b></li>`;
}

function renderTrades(trades) {
  const tb = $("tradeTable").querySelector("tbody");
  tb.innerHTML = trades.length
    ? trades.map((t) => `<tr>
        <td>${new Date(t.ts).toLocaleTimeString("en-IN")}</td>
        <td>${t.symbol}</td>
        <td><span class="tag ${t.side}">${t.side}</span></td>
        <td>${t.qty}</td>
        <td>${fmt(t.price)}</td>
        <td><span class="tag ${t.status}">${t.status}</span></td>
        <td class="${cls(t.realized_pnl)}">${t.realized_pnl ? fmt(t.realized_pnl) : "—"}</td>
        <td class="muted">${t.reason || ""}</td>
      </tr>`).join("")
    : `<tr><td colspan="8" class="muted">No trades yet</td></tr>`;
}

// --- live stream ---
function connectWS() {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${proto}://${location.host}/ws`);
  ws.onmessage = (e) => {
    const { status, trades } = JSON.parse(e.data);
    renderStatus(status);
    renderTrades(trades);
  };
  ws.onclose = () => setTimeout(connectWS, 3000);
}

initChart();
connectWS();
refreshChart();
setInterval(refreshChart, 10000);
