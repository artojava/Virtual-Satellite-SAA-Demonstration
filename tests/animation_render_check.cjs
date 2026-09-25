// Exercise the actual renderer against a lightweight DOM/canvas test double.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const folder = process.argv[2];
let now = 0, animationFrame, messageListener, lineSegments = [];
const messages = [];
const ctx = new Proxy({}, {get(target, name) {
  if (name === 'moveTo' || name === 'lineTo') return (...point) => lineSegments.push([name, ...point]);
  return () => {};
}});
const elements = Object.fromEntries(['map', 'background', 'history', 'motion', 'status'].map(id =>
  [id, {clientWidth: 1200, style: {}, getContext: () => ctx, getAttribute(name) {return this[name];}}]));
let resizeCallback;
const root = {clientWidth: 1200};
const parent = {innerHeight: 900, postMessage: message => messages.push(message), addEventListener() {}};
const environment = {
  document: {documentElement: root, getElementById: id => elements[id]},
  window: {parent, frameElement: {getBoundingClientRect: () => ({top: 300})},
    devicePixelRatio: 2, addEventListener: (type, listener) => {
      if (type === 'message') messageListener = listener;
      if (type === 'resize') resizeCallback = listener;
    }},
  performance: {now: () => now},
  ResizeObserver: class {observe() {}},
  requestAnimationFrame: callback => {animationFrame = callback;},
  OrbitAnimation: require(path.join(folder, 'orbit.js')),
};
vm.createContext(environment);
vm.runInContext(fs.readFileSync(path.join(folder, 'render.js'), 'utf8'), environment);
assert.ok(messages.some(m => m.type === 'streamlit:componentReady'));
assert.ok(messages.some(m => m.type === 'streamlit:setFrameHeight' && m.height === 550));
const payload = {mission: 'a', time: 0, running: true, pace: 300, period: 5700,
  inclination: 51.6, startLongitude: -90, siderealDay: 86164.0905,
  track: [[0,179,0], [1,-179,1]], events: [[0,179,0,1]]};
function render(packet) {
  messageListener({source: parent, data: {type:'streamlit:render',
    args: {payload: packet, background: {bounds: [0,0,1,1], image: 'map'}}}});
}
render(payload);
assert.equal(lineSegments[0][0], 'moveTo');
assert.equal(lineSegments[1][0], 'moveTo'); // Never draw across the whole map at the date line.
animationFrame(0); const first = elements.status.textContent;
animationFrame(16); assert.notEqual(elements.status.textContent, first);
animationFrame(3000); assert.match(elements.status.textContent, /Waiting/);
now = 3000; render({...payload, running:false, time:100});
animationFrame(3100); const paused = elements.status.textContent;
animationFrame(9900); assert.equal(elements.status.textContent, paused);
now = 10000; render({...payload, mission:'b', running:false, time:0});
animationFrame(10000); assert.equal(elements.status.textContent, first);
// A wide, short window must shrink the whole map to the remaining viewport height.
parent.innerHeight = 500;
resizeCallback();
assert.equal(parseFloat(elements.map.style.height), 184);
assert.ok(parseFloat(elements.map.style.width) < 1200);
assert.ok(messages.some(m => m.type === 'streamlit:setFrameHeight' && m.height === 184));
// A narrow window must instead fit the available width without distortion.
root.clientWidth = 320; parent.innerHeight = 900;
resizeCallback();
assert.equal(parseFloat(elements.map.style.width), 320);
assert.ok(Math.abs(parseFloat(elements.map.style.height) - 320 * 5.5 / 12) < 1e-8);
// Hiding a tab does not destroy its canvas; reopening it retains correct sizing.
const savedWidth = elements.history.width;
root.clientWidth = 0; resizeCallback();
assert.equal(elements.history.width, savedWidth);
root.clientWidth = 1200; resizeCallback();
assert.equal(parseFloat(elements.map.style.width), 1200);
