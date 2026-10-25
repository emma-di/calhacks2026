const NS = 'http://www.w3.org/2000/svg';
const css = {
  power: 'var(--power)', ground: 'var(--ground)', sck: 'var(--sck)',
  ws: 'var(--ws)', sd: 'var(--sd)', scl: 'var(--scl)', sda: 'var(--sda)'
};

const usedPins = {
  1: { label: '3V3 · MICS', signal: 'power' },
  3: { label: 'GPIO2 · SDA', signal: 'sda' },
  5: { label: 'GPIO3 · SCL', signal: 'scl' },
  6: { label: 'GND · MICS', signal: 'ground' },
  12: { label: 'GPIO18 · PCM_CLK', signal: 'sck' },
  14: { label: 'GND · OLED', signal: 'ground' },
  17: { label: '3V3 · OLED', signal: 'power' },
  35: { label: 'GPIO19 · PCM_FS', signal: 'ws' },
  38: { label: 'GPIO20 · PCM_DIN', signal: 'sd' }
};

const connections = [
  { id: 'mic-power', group: ['left', 'right'], signal: 'power', from: 1, label: 'Microphone VDD', detail: 'Both VDD pins → physical pin 1 · 3.3 V', targets: ['left-vdd', 'right-vdd'] },
  { id: 'mic-ground', group: ['left', 'right'], signal: 'ground', from: 6, label: 'Microphone ground', detail: 'Both GND pins → physical pin 6 · ground', targets: ['left-gnd', 'right-gnd'] },
  { id: 'mic-sck', group: ['left', 'right'], signal: 'sck', from: 12, label: 'I²S bit clock', detail: 'Both SCK pins → physical pin 12 · GPIO18/PCM_CLK', targets: ['left-sck', 'right-sck'] },
  { id: 'mic-ws', group: ['left', 'right'], signal: 'ws', from: 35, label: 'I²S word select', detail: 'Both WS pins → physical pin 35 · GPIO19/PCM_FS', targets: ['left-ws', 'right-ws'] },
  { id: 'mic-sd', group: ['left', 'right'], signal: 'sd', from: 38, label: 'Shared audio data', detail: 'Both SD pins → physical pin 38 · GPIO20/PCM_DIN', targets: ['left-sd', 'right-sd'] },
  { id: 'oled-power', group: ['oled'], signal: 'power', from: 17, label: 'OLED VCC', detail: 'VCC → physical pin 17 · 3.3 V', target: 'oled-vcc' },
  { id: 'oled-ground', group: ['oled'], signal: 'ground', from: 14, label: 'OLED ground', detail: 'GND → physical pin 14 · ground', target: 'oled-gnd' },
  { id: 'oled-scl', group: ['oled'], signal: 'scl', from: 5, label: 'OLED clock', detail: 'SCL → physical pin 5 · GPIO3/SCL', target: 'oled-scl' },
  { id: 'oled-sda', group: ['oled'], signal: 'sda', from: 3, label: 'OLED data', detail: 'SDA → physical pin 3 · GPIO2/SDA', target: 'oled-sda' },
  { id: 'pi-power', group: ['ports'], signal: 'power', label: 'Pi power input', detail: 'Pocket power bank → Pi PWR IN Micro-USB port', path: 'M368 739 H427 V643 H500' }
];

const viewCopy = {
  all: ['COMPLETE SYSTEM', 'Two-microphone wiring', 'Both microphones share SCK, WS and SD. Left L/R is tied to GND; right L/R is tied to 3.3 V, so each microphone drives a different stereo slot. The OLED uses separate I²C pins.'],
  left: ['LEFT CHANNEL', 'Left I²S microphone', 'VDD → pin 1; GND → pin 6; SCK → pin 12/GPIO18; WS → pin 35/GPIO19; SD → pin 38/GPIO20. Tie this microphone’s L/R pin to GND.'],
  right: ['RIGHT CHANNEL', 'Right I²S microphone', 'VDD → pin 1; GND → pin 6; SCK → pin 12/GPIO18; WS → pin 35/GPIO19; SD → pin 38/GPIO20. Tie this microphone’s L/R pin to 3.3 V.'],
  oled: ['OLED DISPLAY', 'Four-wire I²C', 'The display uses physical pins 17, 14, 5 and 3 for VCC, GND, SCL and SDA respectively.'],
  ports: ['POWER + PORTS', 'Correct physical orientation', 'microSD is at the top, CSI at the bottom, GPIO on the right, and HDMI/USB/PWR IN run down the left edge.'],
  clearance: ['CAD KEEP-OUTS', 'Leave room for real plugs', 'Keep 15 mm at the microSD edge, 12–15 mm above the GPIO header for wire bends, and about 25 mm laterally at both Micro-USB connectors.'],
  solder: ['UNDERSIDE / SOLDER SIDE', 'OLED header joints', 'Hold the Pi with the microSD end at the top. From the underside the board is mirrored: GPIO is on the left, and square pad 1 is the upper-right pad of the header. Highlighted pads are OLED connections.']
};

