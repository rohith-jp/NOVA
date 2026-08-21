import { tavily } from '@tavily/core';
import { env } from '../config/env.js';

let tavilyClient = null;

/**
 * Get Tavily Web Search Client
 */
export function getTavily() {
  if (!tavilyClient) {
    if (!env.tavilyApiKey) {
      throw new Error('TAVILY_API_KEY is not configured in .env.local');
    }
    tavilyClient = tavily({ apiKey: env.tavilyApiKey });
  }
  return tavilyClient;
}

/**
 * Perform Web Search via Tavily
 */
export async function searchWeb(query, options = { maxResults: 3 }) {
  const client = getTavily();
  const response = await client.search(query, options);
  return response.results || [];
}
