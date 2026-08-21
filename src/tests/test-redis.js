import { env, checkEnv } from '../config/env.js';
import { testRedisCache } from '../services/redis.js';

async function testRedisConnection() {
  console.log('=== Testing Service 3: Upstash Redis (Cache & Rate Limiting) ===\n');

  const urlCheck = checkEnv('UPSTASH_REDIS_REST_URL', env.upstashRedisRestUrl);
  const tokenCheck = checkEnv('UPSTASH_REDIS_REST_TOKEN', env.upstashRedisRestToken);

  console.log(urlCheck.message);
  console.log(tokenCheck.message);

  if (urlCheck.configured && tokenCheck.configured) {
    try {
      console.log('Executing test GET/SET ping operation against Upstash Redis...');
      const success = await testRedisCache();
      if (success) {
        console.log('[SUCCESS] Upstash Redis cache read/write operation verified!\n');
      } else {
        console.log('[ERROR] Redis cache test failed key mismatch.\n');
      }
    } catch (err) {
      console.error('[ERROR] Upstash Redis connection failed:', err.message, '\n');
    }
  } else {
    console.log('[SKIPPED] Provide UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN in .env.local to test.\n');
  }
}

testRedisConnection().catch(console.error);