const pinPosition = {};
const modulePosition = {};

function svg(tag, attrs = {}, text = '') {
  const element = document.createElementNS(NS, tag);
  Object.entries(attrs).forEach(([key, value]) => element.setAttribute(key, value));
  if (text) element.textContent = text;
  return element;
}

const header = document.querySelector('#gpioHeader');
header.append(svg('rect', { class: 'header-bed', x: 792, y: 137, width: 112, height: 590, rx: 19 }));
for (let row = 0; row < 20; row += 1) {
  for (let col = 0; col < 2; col += 1) {
    const number = row * 2 + col + 1;
    const x = col ? 873 : 823;
    const y = 162 + row * 28.2;
    const meta = usedPins[number];
    pinPosition[number] = [x, y];
    const group = svg('g', {
      class: `gpio-pin${meta ? ' used' : ''}`, 'data-pin': number,
      style: `--signal:${meta ? css[meta.signal] : 'var(--dim)'}`,
      tabindex: meta ? '0' : '-1', role: meta ? 'button' : 'presentation'
    });
    group.append(svg('circle', { cx: x, cy: y, r: 8 }));
    group.append(svg('text', { class: 'pin-number', x: col ? x + 16 : x - 16, y: y + 3, 'text-anchor': col ? 'start' : 'end' }, String(number)));
    if (meta) group.append(svg('text', { class: 'pin-label', x: x - 44, y: y + 3, 'text-anchor': 'end' }, meta.label));
    header.append(group);
  }
}

function buildMic(groupSelector, side, centerY) {
  const group = document.querySelector(groupSelector);
  const pins = [
    ['gnd', 'GND', 'ground', centerY - 45],
    ['vdd', 'VDD', 'power', centerY - 23],
    ['sd', 'SD', 'sd', centerY - 1],
    ['sck', 'SCK', 'sck', centerY + 21],
    ['ws', 'WS', 'ws', centerY + 43]
  ];
  pins.forEach(([key, label, signal, y]) => {
    const id = `${side}-${key}`;
    const x = 1100;
    modulePosition[id] = [x, y];
    const pin = svg('g', { class: 'module-pin', 'data-terminal': id, 'data-signal': signal, style: `--signal:${css[signal]}`, tabindex: '0', role: 'button' });
    pin.append(svg('circle', { cx: x, cy: y, r: 8 }));
    pin.append(svg('text', { x: x - 13, y: y + 4, 'text-anchor': 'end' }, label));
    group.append(pin);
  });
  const lrSignal = side === 'left' ? 'ground' : 'power';
  const lr = svg('g', { class: 'module-pin', 'data-signal': lrSignal, style: `--signal:${css[lrSignal]}` });
  lr.append(svg('circle', { cx: 1235, cy: centerY - 47, r: 8 }));
  lr.append(svg('text', { x: 1248, y: centerY - 43 }, 'L/R'));
  group.append(lr);
}
buildMic('#leftMicPins', 'left', 443);
buildMic('#rightMicPins', 'right', 700);

