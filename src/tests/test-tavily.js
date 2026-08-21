import { env, checkEnv } from '../config/env.js';
import { searchWeb } from '../services/tavily.js';

async function testTavilyConnection() {
  console.log('=== Testing Service 4: Tavily (Real-Time Web Search) ===\n');

  const tavilyCheck = checkEnv('TAVILY_API_KEY', env.tavilyApiKey);
  console.log(tavilyCheck.message);

  if (tavilyCheck.configured) {
    try {
      console.log('Executing test web search query ("Latest AI news")...');
      const results = await searchWeb('Latest AI news', { maxResults: 2 });
      console.log(`Retrieved ${results.length} search results:`);
      results.forEach((r, i) => console.log(` [${i + 1}] ${r.title} - ${r.url}`));
      console.log('[SUCCESS] Tavily API connection verified!\n');
    } catch (err) {
      console.error('[ERROR] Tavily web search failed:', err.message, '\n');
    }
  } else {
    console.log('[SKIPPED] Provide TAVILY_API_KEY in .env.local to test.\n');
  }
}

testTavilyConnection().catch(console.error);
