import { env, checkEnv } from '../config/env.js';
import { getElevenLabs, textToSpeech } from '../services/elevenlabs.js';

async function testElevenLabsConnection() {
  console.log('=== Testing Service 5: ElevenLabs (Voice Synthesis / TTS) ===\n');

  const apiKeyCheck = checkEnv('ELEVENLABS_API_KEY', env.elevenLabsApiKey);
  console.log(apiKeyCheck.message);

  if (apiKeyCheck.configured) {
    try {
      console.log('Testing ElevenLabs user profile & voices API...');
      const client = getElevenLabs();
      const user = await client.user.get();
      console.log(`ElevenLabs User: ${user.subscription?.tier || 'Active'} Tier`);

      console.log('Generating test audio stream for text: "Hello NOVA!"...');
      const stream = await textToSpeech('Hello NOVA!');
      if (stream) {
        console.log('[SUCCESS] ElevenLabs TTS audio stream generated successfully!\n');
      }
    } catch (err) {
      console.error('[ERROR] ElevenLabs connection failed:', err.message, '\n');
    }
  } else {
    console.log('[SKIPPED] Provide ELEVENLABS_API_KEY in .env.local to test.\n');
  }
}

testElevenLabsConnection().catch(console.error);
