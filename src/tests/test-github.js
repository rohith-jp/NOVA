import { env, checkEnv } from '../config/env.js';
import { getGitHubUser } from '../services/github.js';

async function testGitHubConnection() {
  console.log('=== Testing Service 8: GitHub (Version Control & CI/CD) ===\n');

  const tokenCheck = checkEnv('GITHUB_TOKEN', env.githubToken);
  console.log(tokenCheck.message);

  if (tokenCheck.configured) {
    try {
      console.log('Authenticating with GitHub API...');
      const user = await getGitHubUser();
      console.log(`[SUCCESS] Authenticated as GitHub user: @${user.login} (${user.name || 'User'})`);
      console.log('[SUCCESS] GitHub API integration verified!\n');
    } catch (err) {
      console.error('[ERROR] GitHub authentication failed:', err.message, '\n');
    }
  } else {
    console.log('[SKIPPED] Provide GITHUB_TOKEN in .env.local to test.\n');
  }
}

testGitHubConnection().catch(console.error);
