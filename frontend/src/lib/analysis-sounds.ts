"use client";

export type AnalysisSound = "success" | "error";

let sharedAudioContext: AudioContext | null = null;

type BrowserAudioWindow = Window & {
  webkitAudioContext?: typeof AudioContext;
};

function getAudioContext() {
  if (typeof window === "undefined") {
    return null;
  }

  const audioWindow = window as BrowserAudioWindow;
  const AudioContextConstructor =
    window.AudioContext ?? audioWindow.webkitAudioContext ?? null;

  if (!AudioContextConstructor) {
    return null;
  }

  if (!sharedAudioContext) {
    sharedAudioContext = new AudioContextConstructor();
  }

  return sharedAudioContext;
}

function shapeTone(
  context: AudioContext,
  {
    startTime,
    frequency,
    duration,
    type,
    volume,
  }: {
    startTime: number;
    frequency: number;
    duration: number;
    type: OscillatorType;
    volume: number;
  },
) {
  const oscillator = context.createOscillator();
  const gainNode = context.createGain();

  oscillator.type = type;
  oscillator.frequency.setValueAtTime(frequency, startTime);

  gainNode.gain.setValueAtTime(0.0001, startTime);
  gainNode.gain.linearRampToValueAtTime(volume, startTime + 0.02);
  gainNode.gain.exponentialRampToValueAtTime(0.0001, startTime + duration);

  oscillator.connect(gainNode);
  gainNode.connect(context.destination);

  oscillator.start(startTime);
  oscillator.stop(startTime + duration + 0.02);
}

export async function primeAnalysisSound() {
  const context = getAudioContext();
  if (!context) {
    return;
  }

  if (context.state === "suspended") {
    await context.resume();
  }
}

export async function playAnalysisFinishedSound(sound: AnalysisSound) {
  const context = getAudioContext();
  if (!context) {
    return;
  }

  if (context.state === "suspended") {
    await context.resume();
  }

  const startTime = context.currentTime + 0.02;

  if (sound === "success") {
    shapeTone(context, {
      startTime,
      frequency: 659.25,
      duration: 0.14,
      type: "triangle",
      volume: 0.05,
    });
    shapeTone(context, {
      startTime: startTime + 0.12,
      frequency: 830.61,
      duration: 0.16,
      type: "triangle",
      volume: 0.055,
    });
    shapeTone(context, {
      startTime: startTime + 0.26,
      frequency: 987.77,
      duration: 0.2,
      type: "sine",
      volume: 0.06,
    });
    return;
  }

  shapeTone(context, {
    startTime,
    frequency: 349.23,
    duration: 0.18,
    type: "sawtooth",
    volume: 0.04,
  });
  shapeTone(context, {
    startTime: startTime + 0.14,
    frequency: 246.94,
    duration: 0.24,
    type: "sawtooth",
    volume: 0.045,
  });
}
