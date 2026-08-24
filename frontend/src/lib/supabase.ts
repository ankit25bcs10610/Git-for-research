import { createClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL as string | undefined
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined

// True once real credentials are provided via env vars. Every caller must
// check this before using `supabase` -- without it, `supabase` is null and
// there is nothing to actually talk to yet.
export const supabaseConfigured = Boolean(supabaseUrl && supabaseAnonKey)

export const supabase = supabaseConfigured ? createClient(supabaseUrl!, supabaseAnonKey!) : null
