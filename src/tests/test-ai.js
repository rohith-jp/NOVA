import { env, checkEnv } from '../config/env.js';
import { generateGeminiText, generateGroqText } from '../services/ai.js';

async function testAIConnections() {
  console.log('=== Testing Service 1: AI Models (Gemini & Groq) ===\n');

  // 1. Check Gemini Env
  const geminiCheck = checkEnv('GEMINI_API_KEY', env.geminiApiKey);
  console.log(geminiCheck.message);

  if (geminiCheck.configured) {
    try {
      console.log('Sending test prompt to Google Gemini...');
      const response = await generateGeminiText('Hello NOVA! Respond with one sentence acknowledging connection.');
      console.log('Gemini Response:', response.trim());
      console.log('[SUCCESS] Google Gemini API connection verified!\n');
    } catch (err) {
      console.error('[ERROR] Google Gemini connection failed:', err.message, '\n');
    }
  } else {
    console.log('[SKIPPED] Provide a valid GEMINI_API_KEY in .env.local to test.\n');
  }

  // 2. Check Groq Env
  const groqCheck = checkEnv('GROQ_API_KEY', env.groqApiKey);
  console.log(groqCheck.message);

  if (groqCheck.configured) {
    try {
      console.log('Sending test prompt to Groq Cloud...');
      const response = await generateGroqText('Hello NOVA! Respond with one sentence acknowledging connection.');
      console.log('Groq Response:', response.trim());
      console.log('[SUCCESS] Groq API connection verified!\n');
    } catch (err) {
      console.error('[ERROR] Groq connection failed:', err.message, '\n');
    }
  } else {
    console.log('[SKIPPED] Provide a valid GROQ_API_KEY in .env.local to test.\n');
  }
}

testAIConnections().catch(console.error);
