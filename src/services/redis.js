import { Redis } from '@upstash/redis';
import { env } from '../config/env.js';

let redisClient = null;

/**
 * Get Upstash Redis Client instance
 */
export function getRedis() {
  if (!redisClient) {
    if (!env.upstashRedisRestUrl || !env.upstashRedisRestToken) {
      throw new Error('UPSTASH_REDIS_REST_URL or UPSTASH_REDIS_REST_TOKEN is not configured in .env.local');
    }
    redisClient = new Redis({
      url: env.upstashRedisRestUrl,
      token: env.upstashRedisRestToken
    });
  }
  return redisClient;
}

/**
 * Test Redis cache get/set operations
 */
export async function testRedisCache() {
  const redis = getRedis();
  const testKey = `nova_test_${Date.now()}`;
  const testVal = 'connected';

  // SET with 60s TTL
  await redis.set(testKey, testVal, { ex: 60 });
  const retrievedVal = await redis.get(testKey);
  await redis.del(testKey);

  return retrievedVal === testVal;
}
