-- Enable extensions
create extension if not exists "vector";

-- Enum for Roles
create type app_role as enum ('admin', 'manager', 'user');

-- Users Table (extends auth.users)
create table public.users (
  id uuid references auth.users on delete cascade not null primary key,
  email text not null,
  full_name text,
  role app_role not null default 'user',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- Folders
create table public.folders (
  id uuid default gen_random_uuid() primary key,
  name text not null,
  parent_id uuid references public.folders(id),
  owner_id uuid references public.users(id),
  
  -- Permissions
  allowed_roles app_role[] default '{}',
  allowed_users uuid[] default '{}',
  
  created_at timestamptz default now()
);

-- Documents
create table public.documents (
  id uuid default gen_random_uuid() primary key,
  folder_id uuid references public.folders(id),
  owner_id uuid references public.users(id),
  
  title text not null,
  storage_path text not null, -- Path in Supabase Storage
  mime_type text,
  metadata jsonb default '{}',
  
  -- Inherits permissions from folder usually, but can override?
  -- For now, let's assume strict folder-based permissions + optional override
  allowed_roles app_role[] default '{}',
  allowed_users uuid[] default '{}',
  
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- Document Chunks (for RAG)
create table public.document_chunks (
  id uuid default gen_random_uuid() primary key,
  document_id uuid references public.documents(id) on delete cascade,
  
  content text not null,
  page_number int,
  chunk_index int,
  
  -- Metadata for highlighting
  start_char_idx int,
  end_char_idx int,
  
  -- Vector Embedding (OpenAI small = 1536)
  embedding vector(1536),
  
  metadata jsonb default '{}'
);

-- Index for vector search
create index on public.document_chunks using hnsw (embedding vector_cosine_ops);

-- Chat System
create table public.conversations (
  id uuid default gen_random_uuid() primary key,
  user_id uuid references public.users(id) on delete cascade,
  title text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table public.messages (
  id uuid default gen_random_uuid() primary key,
  conversation_id uuid references public.conversations(id) on delete cascade,
  role text not null check (role in ('user', 'assistant', 'system')),
  content text not null,
  
  -- Citations: Array of objects { chunk_id, label, text_preview }
  citations jsonb default '[]',
  
  created_at timestamptz default now()
);

-- Audit Logs
create table public.audit_logs (
  id uuid default gen_random_uuid() primary key,
  user_id uuid references public.users(id),
  action text not null,
  resource_type text,
  resource_id uuid,
  details jsonb,
  created_at timestamptz default now()
);

-- RLS Policies (Examples)
alter table public.users enable row level security;
alter table public.folders enable row level security;
alter table public.documents enable row level security;
alter table public.document_chunks enable row level security;
alter table public.conversations enable row level security;
alter table public.messages enable row level security;

-- Policy: Users can read their own profile
create policy "Users can read own profile" on public.users
  for select using (auth.uid() = id);

-- Policy: Admin can do everything
-- (Implementation of specific RBAC policies requires Supabase Auth functions)
