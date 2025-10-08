-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- 1️⃣ Websites Table
CREATE TABLE sites (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    base_url TEXT NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2️⃣ Site Pages (Scraped Pages)
CREATE TABLE site_pages (
    id BIGSERIAL PRIMARY KEY,
    site_id UUID REFERENCES sites(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    title TEXT NOT NULL,
    summary TEXT,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (site_id, url)
);

-- 3️⃣ Page Chunks (Content Segmentation)
CREATE TABLE page_chunks (
    id BIGSERIAL PRIMARY KEY,
    page_id BIGINT REFERENCES site_pages(id) ON DELETE CASCADE,
    chunk_number INT NOT NULL,
    title TEXT,
    summary TEXT,
    content TEXT NOT NULL,
    token_count INT,
    embedding VECTOR(768), -- For OpenAI/Nomic/Gemma embeddings
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4️⃣ Embeddings Table (Optional — if you separate vectors)
CREATE TABLE embeddings (
    id BIGSERIAL PRIMARY KEY,
    chunk_id BIGINT REFERENCES page_chunks(id) ON DELETE CASCADE,
    model_name TEXT NOT NULL,
    embedding VECTOR(768),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
