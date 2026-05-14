-- Initial schema for Decode Beijing
-- Run via: psql $DATABASE_URL -f this_file.sql
-- Or let Alembic handle it via: alembic upgrade head

CREATE TYPE meeting_category AS ENUM (
  'party_congress',
  'plenum',
  'two_sessions_national',
  'two_sessions_local',
  'economic_work_conference',
  'politburo'
);

CREATE TYPE term_category AS ENUM (
  'slogan',
  'policy_phrase',
  'ideological',
  'economic',
  'diplomatic',
  'other'
);

-- ─────────────────────────────────────
-- Reference tables
-- ─────────────────────────────────────

CREATE TABLE IF NOT EXISTS meeting_types (
  id          SERIAL PRIMARY KEY,
  category    meeting_category NOT NULL,
  name_zh     TEXT NOT NULL,
  name_en     TEXT NOT NULL,
  UNIQUE (category, name_zh)
);

-- Seed the standard meeting types
INSERT INTO meeting_types (category, name_zh, name_en) VALUES
  ('party_congress',          '中国共产党全国代表大会',     'National Congress of the CPC'),
  ('plenum',                  '中央委员会全体会议',         'Plenary Session of the Central Committee'),
  ('two_sessions_national',   '全国人民代表大会',           'National People''s Congress'),
  ('two_sessions_national',   '中国人民政治协商会议',       'Chinese People''s Political Consultative Conference'),
  ('economic_work_conference','中央经济工作会议',           'Central Economic Work Conference'),
  ('politburo',               '中央政治局会议',             'Politburo Meeting'),
  ('politburo',               '中央政治局常委会议',         'Politburo Standing Committee Meeting')
ON CONFLICT DO NOTHING;

-- ─────────────────────────────────────
-- Documents
-- ─────────────────────────────────────

CREATE TABLE IF NOT EXISTS documents (
  id              SERIAL PRIMARY KEY,
  meeting_type_id INTEGER REFERENCES meeting_types(id),
  title_zh        TEXT NOT NULL,
  title_en        TEXT,
  meeting_date    DATE NOT NULL,
  source_url      TEXT NOT NULL UNIQUE,
  raw_text_zh     TEXT NOT NULL,
  raw_text_en     TEXT,
  word_count_zh   INTEGER,
  scraped_at      TIMESTAMPTZ DEFAULT now(),
  processed_at    TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_documents_date     ON documents (meeting_date);
CREATE INDEX IF NOT EXISTS idx_documents_type     ON documents (meeting_type_id);
CREATE INDEX IF NOT EXISTS idx_documents_fts_zh   ON documents USING gin(to_tsvector('simple', raw_text_zh));

-- ─────────────────────────────────────
-- Tracked terms
-- ─────────────────────────────────────

CREATE TABLE IF NOT EXISTS terms (
  id              SERIAL PRIMARY KEY,
  term_zh         TEXT NOT NULL UNIQUE,
  term_en         TEXT,
  category        term_category NOT NULL DEFAULT 'other',
  description     TEXT,
  first_seen_doc  INTEGER REFERENCES documents(id),
  first_seen_date DATE,
  added_by        TEXT DEFAULT 'auto',
  created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_terms_zh ON terms (term_zh);

-- Seed well-known terms for initial tracking
INSERT INTO terms (term_zh, term_en, category, added_by) VALUES
  ('新质生产力',     'New Quality Productive Forces',  'slogan',        'manual'),
  ('房住不炒',       'Housing is for Living, not Speculation', 'policy_phrase', 'manual'),
  ('共同富裕',       'Common Prosperity',              'slogan',        'manual'),
  ('双循环',         'Dual Circulation',               'policy_phrase', 'manual'),
  ('高质量发展',     'High-Quality Development',       'policy_phrase', 'manual'),
  ('中国式现代化',   'Chinese-style Modernization',    'ideological',   'manual'),
  ('两个确立',       'Two Establishments',             'ideological',   'manual'),
  ('两个维护',       'Two Safeguards',                 'ideological',   'manual'),
  ('全过程人民民主', 'Whole-Process People''s Democracy','ideological', 'manual'),
  ('供给侧结构性改革','Supply-Side Structural Reform', 'economic',      'manual'),
  ('脱贫攻坚',       'Poverty Alleviation',            'policy_phrase', 'manual'),
  ('乡村振兴',       'Rural Revitalization',           'policy_phrase', 'manual'),
  ('一带一路',       'Belt and Road Initiative',       'diplomatic',    'manual'),
  ('人类命运共同体', 'Community of Shared Future for Mankind', 'diplomatic', 'manual'),
  ('底线思维',       'Bottom-line Thinking',           'ideological',   'manual'),
  ('统筹发展和安全', 'Coordinate Development and Security', 'policy_phrase', 'manual')
ON CONFLICT DO NOTHING;

-- ─────────────────────────────────────
-- Term occurrences per document
-- ─────────────────────────────────────

CREATE TABLE IF NOT EXISTS term_occurrences (
  id               SERIAL PRIMARY KEY,
  term_id          INTEGER NOT NULL REFERENCES terms(id),
  document_id      INTEGER NOT NULL REFERENCES documents(id),
  frequency        INTEGER NOT NULL DEFAULT 0,
  char_positions   INTEGER[],
  context_snippets TEXT[],
  UNIQUE (term_id, document_id)
);

CREATE INDEX IF NOT EXISTS idx_occ_term ON term_occurrences (term_id);
CREATE INDEX IF NOT EXISTS idx_occ_doc  ON term_occurrences (document_id);

-- ─────────────────────────────────────
-- Policy list tracking (priority ordering)
-- ─────────────────────────────────────

CREATE TABLE IF NOT EXISTS list_contexts (
  id           SERIAL PRIMARY KEY,
  document_id  INTEGER NOT NULL REFERENCES documents(id),
  list_name_zh TEXT NOT NULL,
  list_name_en TEXT,
  extracted_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS list_entries (
  id              SERIAL PRIMARY KEY,
  list_context_id INTEGER NOT NULL REFERENCES list_contexts(id),
  term_id         INTEGER REFERENCES terms(id),
  raw_text_zh     TEXT NOT NULL,
  raw_text_en     TEXT,
  position        SMALLINT NOT NULL,
  UNIQUE (list_context_id, position)
);

-- ─────────────────────────────────────
-- Omission tracking
-- ─────────────────────────────────────

CREATE TABLE IF NOT EXISTS term_gaps (
  id               SERIAL PRIMARY KEY,
  term_id          INTEGER NOT NULL REFERENCES terms(id),
  last_seen_doc    INTEGER NOT NULL REFERENCES documents(id),
  last_seen_date   DATE NOT NULL,
  gap_start_date   DATE NOT NULL,
  gap_end_date     DATE,
  gap_length_days  INTEGER,
  meetings_missed  INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_gaps_term ON term_gaps (term_id);
CREATE INDEX IF NOT EXISTS idx_gaps_open ON term_gaps (gap_end_date) WHERE gap_end_date IS NULL;

-- ─────────────────────────────────────
-- Document diffs
-- ─────────────────────────────────────

CREATE TABLE IF NOT EXISTS document_diffs (
  id           SERIAL PRIMARY KEY,
  doc_a_id     INTEGER NOT NULL REFERENCES documents(id),
  doc_b_id     INTEGER NOT NULL REFERENCES documents(id),
  diff_json    JSONB NOT NULL,
  summary_en   TEXT,
  computed_at  TIMESTAMPTZ DEFAULT now(),
  UNIQUE (doc_a_id, doc_b_id)
);