const oledPins = document.querySelector('#oledPins');
[
  ['gnd', 'GND', 'ground'], ['vcc', 'VCC', 'power'],
  ['scl', 'SCL', 'scl'], ['sda', 'SDA', 'sda']
].forEach(([key, label, signal], index) => {
  const x = 1085 + index * 63;
  const y = 119;
  const id = `oled-${key}`;
  modulePosition[id] = [x, y];
  const pin = svg('g', { class: 'module-pin', 'data-terminal': id, 'data-signal': signal, style: `--signal:${css[signal]}`, tabindex: '0', role: 'button' });
  pin.append(svg('circle', { cx: x, cy: y, r: 9 }));
  pin.append(svg('text', { x, y: y - 17, 'text-anchor': 'middle' }, label));
  oledPins.append(pin);
});

const wireLayer = document.querySelector('#wireLayer');
function addWire(connection, path, groups = connection.group, suffix = '') {
  wireLayer.append(
    svg('path', { class: 'wire-hit', 'data-connection': connection.id, 'data-groups': groups.join(' '), d: path }),
    svg('path', { class: 'wire', id: `${connection.id}-${suffix}`, 'data-connection': connection.id, 'data-groups': groups.join(' '), 'data-signal': connection.signal, style: `--signal:${css[connection.signal]}`, d: path })
  );
}

connections.filter(connection => connection.targets).forEach((connection, index) => {
  const [px, py] = pinPosition[connection.from];
  const splitX = 952 + index * 22;
  const splitY = 556 + index * 12;
  addWire(connection, `M${px} ${py} H${splitX} V${splitY}`, connection.group, 'trunk');
  connection.targets.forEach((target, targetIndex) => {
    const [tx, ty] = modulePosition[target];
    const group = [targetIndex === 0 ? 'left' : 'right'];
    addWire(connection, `M${splitX} ${splitY} V${ty} H${tx}`, group, targetIndex === 0 ? 'left' : 'right');
  });
});

connections.filter(connection => connection.target).forEach((connection, index) => {
  const [px, py] = pinPosition[connection.from];
  const [tx, ty] = modulePosition[connection.target];
  const laneX = 955 + index * 17;
  const laneY = 315 + index * 15;
  addWire(connection, `M${px} ${py} H${laneX} V${laneY} H${tx} V${ty}`, connection.group, 'direct');
});
connections.filter(connection => connection.path).forEach(connection => addWire(connection, connection.path, connection.group, 'direct'));

const solderPinMeta = {
  3: { label: 'SDA', signal: 'sda', detail: 'OLED SDA wire' },
  5: { label: 'SCL', signal: 'scl', detail: 'OLED SCL wire' },
  14: { label: 'GND', signal: 'ground', detail: 'OLED ground' },
  17: { label: '3.3 V', signal: 'power', detail: 'OLED VCC' }
};

function addText(parent, attrs, text) { parent.append(svg('text', attrs, text)); }

