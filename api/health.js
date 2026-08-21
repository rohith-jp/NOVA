import { env } from '../src/config/env.js';

export default function handler(req, res) {
  res.status(200).json({
    status: 'online',
    service: 'NOVA Vercel Edge / Serverless API',
    timestamp: new Date().toISOString(),
    envConfigured: {
      gemini: Boolean(env.geminiApiKey),
      groq: Boolean(env.groqApiKey),
      supabase: Boolean(env.supabaseUrl),
      redis: Boolean(env.upstashRedisRestUrl),
      tavily: Boolean(env.tavilyApiKey),
      elevenlabs: Boolean(env.elevenLabsApiKey)
    }
  });
}
