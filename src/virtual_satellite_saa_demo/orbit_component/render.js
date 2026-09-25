/* Streamlit component protocol, no external scripts or per-frame server requests. */
const map = document.getElementById("map");
const background = document.getElementById("background");
const history = document.getElementById("history");
const motion = document.getElementById("motion");
const status = document.getElementById("status");
let packet = null, bounds = null, received = 0, correction = 0, width = 1, height = 1;

function send(type, extra = {}) {
  window.parent.postMessage({isStreamlitMessage: true, type, ...extra}, "*");
}
function point(longitude, latitude) {
  return [(bounds[0] + (longitude + 180) / 360 * bounds[2]) * width,
          (bounds[1] + (90 - latitude) / 180 * bounds[3]) * height];
}
function clip(context) {
  context.beginPath();
  context.rect(bounds[0] * width, bounds[1] * height, bounds[2] * width, bounds[3] * height);
  context.clip();
}
function line(context, positions) {
  context.beginPath();
  let previous = null;
  for (const [lon, lat] of positions) {
    const [x, y] = point(lon, lat);
    if (previous === null || Math.abs(lon - previous) > 180) context.moveTo(x, y);
    else context.lineTo(x, y);
    previous = lon;
  }
  context.strokeStyle = "rgba(103,220,229,0.35)";
  context.lineWidth = 1;
  context.stroke();
}
function drawHistory() {
  if (!packet || !bounds) return;
  const context = history.getContext("2d");
  context.clearRect(0, 0, width, height);
  context.save(); clip(context);
  line(context, packet.track.map(row => row.slice(1)));
  context.fillStyle = "rgba(255,180,91,0.8)";
  for (const [, lon, lat, count] of packet.events) {
    const [x, y] = point(lon, lat);
    context.beginPath(); context.arc(x, y, Math.sqrt(12 + 9 * Math.sqrt(count)) / 2, 0, 2 * Math.PI);
    context.fill();
  }
  context.restore();
}
function resize() {
  width = Math.max(1, map.clientWidth); height = width * 5.5 / 12;
  const ratio = window.devicePixelRatio || 1;
  for (const canvas of [history, motion]) {
    canvas.width = Math.round(width * ratio); canvas.height = Math.round(height * ratio);
    canvas.getContext("2d").setTransform(ratio, 0, 0, ratio, 0, 0);
  }
  send("streamlit:setFrameHeight", {height: Math.ceil(height)});
  drawHistory();
}
window.addEventListener("message", event => {
  if (event.source !== window.parent || event.data.type !== "streamlit:render") return;
  const next = event.data.args.payload;
  const now = performance.now();
  // Reconcile small transport delays gradually; reset instantly for pause/scrub/new missions.
  correction = packet && packet.running && next.running && packet.mission === next.mission
    ? OrbitAnimation.displayTime(packet, received, now, correction) - next.time : 0;
  if (Math.abs(correction) > 2 * next.pace) correction = 0;
  packet = next; received = now;
  bounds = event.data.args.background.bounds;
  if (background.getAttribute("src") !== event.data.args.background.image)
    background.src = event.data.args.background.image;
  drawHistory();
});
function frame(now) {
  if (packet && bounds) {
    const context = motion.getContext("2d");
    context.clearRect(0, 0, width, height);
    const time = OrbitAnimation.displayTime(packet, received, now, correction);
    context.save(); clip(context);
    const last = packet.track[packet.track.length - 1];
    if (packet.running && time > last[0]) {
      const count = Math.max(1, Math.ceil((time - last[0]) / (packet.period / 360)));
      const tip = Array.from({length: count + 1}, (_, i) =>
        OrbitAnimation.position(last[0] + (time - last[0]) * i / count, packet));
      line(context, tip);
    }
    const [lon, lat] = OrbitAnimation.position(time, packet);
    const [x, y] = point(lon, lat);
    context.beginPath(); context.moveTo(x, y - 7); context.lineTo(x + 7, y);
    context.lineTo(x, y + 7); context.lineTo(x - 7, y); context.closePath();
    context.fillStyle = "white"; context.fill(); context.strokeStyle = "#0e1726";
    context.lineWidth = 1; context.stroke(); context.restore();
    status.textContent = `${lat.toFixed(2)}° lat · ${lon.toFixed(2)}° lon` +
      (packet.running && now - received > 2000 ? " · Waiting for update" : "");
  }
  requestAnimationFrame(frame);
}
new ResizeObserver(resize).observe(map);
send("streamlit:componentReady", {apiVersion: 1});
resize();
requestAnimationFrame(frame);