function buildUnderside() {
  const layer = document.querySelector('#undersideLayer');
  layer.append(svg('rect', { class: 'underside-board', x: 382, y: 75, width: 640, height: 790, rx: 42 }));
  [[430, 125], [974, 125], [430, 812], [974, 812]].forEach(([cx, cy]) => layer.append(svg('circle', { class: 'underside-mount', cx, cy, r: 18 })));

  layer.append(svg('rect', { class: 'underside-sd', x: 614, y: 54, width: 177, height: 38, rx: 6 }));
  addText(layer, { class: 'under-edge-label', x: 702, y: 35, 'text-anchor': 'middle' }, 'microSD END — KEEP THIS AT THE TOP');
  layer.append(svg('path', { class: 'under-orientation-line', d: 'M702 43v-22m0 0l-9 10m9-10l9 10' }));

  layer.append(svg('rect', { class: 'underside-header-bed', x: 430, y: 155, width: 132, height: 590, rx: 20 }));
  addText(layer, { class: 'under-header-title', x: 496, y: 135, 'text-anchor': 'middle' }, 'GPIO SOLDER PADS');

  for (let row = 0; row < 20; row += 1) {
    for (let col = 0; col < 2; col += 1) {
      // Underside is mirrored: even pins are the left column, odd pins the right.
      const number = row * 2 + (col === 0 ? 2 : 1);
      const x = col === 0 ? 467 : 525;
      const y = 181 + row * 28.2;
      const meta = solderPinMeta[number];
      const pad = svg('g', {
        class: `solder-pad${meta ? ' target' : ''}${number === 1 ? ' pin-one' : ''}`,
        'data-solder-pin': number,
        'data-connection': meta ? `oled-${meta.label === '3.3 V' ? 'power' : meta.label.toLowerCase()}` : '',
        style: `--signal:${meta ? css[meta.signal] : 'var(--dim)'}`,
        tabindex: meta ? '0' : '-1', role: meta ? 'button' : 'presentation'
      });
      pad.append(number === 1
        ? svg('rect', { x: x - 10, y: y - 10, width: 20, height: 20, rx: 2 })
        : svg('circle', { cx: x, cy: y, r: 10 }));
      pad.append(svg('circle', { class: 'solder-hole', cx: x, cy: y, r: 4 }));
      pad.append(svg('text', { class: 'solder-number', x: col === 0 ? x - 19 : x + 19, y: y + 4, 'text-anchor': col === 0 ? 'end' : 'start' }, String(number)));
      if (meta) {
        pad.append(svg('text', { class: 'solder-signal', x: 585, y: y + 4 }, `${meta.label}  ·  PHYSICAL PIN ${number}`));
        pad.append(svg('path', { class: 'solder-leader', d: `M${x + 13} ${y}H574` }));
      }
      layer.append(pad);
    }
  }

  layer.append(svg('rect', { class: 'under-callout safe', x: 755, y: 170, width: 225, height: 158, rx: 18 }));
  addText(layer, { class: 'under-callout-title', x: 782, y: 205 }, 'OLED: FOUR JOINTS');
  addText(layer, { class: 'under-copy', x: 782, y: 235 }, '3  · SDA  · blue');
  addText(layer, { class: 'under-copy', x: 782, y: 258 }, '5  · SCL  · cyan');
  addText(layer, { class: 'under-copy', x: 782, y: 281 }, '14 · GND  · gray');
  addText(layer, { class: 'under-copy', x: 782, y: 304 }, '17 · 3.3 V · orange');

  layer.append(svg('rect', { class: 'under-callout warning', x: 755, y: 356, width: 465, height: 214, rx: 18 }));
  addText(layer, { class: 'under-warning-title', x: 782, y: 392 }, 'BEFORE SOLDERING');
  addText(layer, { class: 'under-copy', x: 782, y: 424 }, '1. Disconnect USB power and the battery.');
  addText(layer, { class: 'under-copy', x: 782, y: 450 }, '2. If fitting a loose header, solder all 40 pins.');
  addText(layer, { class: 'under-copy', x: 782, y: 476 }, '3. Heat the pad and pin together; use little solder.');
  addText(layer, { class: 'under-copy', x: 782, y: 502 }, '4. No solder may bridge neighboring pads.');
  addText(layer, { class: 'under-copy', x: 782, y: 528 }, '5. Inspect both rows before reconnecting power.');

  layer.append(svg('rect', { class: 'under-callout mirror', x: 755, y: 604, width: 465, height: 132, rx: 18 }));
  addText(layer, { class: 'under-callout-title', x: 782, y: 640 }, 'MIRROR CHECK');
  addText(layer, { class: 'under-copy', x: 782, y: 670 }, 'Underside + microSD up = GPIO is on the LEFT.');
  addText(layer, { class: 'under-copy', x: 782, y: 697 }, 'Square pad 1 is the TOP-RIGHT solder pad.');
  addText(layer, { class: 'under-copy emphasis', x: 782, y: 722 }, 'If those landmarks disagree, rotate the board—do not guess.');

  addText(layer, { class: 'under-board-title', x: 702, y: 805, 'text-anchor': 'middle' }, 'PI ZERO W · UNDERSIDE / SOLDER SIDE');
  addText(layer, { class: 'under-board-sub', x: 702, y: 829, 'text-anchor': 'middle' }, 'BOARD IS MIRRORED FROM THE COMPONENT-SIDE VIEW');
}
buildUnderside();

let currentGroup = 'all';
let selectedConnection = null;
const list = document.querySelector('#connectionList');

function relevant(connection, group) { return group === 'all' || group === 'clearance' || (group === 'solder' ? connection.group.includes('oled') : connection.group.includes(group)); }
function relevantWire(element, group) { return group === 'all' || group === 'clearance' || (group === 'solder' ? (element.dataset.groups || '').split(' ').includes('oled') : (element.dataset.groups || '').split(' ').includes(group)); }

