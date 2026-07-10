/* jsbsim-mcp Dashboard
 * - Boots, fetches /api/aircraft to populate dropdown
 * - Create session REST -> POST /api/sessions
 * - Step / Trim buttons
 * - WebSocket telemetry at /ws/<sid> at ~20Hz
 * - Renders PFD (SVG), 3D attitude (Three.js), stats grid, Plotly history
 * - Tiny MCP JSON-RPC console for hand-debugging
 *
 * Three.js is loaded as an ES module. We try jsdelivr CDN first, fall
 * back to the local vendor file at /static/three.module.min.js (bundled
 * with the deployment so HF Spaces works without outbound requests).
 */
(() => {
  const api = {
    aircraft:  '/api/aircraft',
    create:    '/api/sessions',
    step:      (sid) => `/api/sessions/${sid}/step`,
    trim:      (sid) => `/api/sessions/${sid}/trim`,
    close:     (sid) => `/api/sessions/${sid}`,
    telemetry: (sid) => `/api/sessions/${sid}/telemetry`,
  };

  const ui = {
    sel:        document.getElementById('aircraftSel'),
    icAlt:      document.getElementById('icAlt'),
    icAirspeed: document.getElementById('icAirspeed'),
    icHeading:  document.getElementById('icHeading'),
    stepSeconds:document.getElementById('stepSeconds'),
    btnCreate:  document.getElementById('btnCreate'),
    btnStep:    document.getElementById('btnStep'),
    btnTrim:    document.getElementById('btnTrim'),
    btnClose:   document.getElementById('btnClose'),
    sessionId:  document.getElementById('sessionIdDisplay'),
    connState:  document.getElementById('connState'),
    pfd:        document.getElementById('pfd'),
    canvas:     document.getElementById('attitude3d'),
    stats:      document.getElementById('stats'),
    chart:      document.getElementById('chart'),
    log:        document.getElementById('log'),
    mcpIn:      document.getElementById('mcpIn'),
    mcpSend:    document.getElementById('mcpSend'),
    mcpOut:     document.getElementById('mcpOut'),
  };

  const state = {
    sid: null,
    ws: null,
    history: { t: [], alt: [], aspd: [], mach: [], aoa: [], thrust: [], g: [] },
    chartWindowSec: 60,
    lastSimT: -1,
  };

  const log = (msg, level = 'info') => {
    const stamp = new Date().toISOString().slice(11, 19);
    const text = `[${stamp}] ${msg}`;
    ui.log.textContent += (ui.log.textContent ? '\n' : '') + text;
    ui.log.scrollTop = ui.log.scrollHeight;
    if (level === 'err') console.error(text);
  };

  const setConn = (s) => {
    ui.connState.textContent = s;
    ui.connState.className = 'pill ' + (
      s === 'live'   ? 'pill--online' :
      s === 'error'  ? 'pill--err' :
      'pill--offline'
    );
  };

  // ----------------------------------------------------------------------
  // boot
  // ----------------------------------------------------------------------
  async function boot() {
    try {
      const r = await fetch(api.aircraft);
      const j = await r.json();
      ui.sel.innerHTML = '';
      for (const a of j.aircraft) {
        const o = document.createElement('option');
        o.value = a; o.textContent = a;
        ui.sel.appendChild(o);
      }
      if (j.aircraft.includes('c172x')) ui.sel.value = 'c172x';
      log(`loaded ${j.aircraft.length} aircraft`);
    } catch (e) {
      log('failed to load aircraft: ' + e.message, 'err');
    }

    Plotly.newPlot(ui.chart, [
      { x: [], y: [], mode: 'lines', name: 'alt ft',     yaxis: 'y' },
      { x: [], y: [], mode: 'lines', name: 'kt',         yaxis: 'y2' },
      { x: [], y: [], mode: 'lines', name: 'alpha°',     yaxis: 'y3' },
      { x: [], y: [], mode: 'lines', name: 'thrust lbs', yaxis: 'y'  },
    ], {
      paper_bgcolor: 'transparent',
      plot_bgcolor:  '#0b0e14',
      font: { color: '#d8dee9' },
      margin: { l: 30, r: 30, t: 8, b: 24 },
      legend: { orientation: 'h', font: { size: 10 } },
      yaxis:  { domain: [0.0, 0.5], gridcolor: '#1d2733' },
      yaxis2: { domain: [0.5, 1.0], overlaying: 'y', side: 'right', gridcolor: '#1d2733' },
      yaxis3: { domain: [0.0, 0.5], overlaying: 'y', side: 'right' },
    }, { responsive: true, displaylogo: false });

    bootThree().catch(err => log('three.js failed: ' + err.message + ' — falling back to stub', 'warn'));
    bind();
    setConn('ready');
  }

  // ----------------------------------------------------------------------
  // session lifecycle
  // ----------------------------------------------------------------------
  async function createSession() {
    const ac = ui.sel.value;
    const ic = {
      altitude_ft:  parseFloat(ui.icAlt.value)  || 3000,
      airspeed_fps: (parseFloat(ui.icAirspeed.value) || 95) * 1.6878,
      heading_deg:  parseFloat(ui.icHeading.value)  || 0,
    };
    try {
      const r = await fetch(api.create, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ aircraft: ac, initial_conditions: ic }),
      });
      if (!r.ok) throw new Error(await r.text());
      const j = await r.json();
      state.sid = j.session_id;
      ui.sessionId.textContent = state.sid;
      ui.btnStep.disabled = false;
      ui.btnTrim.disabled = false;
      ui.btnClose.disabled = false;
      log(`created session ${state.sid} (${j.aircraft}, dt=${j.dt.toFixed(4)}s)`);
      openWs();
    } catch (e) {
      log('create failed: ' + e.message, 'err');
    }
  }

  async function stepSim() {
    if (!state.sid) return;
    const sec = parseFloat(ui.stepSeconds.value) || 0.05;
    try {
      const r = await fetch(api.step(state.sid), {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ seconds: sec }),
      });
      if (!r.ok) throw new Error(await r.text());
      const j = await r.json();
      log(`stepped ${j.frames} frames → sim ${j.sim_time.toFixed(2)}s`);
    } catch (e) {
      log('step failed: ' + e.message, 'err');
    }
  }

  async function trimSim() {
    if (!state.sid) return;
    try {
      const r = await fetch(api.trim(state.sid), {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ mode: 'longitudinal' }),
      });
      if (!r.ok) throw new Error(await r.text());
      const j = await r.json();
      log('trim: ' + JSON.stringify(j));
    } catch (e) {
      log('trim failed: ' + e.message, 'err');
    }
  }

  async function closeSession() {
    if (!state.sid) return;
    try {
      if (state.ws) state.ws.close();
      await fetch(api.close(state.sid), { method: 'DELETE' });
      log('closed session ' + state.sid);
    } catch (e) {
      log('close failed: ' + e.message, 'err');
    } finally {
      state.sid = null;
      ui.sessionId.textContent = 'no session';
      ui.btnStep.disabled = true;
      ui.btnTrim.disabled = true;
      ui.btnClose.disabled = true;
      setConn('ready');
    }
  }

  // ----------------------------------------------------------------------
  // WebSocket telemetry
  // ----------------------------------------------------------------------
  function openWs() {
    if (state.ws) try { state.ws.close(); } catch {}
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    const ws = new WebSocket(`${proto}://${location.host}/ws/${state.sid}`);
    state.ws = ws;
    ws.onopen  = () => { setConn('live');   log('ws open');  };
    ws.onerror = () => { setConn('error');  log('ws error', 'err'); };
    ws.onclose = () => { setConn('closed'); log('ws closed'); };
    ws.onmessage = (ev) => {
      try {
        const m = JSON.parse(ev.data);
        if (m.type === 'telemetry') apply(m.frame);
      } catch (e) {
        log('bad frame: ' + e.message, 'err');
      }
    };
  }

  // ----------------------------------------------------------------------
  // telemetry apply
  // ----------------------------------------------------------------------
  function apply(frame) {
    if (!frame) return;
    state.lastSimT = frame.t;
    drawPfd(frame);
    drawAttitude3d(frame);
    drawStats(frame);
    pushHistory(frame);
  }

  function pushHistory(frame) {
    const h = state.history;
    h.t.push(frame.t);
    h.alt.push(frame.alt_ft);
    h.aspd.push(frame.airspeed_kt);
    h.mach.push(frame.mach);
    h.aoa.push(frame.alpha_deg);
    h.thrust.push(frame.thrust_lbs);
    h.g.push(frame.nz_g);
    if (h.t.length > 1200) {
      for (const k of Object.keys(h)) h[k] = h[k].slice(-1200);
    }
    const cut = frame.t - state.chartWindowSec;
    const idx = h.t.findIndex(v => v >= cut);
    const x  = idx > 0 ? h.t.slice(idx)    : h.t;
    const a  = idx > 0 ? h.alt.slice(idx)   : h.alt;
    const sp = idx > 0 ? h.aspd.slice(idx)  : h.aspd;
    const ao = idx > 0 ? h.aoa.slice(idx)   : h.aoa;
    const th = idx > 0 ? h.thrust.slice(idx): h.thrust;
    Plotly.react(ui.chart, [
      { x, y: a,  mode: 'lines', name: 'alt ft',     line: { color: '#5ec4ff' }, yaxis: 'y' },
      { x, y: sp, mode: 'lines', name: 'kt',         line: { color: '#86dc7d' }, yaxis: 'y2' },
      { x, y: ao, mode: 'lines', name: 'alpha°',     line: { color: '#ffc56b' }, yaxis: 'y3' },
      { x, y: th, mode: 'lines', name: 'thrust lbs', line: { color: '#ff8aa3' }, yaxis: 'y'  },
    ], {}, { responsive: true, displaylogo: false });
  }

  // ----------------------------------------------------------------------
  // stats grid
  // ----------------------------------------------------------------------
  function drawStats(f) {
    const rows = [
      ['t (sim)',     f.t.toFixed(2) + ' s'],
      ['altitude',    f.alt_ft.toFixed(0) + ' ft'],
      ['agl',         (f.altitude_agl_ft == null ? '–' : f.altitude_agl_ft.toFixed(0)) + ' ft'],
      ['heading',     f.heading_deg.toFixed(1) + '°'],
      ['pitch',       f.pitch_deg.toFixed(1) + '°'],
      ['roll',        f.roll_deg.toFixed(1) + '°'],
      ['airspeed',    f.airspeed_kt.toFixed(1) + ' kt'],
      ['mach',        f.mach.toFixed(3)],
      ['alpha',       f.alpha_deg.toFixed(2) + '°'],
      ['beta',        f.beta_deg.toFixed(2) + '°'],
      ['thrust',      f.thrust_lbs.toFixed(0) + ' lbs'],
      ['rpm',         f.rpm.toFixed(0)],
      ['fuel',        f.fuel_remaining_lbs.toFixed(1) + ' lbs'],
      ['G',           f.nz_g.toFixed(2) + ' g'],
      ['on ground',   (f.wow_nose || f.wow_main_l || f.wow_main_r) ? 'YES' : 'NO'],
      ['engine',      f.engine_running ? 'running' : 'stopped'],
    ];
    ui.stats.innerHTML = rows.map(([k, v]) =>
      `<div><div class="k">${k}</div><div class="v">${v}</div></div>`
    ).join('');
  }

  // ----------------------------------------------------------------------
  // PFD SVG (artificial horizon + numeric alt/asd/hdg tapes)
  // ----------------------------------------------------------------------
  function drawPfd(f) {
    const svgNS = 'http://www.w3.org/2000/svg';
    const svg = ui.pfd;
    if (!svg._built) {
      svg.innerHTML = `
        <defs>
          <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stop-color="#0a4ea0"/>
            <stop offset="1" stop-color="#3aa8ff"/>
          </linearGradient>
          <linearGradient id="gnd" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stop-color="#7a4a18"/>
            <stop offset="1" stop-color="#3a2106"/>
          </linearGradient>
        </defs>
        <g id="sky"></g>
        <g id="gnd"></g>
        <g id="bugs">
          <polygon points="530,178 540,172 540,184 530,182" fill="#ffd84a"/>
          <polygon points="70,178 60,172 60,184 70,182" fill="#ffd84a"/>
        </g>
        <g id="overlay">
          <line x1="180" y1="180" x2="420" y2="180" stroke="#fff" stroke-width="2"/>
          <line x1="300" y1="120" x2="300" y2="240" stroke="#fff" stroke-width="2"/>
          <circle cx="300" cy="180" r="6" fill="#000" stroke="#fff" stroke-width="2"/>
          <text x="20"  y="22" fill="#86dc7d" font-family="ui-monospace,Menlo" font-size="14">SPEED</text>
          <text x="540" y="22" fill="#86dc7d" font-family="ui-monospace,Menlo" font-size="14">ALT</text>
        </g>
        <g id="num"></g>
      `;
      svg._sky = svg.querySelector('#sky');
      svg._gnd = svg.querySelector('#gnd');
      svg._num = svg.querySelector('#num');
      svg._built = true;
    }

    const pitch = f.pitch_deg;
    const roll  = f.roll_deg;
    const cx = 300, cy = 180;
    const pitchPx = pitch * 6;

    // Apply roll by rotating the horizon rect about its center
    const horizonY = cy + pitchPx;
    const skyRect = `M0,0 L600,0 L600,${horizonY} L0,${horizonY} Z`;
    svg._sky.setAttribute('d', skyRect);
    svg._sky.setAttribute('fill', 'url(#sky)');
    svg._gnd.setAttribute('d', `M0,${horizonY} L600,${horizonY} L600,360 L0,360 Z`);
    svg._gnd.setAttribute('fill', 'url(#gnd)');

    // "Skyline" tick marks: rotate about center by roll degrees.
    let tickGroup = svg.querySelector('#pitchTicks');
    if (!tickGroup) {
      tickGroup = document.createElementNS(svgNS, 'g');
      tickGroup.id = 'pitchTicks';
      svg.appendChild(tickGroup);
    }
    let inner = '';
    for (let p = -10; p <= 20; p += 5) {
      if (p === 0) continue;
      inner += `<line x1="270" y1="${180 + p * 6}" x2="330" y2="${180 + p * 6}" stroke="#fff" stroke-width="1"/>`;
      inner += `<text x="335" y="${184 + p * 6}" fill="#fff" font-family="ui-monospace,Menlo" font-size="10">${p}</text>`;
    }
    tickGroup.innerHTML = inner;
    tickGroup.setAttribute('transform', `rotate(${-roll}, ${cx}, ${cy})`);

    svg._num.innerHTML = `
      <text x="300" y="100" text-anchor="middle" fill="#86dc7d" font-family="ui-monospace,Menlo" font-size="22" font-weight="bold">${Math.round(f.alt_ft)}</text>
      <text x="300" y="118" text-anchor="middle" fill="#86dc7d" font-family="ui-monospace,Menlo" font-size="10">FT</text>
      <text x="300" y="290" text-anchor="middle" fill="#ffc56b" font-family="ui-monospace,Menlo" font-size="14">${Math.round(f.heading_deg)}°</text>
      <text x="300" y="306" text-anchor="middle" fill="#86dc7d" font-family="ui-monospace,Menlo" font-size="18" font-weight="bold">${Math.round(f.airspeed_kt)}</text>
      <text x="300" y="324" text-anchor="middle" fill="#86dc7d" font-family="ui-monospace,Menlo" font-size="10">KT</text>
      <text x="490" y="180" fill="#ffc56b" font-family="ui-monospace,Menlo" font-size="10">PITCH ${f.pitch_deg.toFixed(1)}°</text>
      <text x="490" y="194" fill="#5ec4ff" font-family="ui-monospace,Menlo" font-size="10">ROLL  ${f.roll_deg.toFixed(1)}°</text>
      <text x="490" y="208" fill="#ff8aa3" font-family="ui-monospace,Menlo" font-size="10">G     ${f.nz_g.toFixed(2)}</text>
    `;
  }

  // ----------------------------------------------------------------------
  // 3D attitude (Three.js, ES module)
  // ----------------------------------------------------------------------
  let THREE_M, scene, camera, renderer, planeMesh, horizon;

  async function bootThree() {
    // Try multiple CDN origins, fall back to local vendored copy.
    const sources = [
      'https://cdn.jsdelivr.net/npm/three@0.169.0/build/three.module.min.js',
      'https://unpkg.com/three@0.169.0/build/three.module.min.js',
      '/static/three.module.min.js',
    ];
    for (const url of sources) {
      try {
        THREE_M = await import(/* @vite-ignore */ url);
        if (THREE_M) break;
      } catch (e) { /* try next */ }
    }
    if (!THREE_M) throw new Error('no source worked');

    const T = THREE_M;
    const c = ui.canvas;
    scene = new T.Scene();
    camera = new T.PerspectiveCamera(50, c.width / c.height, 0.1, 100);
    camera.position.set(0, 0, 5);

    renderer = new T.WebGLRenderer({ canvas: c, antialias: true });
    renderer.setPixelRatio(1);
    renderer.setSize(c.width, c.height);

    horizon = new T.Mesh(
      new T.PlaneGeometry(8, 8, 32, 32),
      new T.ShaderMaterial({
        uniforms: {
          skyColor:    { value: new T.Color(0x3aa8ff) },
          groundColor: { value: new T.Color(0x3a2106) },
        },
        vertexShader: `varying vec2 vUv; void main(){ vUv=uv; gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0); }`,
        fragmentShader: `varying vec2 vUv; uniform vec3 skyColor; uniform vec3 groundColor; void main(){ vec3 c=mix(groundColor,skyColor,step(0.5,vUv.y)); gl_FragColor=vec4(c,1.0); }`,
        side: T.DoubleSide,
      })
    );
    horizon.rotation.x = -Math.PI / 2;
    horizon.position.y = -0.5;
    scene.add(horizon);

    const plane = new T.Group();
    const f = new T.Mesh(
      new T.BoxGeometry(1.0, 0.05, 0.15),
      new T.MeshBasicMaterial({ color: 0xffffff }),
    );
    f.position.y = 0.05;
    plane.add(f);
    const tail = new T.Mesh(
      new T.BoxGeometry(0.2, 0.05, 0.05),
      new T.MeshBasicMaterial({ color: 0xffffff }),
    );
    tail.position.z = 0.18;
    plane.add(tail);
    planeMesh = plane;
    scene.add(plane);

    const grid = new T.GridHelper(20, 20, 0x556677, 0x334455);
    grid.rotation.x = Math.PI / 2;
    scene.add(grid);

    animate3d();
    log('three.js loaded', 'info');
  }

  function drawAttitude3d(f) {
    if (!planeMesh || !renderer) return;
    planeMesh.rotation.z = f.roll_deg * Math.PI / 180;
    planeMesh.rotation.x = f.pitch_deg * Math.PI / 180;
    horizon.rotation.z   = -f.roll_deg * Math.PI / 180;
    horizon.position.y   = -0.5 - (f.pitch_deg / 30.0);
    renderer.render(scene, camera);
  }

  function animate3d() {
    requestAnimationFrame(animate3d);
    if (renderer && scene && camera) renderer.render(scene, camera);
  }

  // ----------------------------------------------------------------------
  // MCP JSON-RPC hand-console
  // ----------------------------------------------------------------------
  async function sendMcp() {
    const body = ui.mcpIn.value.trim();
    if (!body) return;
    try {
      const r = await fetch('/mcp', {
        method: 'POST',
        headers: {
          'content-type': 'application/json',
          'accept': 'application/json, text/event-stream',
        },
        body,
      });
      const text = await r.text();
      ui.mcpOut.textContent += '\n→ ' + body + '\n← ' + text + '\n';
      ui.mcpOut.scrollTop = ui.mcpOut.scrollHeight;
    } catch (e) {
      ui.mcpOut.textContent += '\nerr: ' + e.message + '\n';
    }
  }

  // ----------------------------------------------------------------------
  // bindings
  // ----------------------------------------------------------------------
  function bind() {
    ui.btnCreate.addEventListener('click', createSession);
    ui.btnStep.addEventListener('click', stepSim);
    ui.btnTrim.addEventListener('click', trimSim);
    ui.btnClose.addEventListener('click', closeSession);
    ui.mcpSend.addEventListener('click', sendMcp);
  }

  boot();
})();
