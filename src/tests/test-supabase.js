import { env, checkEnv } from '../config/env.js';
import { getSupabase, testSupabaseHealth } from '../services/supabase.js';

async function testSupabaseConnection() {
  console.log('=== Testing Service 2: Supabase (Database, Auth, Vectors) ===\n');

  const urlCheck = checkEnv('NEXT_PUBLIC_SUPABASE_URL', env.supabaseUrl);
  const anonCheck = checkEnv('NEXT_PUBLIC_SUPABASE_ANON_KEY', env.supabaseAnonKey);
  const serviceCheck = checkEnv('SUPABASE_SERVICE_ROLE_KEY', env.supabaseServiceRoleKey);

  console.log(urlCheck.message);
  console.log(anonCheck.message);
  console.log(serviceCheck.message);

  if (urlCheck.configured && anonCheck.configured) {
    try {
      console.log('\nTesting Supabase REST API connection...');
      await testSupabaseHealth();
      console.log('[SUCCESS] Supabase project URL and Anon key connected successfully!');

      // Check auth service
      const supabase = getSupabase();
      const { data, error } = await supabase.auth.getSession();
      if (!error) {
        console.log('[SUCCESS] Supabase Auth service is active and responsive!');
      }
      console.log('\n[SUCCESS] Supabase integration verified!\n');
    } catch (err) {
      console.error('[ERROR] Supabase connection failed:', err.message, '\n');
    }
  } else {
    console.log('\n[SKIPPED] Provide NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY in .env.local to test.\n');
  }
}

testSupabaseConnection().catch(console.error);
