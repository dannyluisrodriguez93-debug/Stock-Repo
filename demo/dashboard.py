"""
Self-contained Flask + SSE real-time trading signal dashboard.

Run standalone:
    python -m demo.dashboard          # from repo root
    python demo/dashboard.py          # direct

The HTML / CSS / JS are embedded in this file for single-file deployment.
Flask and Chart.js (CDN) are the only external dependencies.
"""

from __future__ import annotations

import json
import time
import threading
from typing import Generator

from flask import Flask, Response, render_template_string

from demo.dashboard_state import DashboardState

# ---------------------------------------------------------------------------
# Shared state -- importers can replace this with their own instance
# ---------------------------------------------------------------------------
state = DashboardState()

# ---------------------------------------------------------------------------
# Flask application
# ---------------------------------------------------------------------------
app = Flask(__name__)

# ---------------------------------------------------------------------------
# HTML template (dark trading-terminal aesthetic)
# ---------------------------------------------------------------------------
_TEMPLATE = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Trading Signal Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>
<style>
/* ===== RESET & BASE ===== */
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg-primary:#0a0e17;
  --bg-card:#111827;
  --bg-card-alt:#151d2e;
  --border:#1e293b;
  --text-primary:#e2e8f0;
  --text-secondary:#94a3b8;
  --text-muted:#64748b;
  --green:#22c55e;
  --green-dim:#166534;
  --red:#ef4444;
  --red-dim:#991b1b;
  --amber:#f59e0b;
  --amber-dim:#92400e;
  --blue:#3b82f6;
  --cyan:#06b6d4;
  --purple:#a855f7;
  --font-mono:'Courier New',Consolas,'Liberation Mono',monospace;
}
html{font-size:13px}
body{
  background:var(--bg-primary);
  color:var(--text-primary);
  font-family:var(--font-mono);
  line-height:1.5;
  min-height:100vh;
}

