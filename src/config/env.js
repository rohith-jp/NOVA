import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Load .env.local first, fallback to .env
dotenv.config({ path: path.resolve(__dirname, '../../.env.local') });
dotenv.config({ path: path.resolve(__dirname, '../../.env') });

export const env = {
  // 1. AI Models
  geminiApiKey: process.env.GEMINI_API_KEY || process.env.GOOGLE_GENERATIVE_AI_API_KEY || '',
  groqApiKey: process.env.GROQ_API_KEY || '',

  // 2. Supabase
  supabaseUrl: process.env.NEXT_PUBLIC_SUPABASE_URL || process.env.SUPABASE_URL || '',
  supabaseAnonKey: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || process.env.SUPABASE_ANON_KEY || '',
  supabaseServiceRoleKey: process.env.SUPABASE_SERVICE_ROLE_KEY || '',
  databaseUrl: process.env.DATABASE_URL || '',

  // 3. Upstash Redis
  upstashRedisRestUrl: process.env.UPSTASH_REDIS_REST_URL || '',
  upstashRedisRestToken: process.env.UPSTASH_REDIS_REST_TOKEN || '',
  redisUrl: process.env.REDIS_URL || '',

  // 4. Tavily
  tavilyApiKey: process.env.TAVILY_API_KEY || '',

  // 5. ElevenLabs
  elevenLabsApiKey: process.env.ELEVENLABS_API_KEY || '',
  elevenLabsVoiceId: process.env.ELEVENLABS_VOICE_ID || '21m00Tcm4TlvDq8ikWAM', // default Rachel voice

  // 6. Railway & Backend
  backendUrl: process.env.BACKEND_URL || 'http://localhost:3000',
  railwayToken: process.env.RAILWAY_TOKEN || '',
  port: process.env.PORT || 3000,

  // 7. Vercel
  vercelToken: process.env.VERCEL_TOKEN || '',
  vercelProjectId: process.env.VERCEL_PROJECT_ID || '',
  vercelOrgId: process.env.VERCEL_ORG_ID || '',

  // 8. GitHub
  githubRepoUrl: process.env.GITHUB_REPO_URL || 'https://github.com/rohith-jp/NOVA',
  githubToken: process.env.GITHUB_TOKEN || process.env.GITHUB_PAT || '',
  githubClientId: process.env.GITHUB_CLIENT_ID || '',
  githubClientSecret: process.env.GITHUB_CLIENT_SECRET || ''
};

export function checkEnv(keyName, value) {
  if (!value || value.includes('your_') || value.includes('here')) {
    return {
      configured: false,
      message: `[WARNING] ${keyName} is missing or has placeholder value in .env.local`
    };
  }
  return {
    configured: true,
    message: `[OK] ${keyName} is configured.`
  };
}
