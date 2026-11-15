import { useCallback, useEffect, useRef, useState } from 'react';

export const SPEECH_LANGUAGE = 'en-US';
type SpeechEvent = Event & { resultIndex: number; results: ArrayLike<ArrayLike<{ transcript: string; isFinal: boolean }>> };
type SpeechError = Event & { error: string };
type Recognition = {
  continuous: boolean; interimResults: boolean; lang: string;
  onresult: ((event: SpeechEvent) => void) | null;
  onerror: ((event: SpeechError) => void) | null;
  onend: (() => void) | null;
  start: () => void; stop: () => void;
};
type SpeechWindow = Window & { SpeechRecognition?: new () => Recognition; webkitSpeechRecognition?: new () => Recognition };

const errors: Record<string, string> = {
  'not-allowed': 'Microphone access was denied. Allow microphone access in your browser settings.',
  'no-speech': 'No speech was detected. Try speaking closer to your microphone.',
  network: 'Speech recognition could not connect. Check your internet connection.',
  'audio-capture': 'No microphone was found. Connect a microphone and try again.',
};

export function useSpeechRecognition(onTranscript: (text: string) => void) {
  const [supported, setSupported] = useState(false);
  const [recording, setRecording] = useState(false);
  const [message, setMessage] = useState('');
  const recognition = useRef<Recognition | null>(null);
  const callback = useRef(onTranscript);
  callback.current = onTranscript;

  useEffect(() => {
    const Speech = (window as SpeechWindow).SpeechRecognition || (window as SpeechWindow).webkitSpeechRecognition;
    if (!Speech) return;
    setSupported(true);
    const instance = new Speech();
    instance.continuous = true;
    instance.interimResults = true;
    instance.lang = SPEECH_LANGUAGE;
    instance.onresult = event => {
      let finalized = '';
      for (let index = event.resultIndex; index < event.results.length; index += 1) {
        const result = event.results[index][0];
        if (result.isFinal) finalized += result.transcript;
      }
      if (finalized) callback.current(finalized);
    };
    instance.onerror = event => { setMessage(errors[event.error] || 'Speech recognition stopped unexpectedly.'); setRecording(false); };
    instance.onend = () => setRecording(false);
    recognition.current = instance;
    return () => { instance.onresult = null; instance.onerror = null; instance.onend = null; instance.stop(); recognition.current = null; };
  }, []);

  const start = useCallback(() => {
    if (!recognition.current) return;
    setMessage('');
    try { recognition.current.start(); setRecording(true); }
    catch { setMessage('Speech recognition is already active.'); }
  }, []);
  const stop = useCallback(() => { recognition.current?.stop(); setRecording(false); }, []);
  return { supported, recording, message, start, stop };
}