/* ===== HEADER ===== */
.header{
  background:linear-gradient(135deg,#0f172a 0%,#1e1b4b 100%);
  border-bottom:1px solid var(--border);
  padding:10px 20px;
  display:flex;
  align-items:center;
  justify-content:space-between;
}
.header h1{font-size:1.15rem;letter-spacing:1px;color:var(--cyan)}
.header .clock{color:var(--text-secondary);font-size:.9rem}
.header .status-dot{
  display:inline-block;width:8px;height:8px;border-radius:50%;
  margin-right:6px;vertical-align:middle;
}
.header .status-dot.connected{background:var(--green);box-shadow:0 0 6px var(--green)}
.header .status-dot.disconnected{background:var(--red);box-shadow:0 0 6px var(--red)}

/* ===== ACCOUNT SUMMARY BAR ===== */
.account-bar{
  display:grid;
  grid-template-columns:repeat(auto-fit,minmax(140px,1fr));
  gap:1px;
  background:var(--border);
  border-bottom:1px solid var(--border);
}
.account-bar .metric{
  background:var(--bg-card);
  padding:10px 14px;
  text-align:center;
}
.account-bar .metric .label{
  font-size:.7rem;text-transform:uppercase;letter-spacing:.5px;
  color:var(--text-muted);margin-bottom:2px;
}
.account-bar .metric .value{
  font-size:1.05rem;font-weight:700;
}

/* ===== MAIN GRID ===== */
.grid{
  display:grid;
  grid-template-columns:1fr 1fr;
  grid-template-rows:auto auto auto;
  gap:1px;
  background:var(--border);
  flex:1;
}
.grid>.panel{background:var(--bg-card);overflow:hidden;display:flex;flex-direction:column}

.panel-header{
  background:var(--bg-card-alt);
  padding:8px 14px;
  font-size:.8rem;
  font-weight:700;
  text-transform:uppercase;
  letter-spacing:1px;
  color:var(--cyan);
  border-bottom:1px solid var(--border);
  display:flex;justify-content:space-between;align-items:center;
  flex-shrink:0;
}
.panel-header .badge{
  background:var(--blue);color:#fff;
  padding:1px 8px;border-radius:10px;font-size:.7rem;
}
.panel-body{
  padding:6px;
  overflow-y:auto;
  flex:1;
  min-height:0;
}

/* ===== SIGNALS FEED ===== */
.signal-item{
  padding:6px 8px;
  border-bottom:1px solid var(--border);
  font-size:.8rem;
  display:grid;
  grid-template-columns:60px 70px 1fr 70px 60px 50px 60px;
  gap:6px;
  align-items:center;
}
.signal-item:hover{background:rgba(59,130,246,.06)}
.signal-item .ts{color:var(--text-muted)}
.signal-item .ticker{font-weight:700;color:var(--cyan)}
.signal-item .catalyst{color:var(--text-secondary);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.signal-item .dir-long{color:var(--green)}
.signal-item .dir-short{color:var(--red)}
.signal-item .flag-yellow{color:var(--amber);font-weight:700}
.signal-item .flag-red{color:var(--red);font-weight:700}

/* ===== TABLES ===== */
.data-table{width:100%;border-collapse:collapse;font-size:.78rem}
.data-table thead th{
  position:sticky;top:0;
  background:var(--bg-card-alt);
  padding:6px 8px;
  text-align:right;
  color:var(--text-muted);
  font-weight:600;
  text-transform:uppercase;
  font-size:.68rem;
  letter-spacing:.5px;
  border-bottom:1px solid var(--border);
}
.data-table thead th:first-child{text-align:left}
.data-table tbody td{
  padding:5px 8px;
  text-align:right;
  border-bottom:1px solid rgba(30,41,59,.5);
  white-space:nowrap;
}
.data-table tbody td:first-child{text-align:left}
.data-table tbody tr:hover{background:rgba(59,130,246,.05)}
.profit{color:var(--green)}
.loss{color:var(--red)}
.row-profit{background:rgba(34,197,94,.04)}
.row-loss{background:rgba(239,68,68,.04)}

/* ===== EQUITY CHART ===== */
.chart-wrap{padding:10px;height:100%;min-height:220px;position:relative}
.chart-wrap canvas{width:100%!important;height:100%!important}

/* ===== SYSTEM LOG ===== */
.log-entry{
  font-size:.75rem;
  padding:3px 8px;
  border-bottom:1px solid rgba(30,41,59,.3);
  display:flex;gap:8px;
}
.log-entry .log-ts{color:var(--text-muted);flex-shrink:0;width:60px}
.log-entry .log-level{flex-shrink:0;width:50px;font-weight:700}
.log-entry .log-level.INFO{color:var(--blue)}
.log-entry .log-level.WARN{color:var(--amber)}
.log-entry .log-level.ERROR{color:var(--red)}
.log-entry .log-level.EXEC{color:var(--purple)}
.log-entry .log-level.SCAN{color:var(--cyan)}
.log-entry .log-msg{color:var(--text-secondary)}

/* ===== COLLAPSIBLE ===== */
.collapse-toggle{
  cursor:pointer;user-select:none;
}
.collapse-toggle::after{content:' ▼';font-size:.6rem}
.collapse-toggle.collapsed::after{content:' ▶';font-size:.6rem}

/* ===== SCROLLBARS ===== */
::-webkit-scrollbar{width:6px;height:6px}
::-webkit-scrollbar-track{background:var(--bg-primary)}
::-webkit-scrollbar-thumb{background:var(--text-muted);border-radius:3px}
::-webkit-scrollbar-thumb:hover{background:var(--text-secondary)}

/* ===== RESPONSIVE ===== */
@media(max-width:900px){
  .grid{grid-template-columns:1fr}
  .signal-item{grid-template-columns:50px 60px 1fr 50px 50px}
}

/* ===== EMPTY STATE ===== */
.empty-state{
  color:var(--text-muted);
  text-align:center;
  padding:30px;
  font-size:.85rem;
  font-style:italic;
}
</style>
</head>
<body>

<!-- ===== HEADER ===== -->
<div class="header">
  <h1>TRADING SIGNAL SYSTEM</h1>
  <div>
    <span class="status-dot connected" id="sseStatus"></span>
    <span id="sseLabel" style="color:var(--green);font-size:.75rem">LIVE</span>
    &nbsp;&nbsp;
    <span class="clock" id="clock"></span>
  </div>
</div>

<!-- ===== ACCOUNT SUMMARY ===== -->
<div class="account-bar" id="accountBar">
  <div class="metric"><div class="label">Starting Capital</div><div class="value" id="a_capital">$1,000.00</div></div>
  <div class="metric"><div class="label">Current Equity</div><div class="value" id="a_equity">$1,000.00</div></div>
  <div class="metric"><div class="label">Total P&amp;L</div><div class="value" id="a_pnl">$0.00</div></div>
  <div class="metric"><div class="label">P&amp;L %</div><div class="value" id="a_pnl_pct">0.00%</div></div>
  <div class="metric"><div class="label">Available Cash</div><div class="value" id="a_cash">$1,000.00</div></div>
  <div class="metric"><div class="label">Unsettled (T+1)</div><div class="value" id="a_unsettled">$0.00</div></div>
  <div class="metric"><div class="label">Day Trades Left</div><div class="value" id="a_daytrades">3 / 3</div></div>
  <div class="metric"><div class="label">Market Status</div><div class="value" id="a_market">Closed</div></div>
</div>

<!-- ===== MAIN GRID ===== -->
<div class="grid">

  <!-- ACTIVE SIGNALS -->
  <div class="panel" style="grid-column:1/3">
    <div class="panel-header">
      <span>Active Signals</span>
      <span class="badge" id="signalCount">0</span>
    </div>
    <div class="panel-body" id="signalFeed" style="max-height:220px">
      <div class="signal-item" style="font-weight:700;color:var(--text-muted);font-size:.7rem">
        <span>TIME</span><span>TICKER</span><span>CATALYST</span><span>DIR</span><span>MAG</span><span>CONF</span><span>FLAG</span>
      </div>
      <div id="signalList"></div>
    </div>
  </div>

  <!-- OPEN POSITIONS -->
  <div class="panel">
    <div class="panel-header">
      <span>Open Positions</span>
      <span class="badge" id="posCount">0</span>
    </div>
    <div class="panel-body" style="max-height:260px">
      <table class="data-table">
        <thead><tr>
          <th>Ticker</th><th>Dir</th><th>Qty</th><th>Entry</th><th>Current</th><th>P&amp;L $</th><th>P&amp;L %</th><th>Stop</th><th>Target</th><th>Held</th>
        </tr></thead>
        <tbody id="posBody"></tbody>
      </table>
      <div class="empty-state" id="posEmpty">No open positions</div>
    </div>
  </div>

  <!-- EQUITY CURVE -->
  <div class="panel">
    <div class="panel-header"><span>Equity Curve</span></div>
    <div class="chart-wrap">
      <canvas id="equityChart"></canvas>
    </div>
  </div>

  <!-- TRADE HISTORY -->
  <div class="panel" style="grid-column:1/3">
    <div class="panel-header">
      <span>Trade History</span>
      <span class="badge" id="tradeCount">0</span>
    </div>
    <div class="panel-body" style="max-height:240px">
      <table class="data-table">
        <thead><tr>
          <th>Entry</th><th>Exit</th><th>Ticker</th><th>Dir</th><th>Entry$</th><th>Exit$</th><th>Qty</th><th>Gross</th><th>Fees</th><th>Net P&amp;L</th><th>Cum P&amp;L</th><th>Trigger</th><th>Duration</th>
        </tr></thead>
        <tbody id="tradeBody"></tbody>
      </table>
      <div class="empty-state" id="tradeEmpty">No trades yet</div>
    </div>
  </div>

  <!-- SYSTEM LOG -->
  <div class="panel" style="grid-column:1/3">
    <div class="panel-header">
      <span class="collapse-toggle" id="logToggle" onclick="toggleLog()">System Log</span>
      <span class="badge" id="logCount">0</span>
    </div>
    <div class="panel-body" id="logBody" style="max-height:180px">
      <div id="logList"></div>
      <div class="empty-state" id="logEmpty">No events</div>
    </div>
  </div>

</div>

<script>
/* ================================================================
   DASHBOARD CLIENT  -- SSE consumer + DOM updater
   ================================================================ */

// ---------- clock ----------
function tickClock(){
  const now = new Date();
  document.getElementById('clock').textContent =
    now.toLocaleTimeString('en-US',{hour12:false}) + ' ' +
    now.toLocaleDateString('en-US',{month:'short',day:'numeric',year:'numeric'});
}
tickClock(); setInterval(tickClock, 1000);

// ---------- helpers ----------
function $(id){return document.getElementById(id)}
function money(v){
  const n = parseFloat(v)||0;
  return (n<0?'-':'') + '$' + Math.abs(n).toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g,',');
}
function pct(v){
  const n = parseFloat(v)||0;
  return (n>=0?'+':'') + n.toFixed(2) + '%';
}
function pnlClass(v){return parseFloat(v)>=0?'profit':'loss'}
function fmtSec(s){s=Math.round(s);if(s<60)return s+'s';if(s<3600)return Math.floor(s/60)+'m '+s%60+'s';return Math.floor(s/3600)+'h '+Math.floor((s%3600)/60)+'m'}
function rowPnlClass(v){return parseFloat(v)>=0?'row-profit':'row-loss'}

// ---------- equity chart ----------
const ctx = $('equityChart').getContext('2d');
const equityChart = new Chart(ctx, {
  type:'line',
  data:{
    labels:[],
    datasets:[{
      label:'Equity',
      data:[],
      borderColor:'#06b6d4',
      backgroundColor:'rgba(6,182,212,.08)',
      borderWidth:2,
      pointRadius:0,
      pointHitRadius:6,
      fill:true,
      tension:0.3
    }]
  },
  options:{
    responsive:true,
    maintainAspectRatio:false,
    animation:{duration:300},
    plugins:{
      legend:{display:false},
      tooltip:{
        backgroundColor:'#1e293b',
        titleColor:'#e2e8f0',
        bodyColor:'#94a3b8',
        borderColor:'#334155',
        borderWidth:1,
        callbacks:{
          label:function(c){return '$'+parseFloat(c.raw).toFixed(2)}
        }
      }
    },
    scales:{
      x:{
        ticks:{color:'#64748b',font:{size:10,family:'Courier New'},maxTicksLimit:10},
        grid:{color:'rgba(30,41,59,.5)'}
      },
      y:{
        ticks:{
          color:'#64748b',
          font:{size:10,family:'Courier New'},
          callback:function(v){return '$'+v}
        },
        grid:{color:'rgba(30,41,59,.5)'}
      }
    }
  }
});

// ---------- state cache ----------
let lastVersion = -1;

// ---------- render functions ----------
function renderAccount(a){
  $('a_capital').textContent = money(a.starting_capital);
  $('a_equity').textContent = money(a.current_equity);

  const pnlEl = $('a_pnl');
  pnlEl.textContent = money(a.total_pnl);
  pnlEl.style.color = a.total_pnl >= 0 ? 'var(--green)' : 'var(--red)';

  const pctEl = $('a_pnl_pct');
  pctEl.textContent = pct(a.total_pnl_pct);
  pctEl.style.color = a.total_pnl_pct >= 0 ? 'var(--green)' : 'var(--red)';

  $('a_cash').textContent = money(a.available_cash);
  $('a_unsettled').textContent = money(a.unsettled_funds);
  $('a_daytrades').textContent = a.day_trades_remaining + ' / 3';
  $('a_daytrades').style.color = a.day_trades_remaining<=1?'var(--red)':
                                  a.day_trades_remaining<=2?'var(--amber)':'var(--green)';

  const mktEl = $('a_market');
  if(a.market_open){
    mktEl.innerHTML = '<span style="color:var(--green)">OPEN</span>';
  } else {
    mktEl.innerHTML = '<span style="color:var(--red)">CLOSED</span>';
  }
  if(a.next_event){
    mktEl.innerHTML += '<br><span style="font-size:.7rem;color:var(--text-muted)">'+a.next_event+'</span>';
  }
}

function renderSignals(signals){
  $('signalCount').textContent = signals.length;
  if(!signals.length){
    $('signalList').innerHTML='<div class="empty-state">Waiting for signals...</div>';
    return;
  }
  let html = '';
  for(const s of signals){
    const tk = s.ticker || s.tickers || '';
    const dir = (s.direction||'').toLowerCase();
    const dirClass = (dir==='long'||dir==='bullish')?'dir-long':'dir-short';
    const dirLabel = (dir==='bullish')?'LONG':(dir==='bearish')?'SHORT':dir.toUpperCase();
    const flag = (s.flag_level||'').toUpperCase();
    const flagClass = flag==='RED'?'flag-red':'flag-yellow';
    const conf = typeof s.confidence==='number'? (s.confidence*100).toFixed(0)+'%' : s.confidence;
    html += '<div class="signal-item">' +
      '<span class="ts">'+esc(s.timestamp||'')+'</span>' +
      '<span class="ticker">'+esc(tk)+'</span>' +
      '<span class="catalyst">'+esc(s.catalyst||'')+'</span>' +
      '<span class="'+dirClass+'">'+dirLabel+'</span>' +
      '<span>'+esc(s.magnitude||'')+'</span>' +
      '<span>'+esc(conf)+'</span>' +
      '<span class="'+flagClass+'">'+esc(flag)+'</span>' +
    '</div>';
  }
  $('signalList').innerHTML = html;
}

function renderPositions(positions){
  $('posCount').textContent = positions.length;
  if(!positions.length){
    $('posBody').innerHTML='';
    $('posEmpty').style.display='block';
    return;
  }
  $('posEmpty').style.display='none';
  let html='';
  for(const p of positions){
    const upnl = parseFloat(p.unrealized_pnl)||0;
    const upct = parseFloat(p.unrealized_pct||p.unrealized_pnl_pct)||0;
    const cls = pnlClass(upnl);
    const dir = (p.direction||'LONG').toUpperCase();
    const held = p.time_held || (p.held_seconds ? fmtSec(p.held_seconds) : '--');
    html += '<tr class="'+rowPnlClass(upnl)+'">' +
      '<td style="font-weight:700;color:var(--cyan)">'+esc(p.ticker)+'</td>' +
      '<td class="'+(dir==='LONG'||dir==='BULLISH'?'profit':'loss')+'">'+dir+'</td>' +
      '<td>'+p.qty+'</td>' +
      '<td>'+money(p.entry_price)+'</td>' +
      '<td>'+money(p.current_price)+'</td>' +
      '<td class="'+cls+'">'+money(upnl)+'</td>' +
      '<td class="'+cls+'">'+pct(upct)+'</td>' +
      '<td>'+(p.stop_loss?money(p.stop_loss):'--')+'</td>' +
      '<td>'+(p.target?money(p.target):'--')+'</td>' +
      '<td>'+esc(held)+'</td>' +
    '</tr>';
  }
  $('posBody').innerHTML = html;
}

function renderTrades(trades){
  $('tradeCount').textContent = trades.length;
  if(!trades.length){
    $('tradeBody').innerHTML='';
    $('tradeEmpty').style.display='block';
    return;
  }
  $('tradeEmpty').style.display='none';
  let html='';
  let cumPnl = 0;
  for(const t of trades){
    const net = parseFloat(t.net_pnl||t.pnl_net)||0;
    const gross = parseFloat(t.gross_pnl||t.pnl_gross)||0;
    cumPnl += net;
    const cls = pnlClass(net);
    const cumCls = pnlClass(cumPnl);
    const dur = t.hold_duration || (t.hold_duration_sec ? fmtSec(t.hold_duration_sec) : '--');
    const dir = t.direction || 'long';
    html += '<tr class="'+rowPnlClass(net)+'">' +
      '<td>'+esc(t.entry_time||'')+'</td>' +
      '<td>'+esc(t.exit_time||'')+'</td>' +
      '<td style="font-weight:700;color:var(--cyan)">'+esc(t.ticker)+'</td>' +
      '<td>'+esc(dir)+'</td>' +
      '<td>'+money(t.entry_price)+'</td>' +
      '<td>'+money(t.exit_price)+'</td>' +
      '<td>'+t.qty+'</td>' +
      '<td class="'+cls+'">'+money(gross)+'</td>' +
      '<td>'+money(t.fees)+'</td>' +
      '<td class="'+cls+'">'+money(net)+'</td>' +
      '<td class="'+cumCls+'">'+money(cumPnl)+'</td>' +
      '<td>'+esc(t.exit_trigger||'')+'</td>' +
      '<td>'+esc(dur)+'</td>' +
    '</tr>';
  }
  $('tradeBody').innerHTML = html;
}

function renderEquity(curve){
  if(!curve.length) return;
  equityChart.data.labels = curve.map(function(p){return p[0]});
  equityChart.data.datasets[0].data = curve.map(function(p){return p[1]});
  equityChart.update();
}

function renderLog(logs){
  $('logCount').textContent = logs.length;
  if(!logs.length){
    $('logList').innerHTML='';
    $('logEmpty').style.display='block';
    return;
  }
  $('logEmpty').style.display='none';
  let html='';
  for(const l of logs){
    html += '<div class="log-entry">' +
      '<span class="log-ts">'+esc(l.timestamp||'')+'</span>' +
      '<span class="log-level '+esc(l.level||'INFO')+'">'+esc(l.level||'INFO')+'</span>' +
      '<span class="log-msg">'+esc(l.message||'')+'</span>' +
    '</div>';
  }
  $('logList').innerHTML = html;
}

function esc(s){
  if(s===null||s===undefined) return '';
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// ---------- log toggle ----------
function toggleLog(){
  const t=$('logToggle'), b=$('logBody');
  t.classList.toggle('collapsed');
  b.style.display = t.classList.contains('collapsed') ? 'none' : 'block';
}

// ---------- SSE connection ----------
let retryDelay = 1000;

function connectSSE(){
  const src = new EventSource('/stream');

  src.onopen = function(){
    $('sseStatus').className='status-dot connected';
    $('sseLabel').textContent='LIVE';
    $('sseLabel').style.color='var(--green)';
    retryDelay = 1000;
  };

  src.addEventListener('state', function(e){
    try{
      const d = JSON.parse(e.data);
      if(d.version === lastVersion) return;
      lastVersion = d.version;
      renderAccount(d.account_summary);
      renderSignals(d.active_signals);
      renderPositions(d.open_positions);
      renderTrades(d.trade_history);
      renderEquity(d.equity_curve);
      renderLog(d.system_log);
    }catch(err){
      console.error('SSE parse error', err);
    }
  });

  src.onerror = function(){
    src.close();
    $('sseStatus').className='status-dot disconnected';
    $('sseLabel').textContent='DISCONNECTED';
    $('sseLabel').style.color='var(--red)';
    setTimeout(connectSSE, retryDelay);
    retryDelay = Math.min(retryDelay * 2, 10000);
  };
}

connectSSE();
</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/")
def index() -> str:
    """Serve the single-page dashboard."""
    return render_template_string(_TEMPLATE)


@app.route("/stream")
def stream() -> Response:
    """SSE endpoint -- pushes full state snapshots when the version bumps."""

    def _generate() -> Generator[str, None, None]:
        last_version = -1
        while True:
            current_version = state.version
            if current_version != last_version:
                snapshot = state.snapshot()
                payload = json.dumps(snapshot, default=str)
                yield f"event: state\ndata: {payload}\n\n"
                last_version = current_version
            time.sleep(0.5)

    return Response(
        _generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@app.route("/api/state")
def api_state() -> dict:
    """JSON endpoint for one-shot polling (debugging / testing)."""
    return state.snapshot()


# ---------------------------------------------------------------------------
# Standalone demo mode -- injects fake data so you can see the UI working
# ---------------------------------------------------------------------------
def _run_demo_data_pump(st: DashboardState) -> None:
    """Background thread that feeds synthetic data into *st* so the
    dashboard has something to display when run standalone."""
    import random

    tickers = ["NVDA", "TSLA", "AAPL", "AMD", "META", "SPY", "BA", "MSFT"]
    catalysts = [
        "Earnings beat", "FDA approval", "Analyst upgrade", "Volume spike",
        "Insider buy", "Sector rotation", "Gap up", "Breakout",
        "News catalyst", "RSI oversold bounce",
    ]
    base_prices = {
        "NVDA": 135.0, "TSLA": 245.0, "AAPL": 192.0, "AMD": 165.0,
        "META": 510.0, "SPY": 525.0, "BA": 188.0, "MSFT": 420.0,
    }

    equity = 1000.0
    cash = 1000.0
    positions: list[dict] = []
    trades: list[dict] = []
    step = 0

    st.add_equity_point(time.strftime("%H:%M:%S"), equity)
    st.add_log("Demo data pump started", "INFO")
    st.add_log("Scanning watchlist: " + ", ".join(tickers), "SCAN")

    while True:
        step += 1
        time.sleep(random.uniform(2.0, 4.0))

        # -- emit a signal every cycle --
        ticker = random.choice(tickers)
        direction = random.choice(["Long", "Short"])
        flag = random.choice(["Yellow", "Yellow", "Red"])
        mag = round(random.uniform(0.5, 5.0), 1)
        conf = round(random.uniform(0.4, 0.95), 2)

        st.add_signal({
            "ticker": ticker,
            "catalyst": random.choice(catalysts),
            "direction": direction,
            "magnitude": str(mag) + "%",
            "confidence": str(int(conf * 100)) + "%",
            "flag_level": flag,
        })
        st.add_log(
            f"Signal: {ticker} {direction} | {flag} flag | conf={int(conf*100)}%",
            "SCAN",
        )

        # -- maybe open a position (30 % chance) --
        if random.random() < 0.30 and len(positions) < 4:
            price = base_prices.get(ticker, 100.0) * random.uniform(0.97, 1.03)
            qty = max(1, int(50 / price))
            cost = round(price * qty, 2)
            if cost < cash:
                cash -= cost
                pos = {
                    "ticker": ticker,
                    "direction": direction,
                    "qty": qty,
                    "entry_price": round(price, 2),
                    "current_price": round(price, 2),
                    "unrealized_pnl": 0.0,
                    "unrealized_pnl_pct": 0.0,
                    "stop_loss": round(price * 0.97, 2),
                    "target": round(price * 1.05, 2),
                    "time_held": "0m",
                    "_entry_time": time.strftime("%H:%M:%S"),
                    "_step_opened": step,
                }
                positions.append(pos)
                st.add_log(
                    f"OPEN {direction} {qty}x {ticker} @ ${price:.2f}",
                    "EXEC",
                )

        # -- update existing positions --
        for p in positions:
            drift = random.uniform(-0.015, 0.02)
            p["current_price"] = round(p["current_price"] * (1 + drift), 2)
            raw_pnl = (p["current_price"] - p["entry_price"]) * p["qty"]
            if p["direction"] == "Short":
                raw_pnl = -raw_pnl
            p["unrealized_pnl"] = round(raw_pnl, 2)
            p["unrealized_pnl_pct"] = round(
                raw_pnl / (p["entry_price"] * p["qty"]) * 100, 2
            )
            mins = (step - p["_step_opened"]) * 3
            p["time_held"] = f"{mins}m"

        st.update_positions(positions)

        # -- maybe close a position --
        if positions and random.random() < 0.25:
            p = positions.pop(random.randint(0, len(positions) - 1))
            fees = round(random.uniform(0.01, 0.10), 2)
            gross = p["unrealized_pnl"]
            net = round(gross - fees, 2)
            cash += round(p["entry_price"] * p["qty"] + gross, 2)
            trade = {
                "entry_time": p["_entry_time"],
                "exit_time": time.strftime("%H:%M:%S"),
                "ticker": p["ticker"],
                "direction": p["direction"],
                "entry_price": p["entry_price"],
                "exit_price": p["current_price"],
                "qty": p["qty"],
                "gross_pnl": round(gross, 2),
                "fees": fees,
                "net_pnl": net,
                "exit_trigger": random.choice([
                    "Stop loss", "Target hit", "Trailing stop", "Manual",
                ]),
                "hold_duration": p["time_held"],
            }
            trades.append(trade)
            st.add_trade(trade)
            st.add_log(
                f"CLOSE {p['ticker']} | net={net:+.2f}",
                "EXEC",
            )

            equity = cash + sum(
                pos["entry_price"] * pos["qty"] + pos["unrealized_pnl"]
                for pos in positions
            )
            st.add_equity_point(time.strftime("%H:%M:%S"), round(equity, 2))

        # -- always recompute equity for the account bar --
        pos_value = sum(
            pos["entry_price"] * pos["qty"] + pos["unrealized_pnl"]
            for pos in positions
        )
        equity = round(cash + pos_value, 2)
        total_pnl = round(equity - 1000.0, 2)
        unsettled = round(
            sum(t["entry_price"] * t["qty"] for t in trades[-2:]) * 0.1, 2
        )
        day_trades = max(0, 3 - len([t for t in trades[-5:]]))

        st.update_account(
            current_equity=equity,
            total_pnl=total_pnl,
            total_pnl_pct=round(total_pnl / 10.0, 2),  # pct of 1000
            available_cash=round(cash, 2),
            unsettled_funds=unsettled,
            day_trades_remaining=day_trades,
            market_open=True,
            market_status="Open",
            next_event="Closes in 2h 14m",
        )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def run(host: str = "127.0.0.1", port: int = 5000, debug: bool = False,
        demo_mode: bool = True) -> None:
    """Launch the dashboard server.

    Parameters
    ----------
    demo_mode : bool
        If *True* (default when run standalone), a background thread
        injects synthetic data so you can see the UI in action.
    """
    if demo_mode:
        t = threading.Thread(target=_run_demo_data_pump, args=(state,), daemon=True)
        t.start()

    app.run(host=host, port=port, debug=debug, threaded=True)


if __name__ == "__main__":
    print("Starting Trading Signal Dashboard on http://127.0.0.1:5000")
    print("Press Ctrl+C to stop.\n")
    run(debug=False, demo_mode=True)
