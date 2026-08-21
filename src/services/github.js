import { Octokit } from '@octokit/rest';
import { env } from '../config/env.js';

let octokitClient = null;

/**
 * Get GitHub Octokit API Client instance
 */
export function getOctokit() {
  if (!octokitClient) {
    if (!env.githubToken) {
      throw new Error('GITHUB_TOKEN is not configured in .env.local');
    }
    octokitClient = new Octokit({ auth: env.githubToken });
  }
  return octokitClient;
}

/**
 * Verify GitHub Auth User
 */
export async function getGitHubUser() {
  const octokit = getOctokit();
  const { data } = await octokit.users.getAuthenticated();
  return data;
}
