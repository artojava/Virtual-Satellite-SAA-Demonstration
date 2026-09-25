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
  [id, {clientWidth: 1200, getContext: () => ctx, getAttribute(name) {return this[name];}}]));
const parent = {postMessage: message => messages.push(message)};
const environment = {
  document: {getElementById: id => elements[id]},
  window: {parent, devicePixelRatio: 2, addEventListener: (_, listener) => {messageListener = listener;}},
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
