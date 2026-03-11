# AI News Aggregator - Product Requirements Document

## 1. Overview

Sistema automatizzato di raccolta, filtraggio e distribuzione di notizie relative all'intelligenza artificiale, robotica, vibecoding e tecnologie emergenti.

**Target:** Utenti italiani interessati a AI/tech (canale Telegram primario, EN optional)

**Value Proposition:**
- Cura manuale delle fonti migliori
- Riassunti in italiano intelligente
- No spam: solo notizie rilevanti
- Delivery tempestivo (2-3x/giorno)

---

## 2. Functional Requirements

### Core Features

| ID | Feature | Priority | Description |
|----|---------|----------|-------------|
| F1 | Multi-source aggregation | P0 | Colleziona da RSS, HN, Reddit, dev.to, arXiv, GitHub |
| F2 | Smart deduplication | P0 | Evita duplicati per URL + titolo normalizzato |
| F3 | AI categorization | P0 | Tagga: AI-general, robotics, vibecoding, Openclaw, llm, ethics |
| F4 | Italian summarization | P0 | Riassunto 2-3 righe in IT via LLM (GLM4.7) |
| F5 | Telegram delivery | P0 | Push a canale configurato con formattazione Markdown |
| F6 | Bilingual support | P1 | `--lang=it|en` per multi-canale |
| F7 | Manual curation UI | P2 | Web UI per approve/reject prima di pubblicazione |
| F8 | Analytics | P2 | Track: click, reactions, most-read sources |

### Content Sources (Phase 1)

```yaml
sources:
  hackernews:
    endpoint: https://hn.algolia.com/api/v1/search
    query: "AI OR artificial intelligence OR LLM OR ChatGPT"
    frequency: 3h
    max_items: 10

  reddit:
    subreddits:
      - artificial
      - MachineLearning
      - ChatGPT
      - OpenAI
      - robotics
    filter: top/week
    frequency: 6h

  devto:
    tags: [ai, machinelearning, robotics, vibe-coding]
    frequency: 6h

  arxiv:
    categories: [cs.AI, cs.CL, cs.CV, cs.RO]
    recency: last_3_days
    frequency: 12h

  github_trending:
    query: "artificial intelligence OR llm OR agent"
    frequency: 24h
```

---

## 3. Non-Functional Requirements

| NFR | Requirement | Target |
|-----|-------------|--------|
| Performance | Full cycle scrape→deliver | < 5 min |
| Reliability | Uptime delivery | > 99% |
| Cost | LLM calls/day | < 1000 (GLM4.7 economico) |
| Scale | Articles/day processed | 50-100 |
| Latency | Telegram delivery | < 10s |

---

## 4. Technical Architecture

### Stack

```
Backend:      Python 3.11 + FastAPI
Scrapers:     aiohttp + feedparser + asyncpraw
Database:     SQLite (embeddable) or Postgres (Docker)
LLM:          OpenRouter (GLM4.7, zhipu) or local Ollama
Task Queue:   APScheduler or Celery
Bot:          python-telegram-bot v20
Deployment:   Docker Compose
```

### Data Flow

```
┌─────────────┐   ┌──────────────┐   ┌─────────────┐   ┌──────────────┐
│   Sources   │──▶│   Fetcher    │──▶│   Filter    │──▶│  Summarizer  │
│  (RSS/API)  │   │  (async)     │   │ (dedup/AI)  │   │   (GLM4.7)   │
└─────────────┘   └──────────────┘   └─────────────┘   └──────────────┘
                                                              │
                                                              ▼
┌─────────────┐   ┌──────────────┐                   ┌──────────────┐
│   Telegram  │◀──│   Queue      │◀──────────────────│    Store     │
│   Channel   │   │  (delivery)  │                   │   (SQLite)   │
└─────────────┘   └──────────────┘                   └──────────────┘
```

### Database Schema

