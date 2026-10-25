(async () => {
  const context = new AudioContext();
  const response = await fetch('/assets/audio/chain_d_impacts_0201.ogg');
  const buffer = await context.decodeAudioData(await response.arrayBuffer());
  const result = { duration: buffer.duration, sampleRate: buffer.sampleRate, channels: buffer.numberOfChannels };
  await context.close();
  return result;
})()
