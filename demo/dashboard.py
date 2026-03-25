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
  if(a.day_trades_remaining >= 999){
    $('a_daytrades').textContent = 'Unlimited';
    $('a_daytrades').style.color = 'var(--cyan)';
  } else {
    $('a_daytrades').textContent = a.day_trades_remaining + ' / 3';
    $('a_daytrades').style.color = a.day_trades_remaining<=1?'var(--red)':
                                    a.day_trades_remaining<=2?'var(--amber)':'var(--green)';
  }

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
    dashboard has something to display when run standalone.

    v2 — realistic hold times, price-driven exits, simulated clock,
    and comprehensive logging for optimization analysis.
    """
    import random
    from datetime import datetime, timedelta
    from demo.config import (
        DEMO_MIN_HOLD_STEPS,
        DEMO_SIM_MINUTES_PER_STEP,
        SEC_FEE_RATE,
        FINRA_TAF_RATE,
        FINRA_TAF_CAP,
        SLIPPAGE_MIN_PCT,
        SLIPPAGE_MAX_PCT,
        MAX_POSITION_PCT,
    )
    from demo.demo_signals import (
        CATALYST_TEMPLATES, TICKER_SECTOR,
        INSIDER_CONFIDENCE_BOOST, CONGRESSIONAL_CONFIDENCE_BOOST,
    )
    from demo.insider_signals import InsiderSignalSource, boost_signal_with_insider

    insider_source = InsiderSignalSource()

    tickers = ["NVDA", "TSLA", "AAPL", "AMD", "META", "SPY", "BA", "MSFT",
               "GOOGL", "AMZN", "LMT", "RTX", "GD", "NOC"]
    base_prices = {
        "NVDA": 135.0, "TSLA": 245.0, "AAPL": 192.0, "AMD": 165.0,
        "META": 510.0, "SPY": 525.0, "BA": 188.0, "MSFT": 420.0,
        "GOOGL": 175.0, "AMZN": 195.0, "LMT": 460.0, "RTX": 120.0,
        "GD": 295.0, "NOC": 470.0,
    }

    # Simulated clock — starts at 9:30 AM and advances each step
    sim_time = datetime.now().replace(hour=9, minute=30, second=0, microsecond=0)

    equity = 1000.0
    cash = 1000.0
    starting_capital = 1000.0
    positions: list[dict] = []
    trades: list[dict] = []
    step = 0
    total_trades = 0
    winning_trades = 0
    total_fees_paid = 0.0

    # Trailing stop tracking: ticker -> high water mark
    high_water_marks: dict[str, float] = {}

    def sim_ts() -> str:
        return sim_time.strftime("%H:%M:%S")

    def compute_fees(price: float, qty: int) -> float:
        sec = price * qty * SEC_FEE_RATE
        taf = min(qty * FINRA_TAF_RATE, FINRA_TAF_CAP)
        return round(sec + taf, 4)

    def apply_slippage(price: float, is_buy: bool) -> float:
        slip = random.uniform(SLIPPAGE_MIN_PCT, SLIPPAGE_MAX_PCT)
        return round(price * (1 + slip) if is_buy else price * (1 - slip), 2)

    st.add_equity_point(sim_ts(), equity)
    st.add_log("Demo simulation engine started", "INFO")
    st.add_log(f"Starting capital: ${starting_capital:,.2f}", "INFO")
    st.add_log(f"Watchlist: {', '.join(tickers)} ({len(tickers)} tickers)", "SCAN")
    st.add_log(f"Min hold: {DEMO_MIN_HOLD_STEPS} cycles | Position limit: {MAX_POSITION_PCT*100:.0f}% of equity", "INFO")
    st.add_log(f"Exit strategies: Take-profit | Trailing stop (1.5%) | Hard stop-loss | Time decay | Volume divergence", "INFO")
    st.add_log("Unlimited day trades enabled (demo mode)", "INFO")

    while True:
        step += 1
        time.sleep(random.uniform(2.0, 4.0))

        # Advance simulated clock by 3-6 minutes per step
        sim_advance = random.randint(DEMO_SIM_MINUTES_PER_STEP[0], DEMO_SIM_MINUTES_PER_STEP[1])
        sim_time += timedelta(minutes=sim_advance)

        # Wrap around at market close, restart next "day"
        if sim_time.hour >= 16:
            sim_time = sim_time.replace(hour=9, minute=30, second=0)
            st.add_log("--- Market close / new session ---", "INFO")

        st.add_log(f"--- Scan cycle #{step} | {sim_ts()} ---", "INFO")

        # -- emit a signal --
        ticker = random.choice(tickers)
        sector = TICKER_SECTOR.get(ticker, "technical")
        templates = CATALYST_TEMPLATES.get(sector, CATALYST_TEMPLATES["technical"])
        headline = random.choice(templates).format(ticker=ticker)
        direction = random.choice(["Long", "Short"])
        mag = round(random.uniform(0.5, 5.0), 1)
        conf = round(random.uniform(0.4, 0.95), 2)
        flag = "Red" if mag >= 3.0 and conf >= 0.6 else "Yellow"
        rsi = round(random.uniform(25, 75), 1)
        vol_ratio = round(random.uniform(0.8, 3.5), 2)

        st.add_signal({
            "ticker": ticker,
            "catalyst": headline,
            "catalyst_type": sector,
            "direction": direction,
            "magnitude": str(mag) + "%",
            "confidence": str(int(conf * 100)) + "%",
            "flag_level": flag,
            "timestamp": sim_ts(),
        })
        st.add_log(
            f"Signal: {ticker} {direction} | {flag.upper()} flag | mag={mag} conf={int(conf*100)}% "
            f"| RSI={rsi} vol_ratio={vol_ratio}x | sector={sector}",
            "SCAN",
        )
        st.add_log(f"  Catalyst: {headline[:100]}", "SCAN")

        # -- scan for insider / congressional signals --
        insider_signals = insider_source.scan_all(sim_time=sim_time, tickers=tickers)
        for isig in insider_signals:
            src_label = "INSIDER" if isig["source"] == "SEC_Form4" else "CONGRESS"
            st.add_signal({
                "ticker": isig["ticker"],
                "catalyst": isig["headline"],
                "catalyst_type": isig["catalyst_type"],
                "direction": isig["direction"].replace("bullish", "Long").replace("bearish", "Short"),
                "magnitude": str(isig["magnitude"]),
                "confidence": str(int(isig["confidence"] * 100)) + "%",
                "flag_level": isig["flag_level"],
                "timestamp": sim_ts(),
            })
            st.add_log(
                f"{src_label} SIGNAL: {isig['ticker']} {isig['direction']} | "
                f"{isig['flag_level']} flag | conf={int(isig['confidence']*100)}% "
                f"mag={isig['magnitude']}",
                "RED" if isig["flag_level"] == "RED" else "YELLOW",
            )
            st.add_log(f"  {isig['headline'][:120]}", "INFO")

            # Log extra insider detail
            if isig["source"] == "SEC_Form4":
                st.add_log(
                    f"  Form 4: {isig.get('insider_title', 'N/A')} | "
                    f"{isig.get('insider_shares', 0):,} shares | "
                    f"${isig.get('insider_value', 'N/A')} | "
                    f"{isig.get('insider_count', 1)} insider(s) | "
                    f"Filed: {isig.get('filing_date', 'N/A')} ({isig.get('filing_days_ago', '?')}d ago)",
                    "INFO",
                )
            elif isig["source"] == "STOCK_Act":
                st.add_log(
                    f"  STOCK Act: {isig.get('congress_type', '').title()} {isig.get('congress_member', 'N/A')} | "
                    f"Committee: {isig.get('committee', 'N/A')} | "
                    f"Oversight: {'YES' if isig.get('has_oversight') else 'NO'} | "
                    f"{isig.get('congress_shares', 0):,} shares (${isig.get('congress_value', 'N/A')})",
                    "INFO",
                )

            # If insider signal matches the technical signal ticker, boost it
            if isig["ticker"] == ticker and isig["direction"].replace("bullish", "Long").replace("bearish", "Short") == direction:
                old_conf = conf
                conf = min(0.95, conf + (CONGRESSIONAL_CONFIDENCE_BOOST if isig["source"] == "STOCK_Act" else INSIDER_CONFIDENCE_BOOST))
                mag = min(5.0, mag + 1.0)
                flag = "Red" if mag >= 3.0 and conf >= 0.6 else flag
                st.add_log(
                    f"  CONFIRMATION: {src_label} aligns with technical on {ticker} — "
                    f"conf boosted {int(old_conf*100)}% -> {int(conf*100)}%, flag={flag.upper()}",
                    "RED",
                )

        # -- maybe open a position (RED flags auto-execute, 15% of YELLOWs, insider signals boost) --
        should_enter = (flag == "Red") or (flag == "Yellow" and random.random() < 0.15)
        # Also enter on any RED insider/congressional signal for a ticker we don't hold
        for isig in insider_signals:
            if isig["flag_level"] == "RED" and not any(p["ticker"] == isig["ticker"] for p in positions):
                ticker = isig["ticker"]
                direction = isig["direction"].replace("bullish", "Long").replace("bearish", "Short")
                conf = isig["confidence"]
                mag = float(isig["magnitude"])
                flag = "Red"
                rsi = isig.get("rsi", 50.0)
                vol_ratio = isig.get("volume_ratio", 1.5)
                sector = isig["catalyst_type"]
                headline = isig["headline"]
                should_enter = True
                st.add_log(f"  Auto-executing {src_label} RED signal for {ticker}", "EXEC")
                break

        already_holding = any(p["ticker"] == ticker for p in positions)

        if should_enter and not already_holding and len(positions) < 5:
            price = base_prices.get(ticker, 100.0) * random.uniform(0.97, 1.03)
            max_spend = min(cash, equity * MAX_POSITION_PCT)
            qty = max(1, int(max_spend / price)) if price > 0 else 0
            fill_price = apply_slippage(price, is_buy=True)
            cost = round(fill_price * qty, 2)

            if cost < cash and qty > 0:
                cash -= cost

                # Set realistic stop/target based on direction and catalyst
                if direction == "Long":
                    stop_loss = round(fill_price * random.uniform(0.965, 0.98), 2)
                    target = round(fill_price * random.uniform(1.03, 1.08), 2)
                else:
                    stop_loss = round(fill_price * random.uniform(1.02, 1.035), 2)
                    target = round(fill_price * random.uniform(0.92, 0.97), 2)

                # Time decay limit based on catalyst type
                time_limits = {
                    "geopolitical": 60, "earnings": 180, "contract_win": 240,
                    "regulatory": 360, "supply_chain": 180, "macro": 120, "technical": 90,
                    "insider_buy": 240, "insider_sell": 180,
                    "congressional_buy": 300, "congressional_sell": 240,
                    "confirmed_insider_buy": 360, "confirmed_congressional_buy": 420,
                }
                max_hold_mins = time_limits.get(sector, 120)

                pos = {
                    "ticker": ticker,
                    "direction": direction,
                    "qty": qty,
                    "entry_price": fill_price,
                    "current_price": fill_price,
                    "unrealized_pnl": 0.0,
                    "unrealized_pnl_pct": 0.0,
                    "stop_loss": stop_loss,
                    "target": target,
                    "time_held": "0m",
                    "_entry_time": sim_ts(),
                    "_entry_sim_time": sim_time,
                    "_step_opened": step,
                    "_catalyst": headline,
                    "_catalyst_type": sector,
                    "_signal_confidence": conf,
                    "_signal_magnitude": mag,
                    "_rsi_at_entry": rsi,
                    "_vol_ratio_at_entry": vol_ratio,
                    "_max_hold_mins": max_hold_mins,
                    "_trailing_pct": 0.015,
                }
                positions.append(pos)
                high_water_marks[ticker] = fill_price

                slippage = round(fill_price - price, 4)
                st.add_log(
                    f"ENTRY {direction.upper()} {qty}x {ticker} @ ${fill_price:.2f} "
                    f"(slippage: ${slippage:.4f}, cost: ${cost:.2f})",
                    "EXEC",
                )
                st.add_log(
                    f"  Position sizing: ${cost:.2f} / ${equity:.2f} equity = "
                    f"{cost/equity*100:.1f}% | Cash remaining: ${cash:.2f}",
                    "INFO",
                )
                st.add_log(
                    f"  Exit plan: stop=${stop_loss:.2f} target=${target:.2f} "
                    f"trailing=1.5% max_hold={max_hold_mins}min ({sector})",
                    "INFO",
                )
            elif qty <= 0:
                st.add_log(f"Skip {ticker}: cannot afford at ${price:.2f} (cash=${cash:.2f})", "WARN")
            else:
                st.add_log(f"Skip {ticker}: cost ${cost:.2f} > cash ${cash:.2f}", "WARN")
        elif already_holding:
            st.add_log(f"Skip {ticker}: already holding position", "WARN")

        # -- update existing positions & check exits --
        closed_indices = []
        for i, p in enumerate(positions):
            # Price drift (smaller per-step for more realism)
            drift = random.uniform(-0.008, 0.012)
            p["current_price"] = round(p["current_price"] * (1 + drift), 2)

            # Update high water mark
            tk = p["ticker"]
            if p["direction"] == "Long":
                if p["current_price"] > high_water_marks.get(tk, p["entry_price"]):
                    high_water_marks[tk] = p["current_price"]
            else:
                if p["current_price"] < high_water_marks.get(tk, p["entry_price"]):
                    high_water_marks[tk] = p["current_price"]

            # Compute P&L
            raw_pnl = (p["current_price"] - p["entry_price"]) * p["qty"]
            if p["direction"] == "Short":
                raw_pnl = -raw_pnl
            p["unrealized_pnl"] = round(raw_pnl, 2)
            p["unrealized_pnl_pct"] = round(
                raw_pnl / (p["entry_price"] * p["qty"]) * 100, 2
            )

            # Simulated hold time
            hold_delta = sim_time - p["_entry_sim_time"]
            hold_mins = int(hold_delta.total_seconds() / 60)
            if hold_mins < 60:
                p["time_held"] = f"{hold_mins}m"
            else:
                p["time_held"] = f"{hold_mins // 60}h {hold_mins % 60}m"

            # -- CHECK EXIT TRIGGERS (only after minimum hold) --
            steps_held = step - p["_step_opened"]
            if steps_held < DEMO_MIN_HOLD_STEPS:
                continue  # enforce minimum hold

            exit_trigger = None
            exit_detail = ""

            # 1. Take-profit: price hit target
            if p["direction"] == "Long" and p["current_price"] >= p["target"]:
                exit_trigger = "Target hit"
                exit_detail = f"Price ${p['current_price']:.2f} >= target ${p['target']:.2f}"
            elif p["direction"] == "Short" and p["current_price"] <= p["target"]:
                exit_trigger = "Target hit"
                exit_detail = f"Price ${p['current_price']:.2f} <= target ${p['target']:.2f}"

            # 2. Hard stop-loss
            if not exit_trigger:
                if p["direction"] == "Long" and p["current_price"] <= p["stop_loss"]:
                    exit_trigger = "Stop loss"
                    exit_detail = f"Price ${p['current_price']:.2f} <= stop ${p['stop_loss']:.2f}"
                elif p["direction"] == "Short" and p["current_price"] >= p["stop_loss"]:
                    exit_trigger = "Stop loss"
                    exit_detail = f"Price ${p['current_price']:.2f} >= stop ${p['stop_loss']:.2f}"

            # 3. Trailing stop
            if not exit_trigger:
                hwm = high_water_marks.get(tk, p["entry_price"])
                trailing_pct = p["_trailing_pct"]
                if p["direction"] == "Long":
                    trailing_stop = hwm * (1 - trailing_pct)
                    if p["current_price"] <= trailing_stop and hwm > p["entry_price"]:
                        exit_trigger = "Trailing stop"
                        exit_detail = (
                            f"Price ${p['current_price']:.2f} fell below trailing "
                            f"${trailing_stop:.2f} (HWM ${hwm:.2f}, -{trailing_pct*100:.1f}%)"
                        )

            # 4. Time decay
            if not exit_trigger and hold_mins >= p["_max_hold_mins"]:
                exit_trigger = "Time decay"
                exit_detail = f"Held {hold_mins}m >= max {p['_max_hold_mins']}m for {p['_catalyst_type']}"

            # 5. Volume divergence (simulated — random chance after long hold)
            if not exit_trigger and steps_held > DEMO_MIN_HOLD_STEPS * 2 and random.random() < 0.08:
                exit_trigger = "Volume divergence"
                exit_detail = f"Price rising but volume declining for 3 consecutive checks"

            if exit_trigger:
                closed_indices.append(i)
                exit_price = apply_slippage(p["current_price"], is_buy=False)
                fees = compute_fees(exit_price, p["qty"])
                total_fees_paid += fees

                gross = (exit_price - p["entry_price"]) * p["qty"]
                if p["direction"] == "Short":
                    gross = -gross
                net = round(gross - fees, 2)
                gross = round(gross, 2)
                proceeds = round(exit_price * p["qty"], 2)
                cash += proceeds - fees

                total_trades += 1
                if net > 0:
                    winning_trades += 1

                trade = {
                    "entry_time": p["_entry_time"],
                    "exit_time": sim_ts(),
                    "ticker": p["ticker"],
                    "direction": p["direction"],
                    "entry_price": p["entry_price"],
                    "exit_price": exit_price,
                    "qty": p["qty"],
                    "pnl_gross": gross,
                    "gross_pnl": gross,
                    "fees": fees,
                    "pnl_net": net,
                    "net_pnl": net,
                    "exit_trigger": exit_trigger,
                    "hold_duration": p["time_held"],
                    "hold_duration_sec": hold_mins * 60,
                }
                trades.append(trade)
                st.add_trade(trade)

                # Clean up tracking
                high_water_marks.pop(tk, None)

                color = "PROFIT" if net >= 0 else "LOSS"
                st.add_log(
                    f"EXIT {p['direction'].upper()} {p['qty']}x {p['ticker']} @ ${exit_price:.2f} "
                    f"| Trigger: {exit_trigger}",
                    color,
                )
                st.add_log(
                    f"  P&L: gross=${gross:+.2f} fees=${fees:.4f} net=${net:+.2f} "
                    f"({net/(p['entry_price']*p['qty'])*100:+.2f}%) | Held: {p['time_held']}",
                    color,
                )
                st.add_log(f"  Reason: {exit_detail}", "INFO")

                # Detailed trade log to file for optimization
                st.log_trade_to_file({
                    **trade,
                    "catalyst": p["_catalyst"],
                    "catalyst_type": p["_catalyst_type"],
                    "signal_confidence": p["_signal_confidence"],
                    "signal_magnitude": p["_signal_magnitude"],
                    "rsi_at_entry": p["_rsi_at_entry"],
                    "vol_ratio_at_entry": p["_vol_ratio_at_entry"],
                    "stop_loss": p["stop_loss"],
                    "target": p["target"],
                    "max_hold_mins": p["_max_hold_mins"],
                    "high_water_mark": high_water_marks.get(tk, p["entry_price"]),
                    "exit_detail": exit_detail,
                    "steps_held": steps_held,
                    "total_trades_so_far": total_trades,
                    "win_rate": round(winning_trades / total_trades * 100, 1) if total_trades else 0,
                    "equity_at_exit": round(cash + sum(
                        pp["entry_price"] * pp["qty"] + pp["unrealized_pnl"]
                        for j, pp in enumerate(positions) if j not in closed_indices
                    ), 2),
                })

        # Remove closed positions (reverse order to preserve indices)
        for i in sorted(closed_indices, reverse=True):
            positions.pop(i)

        st.update_positions(positions)

        # -- recompute equity --
        pos_value = sum(
            pos["entry_price"] * pos["qty"] + pos["unrealized_pnl"]
            for pos in positions
        )
        equity = round(cash + pos_value, 2)
        total_pnl = round(equity - starting_capital, 2)

        st.add_equity_point(sim_ts(), round(equity, 2))

        # Periodic summary log
        if step % 10 == 0:
            win_rate = round(winning_trades / total_trades * 100, 1) if total_trades else 0
            st.add_log(
                f"SUMMARY: Equity=${equity:.2f} P&L=${total_pnl:+.2f} ({total_pnl/starting_capital*100:+.1f}%) "
                f"| Trades={total_trades} Win={win_rate}% | Fees=${total_fees_paid:.2f} "
                f"| Open={len(positions)} Cash=${cash:.2f}",
                "INFO",
            )

        unsettled = round(
            sum(t["entry_price"] * t["qty"] for t in trades[-3:]) * 0.1, 2
        ) if trades else 0.0

        st.update_account(
            current_equity=equity,
            total_pnl=total_pnl,
            total_pnl_pct=round(total_pnl / starting_capital * 100, 2),
            available_cash=round(cash, 2),
            unsettled_funds=unsettled,
            day_trades_remaining=999,  # unlimited in demo
            market_open=True,
            market_status="Open",
            next_event=f"Closes in {max(0, 16 - sim_time.hour)}h {60 - sim_time.minute}m",
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
