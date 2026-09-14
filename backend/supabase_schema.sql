-- Aura AI Assistant - Supabase Cloud Database Schema
-- Run this in your Supabase SQL Editor (https://supabase.com/dashboard/project/srrpewuenwnusmxmazho/sql)
-- This creates cloud tables for user profiles, chat history, and notes.

-- 1. User Profiles Table
CREATE TABLE IF NOT EXISTS public.profiles (
    id BIGSERIAL PRIMARY KEY,
    auth_user_id TEXT,
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    role TEXT DEFAULT 'Creator',
    gender TEXT DEFAULT 'male',
    avatar_url TEXT,
    bio TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 2. Chat Sessions Table
CREATE TABLE IF NOT EXISTS public.chat_sessions (
    id TEXT PRIMARY KEY,
    user_email TEXT,
    title TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 3. Chat Messages Table
CREATE TABLE IF NOT EXISTS public.chat_messages (
    id BIGSERIAL PRIMARY KEY,
    session_id TEXT REFERENCES public.chat_sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 4. User Notes Table
CREATE TABLE IF NOT EXISTS public.user_notes (
    id BIGSERIAL PRIMARY KEY,
    user_email TEXT,
    title TEXT NOT NULL,
    content TEXT,
    status TEXT DEFAULT 'pending',
    due_date TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Enable Row Level Security (RLS)
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chat_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_notes ENABLE ROW LEVEL SECURITY;

-- Allow read/write access via Supabase Anon/Publishable Key
CREATE POLICY "Allow all access to profiles" ON public.profiles FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all access to chat_sessions" ON public.chat_sessions FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all access to chat_messages" ON public.chat_messages FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all access to user_notes" ON public.user_notes FOR ALL USING (true) WITH CHECK (true);
