/* Match orbit_at_times in Python; absolute time preserves phase and Earth rotation. */
(function (root) {
  function position(time, orbit) {
    const rad = Math.PI / 180;
    const phase = 2 * Math.PI * time / orbit.period;
    const inclination = orbit.inclination * rad;
    const latitude = Math.asin(Math.max(-1, Math.min(1, Math.sin(inclination) * Math.sin(phase)))) / rad;
    const inertial = Math.atan2(Math.cos(inclination) * Math.sin(phase), Math.cos(phase)) / rad;
    const longitude = inertial + orbit.startLongitude - 360 * time / orbit.siderealDay;
    return [((longitude + 180) % 360 + 360) % 360 - 180, latitude];
  }
  function displayTime(packet, received, now, correction = 0) {
    if (!packet.running) return packet.time;
    // Freeze after a lost connection or throttled tab instead of advancing forever.
    const elapsed = Math.min(2, Math.max(0, (now - received) / 1000));
    // A long enough correction time prevents positive offsets making time reverse.
    const smoothing = Math.max(0.4, Math.abs(correction) / packet.pace);
    return packet.time + elapsed * packet.pace + correction * Math.exp(-elapsed / smoothing);
  }
  function fitMap(availableWidth, availableHeight) {
    const width = Math.max(1, Math.min(availableWidth, availableHeight * 12 / 5.5));
    return {width, height: width * 5.5 / 12};
  }
  const api = {position, displayTime, fitMap};
  if (typeof module !== "undefined") module.exports = api;
  else root.OrbitAnimation = api;
})(globalThis);
