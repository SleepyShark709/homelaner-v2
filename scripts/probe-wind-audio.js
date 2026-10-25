(async () => {
  const context = new AudioContext();
  const response = await fetch('/assets/audio/flourish03.ogg');
  const buffer = await context.decodeAudioData(await response.arrayBuffer());
  const result = { duration: buffer.duration, sampleRate: buffer.sampleRate, channels: buffer.numberOfChannels };
  await context.close();
  return result;
})()