```sql
CREATE TABLE articles (
    id TEXT PRIMARY KEY,           -- hash URL
    url TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    summary TEXT,                  -- generated IT
    source TEXT NOT NULL,          -- hackernews|reddit|devto|arxiv|github
    category TEXT,                 -- ai-general|robotics|vibecoding|etc
    published_at TIMESTAMP,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    delivered_at TIMESTAMP,
    telegram_message_id INTEGER,
    status TEXT DEFAULT 'pending', -- pending|approved|rejected|delivered
    click_count INTEGER DEFAULT 0
);

CREATE INDEX idx_status ON articles(status);
CREATE INDEX idx_fetched ON articles(fetched_at);
CREATE INDEX idx_category ON articles(category);
```

---

## 5. API Design

### Internal Endpoints

```yaml
GET  /health                    → {"status": "ok", "version": "1.0.0"}
POST /fetch/manual              → Trigger manual fetch
GET  /articles                  → List articles (filter: status, category, date)
PUT  /articles/{id}/approve     → Manual approve
PUT  /articles/{id}/reject      → Manual reject
POST /telegram/send/{id}      → Send specific article
GET  /stats                     → Daily/weekly stats
```

---

## 6. Telegram Message Format

### Template IT

```
🤖 {category_emoji} {Categoria}

*{titolo_riassunto_it}*

{riassunto_2_3_righe}

🔗 [Leggi originale]({url})

👤 {source} • {data}
```

### Category Emojis

| Categoria | Emoji |
|-----------|-------|
| ai-general | 🤖 |
| robotics | ⚙️ |
| vibecoding | 🎨 |
| openclaw | 🦀 |
| llm/prompt | 💬 |
| ethics | ⚖️ |

---

## 7. Configuration

### Environment Variables

```bash
# Database
DATABASE_URL=sqlite:///data/ainews.db

# LLM (OpenRouter)
LLM_API_KEY=sk-or-v1-...
LLM_MODEL=zhipu/glm-4-7

# Telegram
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
TELEGRAM_CHANNEL_ID=@yourchannel  # or -1001234567890

# Delivery schedule (cron)
FETCH_SCHEDULE=0 */3 * * *      # Every 3 hours
DELIVERY_SCHEDULE=0 8,14,20 * * *  # 8am, 2pm, 8pm

# Features
ENABLE_AUTOMATIC_DELIVERY=false  # Start with manual approval
DEFAULT_LANGUAGE=it
```

---

## 8. Deployment

### Docker Compose

```yaml
version: '3.8'
services:
  api:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
    env_file: .env
    restart: unless-stopped

  scheduler:
    build: .
    command: python -m app.scheduler
    env_file: .env
    restart: unless-stopped

  bot:
    build: .
    command: python -m app.telegram_bot
    env_file: .env
    restart: unless-stopped
```

---

## 9. Phased Development

### Phase 1 — MVP (Week 1)
- [ ] Core scraper: HN + Reddit
- [ ] SQLite storage + dedup
- [ ] GLM4.7 summarization (IT)
- [ ] Telegram bot + delivery
- [ ] Docker deployment
- [ ] Manual approval mode

### Phase 2 — Scale (Week 2)
- [ ] Add sources: dev.to, arXiv, GitHub
- [ ] Auto-delivery mode
- [ ] Category detection
- [ ] Stats dashboard

### Phase 3 — Polish (Week 3-4)
- [ ] Web UI curation
- [ ] Click tracking
- [ ] Multi-channel (IT + EN)
- [ ] Analytics

---

## 10. Success Metrics

| Metric | Target |
|--------|--------|
| Articles delivered/day | 5-15 |
| Duplicate rate | < 10% |
| User engagement | 20%+ reactions |
| Cost/article | < €0.01 |
| System uptime | 99%+ |

---

## Next Steps

1. ✅ This PRD approved
2. 🔄 Scaffholding project + Docker
3. 🔄 Implement core scraper
4. 🔄 Integrate GLM4.7
5. 🔄 Telegram bot setup

**PRD v1.0 - 2026-03-11**
