import express from 'express';
import cors from 'cors';
import { env } from './config/env.js';

const app = express();
app.use(cors());
app.use(express.json());

// Service Status Endpoint
app.get('/api/health', (req, res) => {
  res.json({
    status: 'online',
    service: 'NOVA Backend (Railway)',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    servicesConfigured: {
      gemini: Boolean(env.geminiApiKey),
      groq: Boolean(env.groqApiKey),
      supabase: Boolean(env.supabaseUrl && env.supabaseAnonKey),
      redis: Boolean(env.upstashRedisRestUrl),
      tavily: Boolean(env.tavilyApiKey),
      elevenlabs: Boolean(env.elevenLabsApiKey),
      github: Boolean(env.githubToken)
    }
  });
});

app.get('/', (req, res) => {
  res.send('NOVA AI Assistant Backend Service is Running.');
});

const PORT = env.port;
app.listen(PORT, () => {
  console.log(`[NOVA Backend] Server listening on port ${PORT}`);
});

export default app;
