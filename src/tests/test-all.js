import { env, checkEnv } from '../config/env.js';

console.log('====================================================');
console.log('       NOVA AI ASSISTANT - MASTER SERVICES TEST     ');
console.log('====================================================\n');

const services = [
  { name: '1. Google Gemini API', key: 'GEMINI_API_KEY', val: env.geminiApiKey },
  { name: '   Groq Cloud API', key: 'GROQ_API_KEY', val: env.groqApiKey },
  { name: '2. Supabase URL', key: 'NEXT_PUBLIC_SUPABASE_URL', val: env.supabaseUrl },
  { name: '   Supabase Anon Key', key: 'NEXT_PUBLIC_SUPABASE_ANON_KEY', val: env.supabaseAnonKey },
  { name: '   Supabase Service Role', key: 'SUPABASE_SERVICE_ROLE_KEY', val: env.supabaseServiceRoleKey },
  { name: '3. Upstash Redis REST URL', key: 'UPSTASH_REDIS_REST_URL', val: env.upstashRedisRestUrl },
  { name: '   Upstash Redis REST Token', key: 'UPSTASH_REDIS_REST_TOKEN', val: env.upstashRedisRestToken },
  { name: '4. Tavily Web Search API', key: 'TAVILY_API_KEY', val: env.tavilyApiKey },
  { name: '5. ElevenLabs API Key', key: 'ELEVENLABS_API_KEY', val: env.elevenLabsApiKey },
  { name: '6. Vercel Token', key: 'VERCEL_TOKEN', val: env.vercelToken },
  { name: '7. Railway Backend URL', key: 'BACKEND_URL', val: env.backendUrl },
  { name: '8. GitHub PAT Token', key: 'GITHUB_TOKEN', val: env.githubToken }
];

let configuredCount = 0;

console.log('ENVIRONMENT VARIABLES AUDIT:');
services.forEach(s => {
  const result = checkEnv(s.key, s.val);
  if (result.configured) configuredCount++;
  console.log(` ${s.name.padEnd(28)} : ${result.configured ? '✅ CONFIG' : '⚠️ MISSING'}`);
});

console.log(`\nStatus Summary: ${configuredCount}/${services.length} credentials present in .env.local\n`);
console.log('To run individual connection tests:');
console.log(' - npm run test:ai');
console.log(' - npm run test:supabase');
console.log(' - npm run test:redis');
console.log(' - npm run test:tavily');
console.log(' - npm run test:elevenlabs');
console.log(' - npm run test:vercel');
console.log(' - npm run test:github');
console.log('====================================================\n');
