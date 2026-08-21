import { ElevenLabsClient } from 'elevenlabs';
import { env } from '../config/env.js';

let elevenLabsClient = null;

/**
 * Get ElevenLabs Client instance
 */
export function getElevenLabs() {
  if (!elevenLabsClient) {
    if (!env.elevenLabsApiKey) {
      throw new Error('ELEVENLABS_API_KEY is not configured in .env.local');
    }
    elevenLabsClient = new ElevenLabsClient({ apiKey: env.elevenLabsApiKey });
  }
  return elevenLabsClient;
}

/**
 * Convert text to speech audio stream
 */
export async function textToSpeech(text, voiceId = env.elevenLabsVoiceId) {
  const client = getElevenLabs();
  const audioStream = await client.generate({
    voice: voiceId,
    text: text,
    model_id: 'eleven_multilingual_v2'
  });
  return audioStream;
}
