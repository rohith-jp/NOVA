import { create } from "zustand";
import { User, Session } from "@supabase/supabase-js";
import { supabase } from "@/lib/supabase";

interface AuthState {
  user: User | null;
  session: Session | null;
  loading: boolean;
  initialized: boolean;
  error: string | null;
  setError: (error: string | null) => void;
  initialize: () => () => void;
  signOut: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  session: null,
  loading: true,
  initialized: false,
  error: null,

  setError: (error: string | null) => set({ error }),

  initialize: () => {
    // 1. Get initial session
    supabase.auth.getSession().then(({ data: { session }, error }) => {
      if (error) {
        set({ error: error.message, loading: false, initialized: true });
      } else {
        set({
          session,
          user: session?.user ?? null,
          loading: false,
          initialized: true,
        });
      }
    });

    // 2. Listen for auth changes
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      set({
        session,
        user: session?.user ?? null,
        loading: false,
        initialized: true,
      });
    });

    return () => {
      subscription.unsubscribe();
    };
  },

  signOut: async () => {
    set({ loading: true, error: null });
    const { error } = await supabase.auth.signOut();
    if (error) {
      set({ error: error.message, loading: false });
    } else {
      set({ user: null, session: null, loading: false });
    }
  },
}));
