import { createClient } from '@supabase/supabase-js';
import { env } from '../config/env.js';

let supabaseAnonClient = null;
let supabaseAdminClient = null;

/**
 * Get Supabase Public / Anon Client
 */
export function getSupabase() {
  if (!supabaseAnonClient) {
    if (!env.supabaseUrl || !env.supabaseAnonKey) {
      throw new Error('NEXT_PUBLIC_SUPABASE_URL or NEXT_PUBLIC_SUPABASE_ANON_KEY is not configured in .env.local');
    }
    supabaseAnonClient = createClient(env.supabaseUrl, env.supabaseAnonKey);
  }
  return supabaseAnonClient;
}

/**
 * Get Supabase Admin Client (Service Role)
 */
export function getSupabaseAdmin() {
  if (!supabaseAdminClient) {
    if (!env.supabaseUrl || !env.supabaseServiceRoleKey) {
      throw new Error('SUPABASE_SERVICE_ROLE_KEY is not configured in .env.local');
    }
    supabaseAdminClient = createClient(env.supabaseUrl, env.supabaseServiceRoleKey, {
      auth: { persistSession: false }
    });
  }
  return supabaseAdminClient;
}

/**
 * Health check helper for Supabase connection
 */
export async function testSupabaseHealth() {
  const client = getSupabase();
  const { data, error } = await client.from('_health_check_test').select('*').limit(1);
  // A table missing error still confirms DB connection was made successfully
  if (error && error.code !== 'PGRST301' && error.code !== '42P01') {
    throw error;
  }
  return true;
}
