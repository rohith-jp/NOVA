import { env, checkEnv } from '../config/env.js';
import handler from '../../api/health.js';

async function testVercelConnection() {
  console.log('=== Testing Service 6: Vercel (Frontend & Edge Functions) ===\n');

  const tokenCheck = checkEnv('VERCEL_TOKEN', env.vercelToken);
  const projectCheck = checkEnv('VERCEL_PROJECT_ID', env.vercelProjectId);

  console.log(tokenCheck.message);
  console.log(projectCheck.message);

  console.log('\nExecuting Vercel Serverless Function mock invocation...');
  const mockReq = { method: 'GET' };
  let responseData = null;
  let statusCode = null;

  const mockRes = {
    status(code) {
      statusCode = code;
      return this;
    },
    json(data) {
      responseData = data;
      return this;
    }
  };

  handler(mockReq, mockRes);

  if (statusCode === 200 && responseData?.status === 'online') {
    console.log('[SUCCESS] Vercel Serverless handler compiled and executed cleanly!');
    console.log('Handler Output:', responseData);
  } else {
    console.log('[ERROR] Vercel serverless handler returned error status:', statusCode);
  }
  console.log('\n');
}

testVercelConnection().catch(console.error);
