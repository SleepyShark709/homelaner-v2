(async () => {
  const context = new AudioContext();
  const result = {};
  for (const [name, url] of [['cannon', '/assets/audio/cannonexplode01_stereo.ogg'], ['whoosh', '/assets/audio/sweetener_whooshf01.ogg']]) {
    const response = await fetch(url);
    const buffer = await context.decodeAudioData(await response.arrayBuffer());
    result[name] = { duration: buffer.duration, sampleRate: buffer.sampleRate, channels: buffer.numberOfChannels };
  }
  await context.close();
  return result;
})()