function renderList() {
  list.replaceChildren();
  connections.filter(connection => relevant(connection, currentGroup)).forEach(connection => {
    const button = document.createElement('button');
    button.className = `connection${selectedConnection === connection.id ? ' active' : ''}`;
    button.style.setProperty('--signal', css[connection.signal]);
    button.innerHTML = `<i></i><span><b>${connection.label}</b><small>${connection.detail}</small></span>`;
    button.onclick = () => selectConnection(connection.id);
    list.append(button);
  });
}

function applyState() {
  document.querySelectorAll('.wire,.wire-hit').forEach(element => {
    const show = relevantWire(element, currentGroup) && (!selectedConnection || selectedConnection === element.dataset.connection);
    element.classList.toggle('muted', !show);
    element.classList.toggle('active', selectedConnection === element.dataset.connection && show);
  });
  document.querySelectorAll('.gpio-pin.used').forEach(element => {
    const number = Number(element.dataset.pin);
    const show = connections.some(connection => connection.from === number && relevant(connection, currentGroup) && (!selectedConnection || selectedConnection === connection.id));
    element.classList.toggle('muted', !show);
    element.classList.toggle('active', show && Boolean(selectedConnection));
  });
  document.querySelectorAll('.module').forEach(element => {
    const group = element.dataset.module;
    const muted = currentGroup !== 'all' && currentGroup !== 'clearance' && group !== currentGroup;
    element.classList.toggle('muted', muted);
  });
  document.querySelector('.clearance-layer').classList.toggle('visible', currentGroup === 'clearance');
  document.querySelector('#wiringDiagram').classList.toggle('solder-view', currentGroup === 'solder');
  document.querySelectorAll('.solder-pad.target').forEach(element => {
    const show = !selectedConnection || element.dataset.connection === selectedConnection;
    element.classList.toggle('muted', currentGroup === 'solder' && !show);
    element.classList.toggle('active', currentGroup === 'solder' && show && Boolean(selectedConnection));
  });
  document.querySelectorAll('.step').forEach(button => button.classList.toggle('active', button.dataset.group === currentGroup));
  renderList();
}

function setGroup(group) {
  currentGroup = group;
  selectedConnection = null;
  const [kicker, title, text] = viewCopy[group];
  document.querySelector('#detailKicker').textContent = kicker;
  document.querySelector('#detailTitle').textContent = title;
  document.querySelector('#detailText').textContent = text;
  document.querySelector('#viewTitle').textContent = kicker;
  document.querySelector('#viewSubtitle').textContent = group === 'clearance' ? 'Mechanical keep-out overlay' : group === 'solder' ? 'Underside · microSD end up · mirrored pin columns' : 'Click a connection to isolate it';
  applyState();
}

function selectConnection(id) { selectedConnection = selectedConnection === id ? null : id; applyState(); }
document.querySelectorAll('.step').forEach(button => { button.onclick = () => setGroup(button.dataset.group); });
document.querySelector('#resetView').onclick = () => setGroup('all');
document.querySelectorAll('.module').forEach(element => {
  const activate = () => setGroup(element.dataset.module);
  element.addEventListener('click', activate);
  element.addEventListener('keydown', event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); activate(); } });
});
document.querySelectorAll('.gpio-pin.used').forEach(element => {
  const activate = () => { const match = connections.find(connection => connection.from === Number(element.dataset.pin)); if (match) { currentGroup = 'all'; selectConnection(match.id); } };
  element.addEventListener('click', activate);
  element.addEventListener('keydown', event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); activate(); } });
});
document.querySelectorAll('.wire,.wire-hit').forEach(element => element.addEventListener('click', event => { event.stopPropagation(); selectConnection(element.dataset.connection); }));
document.querySelectorAll('.solder-pad.target').forEach(element => {
  const activate = () => selectConnection(element.dataset.connection);
  element.addEventListener('click', activate);
  element.addEventListener('keydown', event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); activate(); } });
});
const requestedView = window.location.hash.slice(1);
setGroup(Object.hasOwn(viewCopy, requestedView) ? requestedView : 'all');
