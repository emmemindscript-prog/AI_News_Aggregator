# 🤖 AI News Aggregator

Sistema automatizzato di raccolta e delivery di notizie AI via Telegram. Preleva da HackerNews, Reddit e altre fonti, riassume in italiano con LLM (GLM4.7), e pubblica sul canale Telegram.

## 🎯 Cosa fa

1. **Fetch**: Raccoglie notizie da fonti AI/tech
2. **Categorizza**: Identifica il topic (LLM, robotics, ethics, etc.)
3. **Riassume**: Genera riassunto italiano con GLM4.7
4. **Deliver**: Pubblica su Telegram in formato leggibile
5. **Schedule**: Funziona automaticamente ogni X minuti

## 📦 Installazione

### Requisiti
- Python 3.10+
- Docker (opzionale)

### Setup

```bash
# 1. Clona il repository
git clone <repo-url>
cd ai-news-aggregator

# 2. Ambiente virtuale
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# oppure: venv\Scripts\activate  # Windows

# 3. Installa dipendenze
pip install -r requirements.txt

# 4. Configura variabili
# Copia .env.example e modifica
cp .env.example .env
# Modifica .env con i tuoi token

# 5. Inizializza database
python -c "from app.models.database import init_database; init_database()"

# 6. Avvia server
python -m uvicorn app.main:app --reload
```

## ⚙️ Configurazione (.env)

```bash
# App
APP_NAME="AI News Aggregator"
DEFAULT_LANGUAGE=it

# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token_here
CHAT_ID=your_channel_id

# OpenRouter (GLM4.7)
OPENROUTER_API_KEY=your_key_here
LLM_MODEL=moonshotai/kimi-k2.5

# Reddit (opzionale)
REDDIT_CLIENT_ID=your_reddit_client
REDDIT_CLIENT_SECRET=your_reddit_secret
REDDIT_USER_AGENT=your_user_agent

# Intervalli
FETCH_INTERVAL_MINUTES=120
DELIVERY_INTERVAL_MINUTES=360
```

## 🚀 Utilizzo

### Modalità Server (API + Scheduler)
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```
Endpoint disponibili:
- `POST /fetch/trigger` — Avvia fetch manuale
- `GET /articles` — Lista articoli
- `POST /deliver/batch` — Invia articoli approvati a Telegram
- `GET /stats` — Statistiche sistema

### Modalità Command Line
```bash
# Fetch singolo
python -m app.scheduler fetch

# Delivery manuale  
python -m app.scheduler deliver

# Ciclo completo (fetch + deliver)
python -m app.scheduler full

# Background scheduler
python -m app.scheduler
```

### Docker
```bash
# Build e run
docker-compose up -d

# Logs
docker-compose logs -f
```

## 📱 Telegram Setup

1. Crea bot con @BotFather
2. Ottieni token: `/newbot` → nome → copia token
3. Aggiungi bot al canale come admin
4. Ottieni chat ID: invia messaggio, poi `https://api.telegram.org/bot<token>/getUpdates`

## 🔧 API Endpoints

| Endpoint | Metodo | Descrizione |
|----------|--------|-------------|
| `/` | GET | Info sistema |
| `/health` | GET | Health check |
| `/config` | GET | Configurazione (safe) |
| `/fetch/trigger` | POST | Avvia fetch |
| `/articles` | GET | Lista articoli |
| `/articles/{id}/approve` | POST | Approva articolo |
| `/articles/{id}/reject` | POST | Rifiuta articolo |
| `/deliver/batch` | POST | Invia batch a Telegram |
| `/telegram/test` | POST | Test messaggio Telegram |
| `/stats` | GET | Statistiche |

## 🏗️ Architettura

```
src/app/
├── core/
│   └── config.py       # Configurazione
├── models/
│   └── database.py     # Database SQLAlchemy
├── services/
│   ├── fetcher.py      # HN, Reddit fetchers
│   ├── aggregator.py   # Orchestratore
│   ├── summarizer.py   # LLM summarization
│   ├── categorizer.py  # AI categorization
│   └── telegram.py     # Telegram delivery
├── main.py             # FastAPI app
└── scheduler.py        # Background jobs
```

## 🔄 Flusso di lavoro

```
┌─────────┐    ┌──────────┐    ┌───────────┐    ┌──────────┐
│ Sources │───▶│ Fetcher  │───▶│ Categorize│───▶│ Summarize│
│(HN, etc)│    │ (async)  │    │  (LLM)    │    │  (GLM)   │
└─────────┘    └──────────┘    └───────────┘    └────┬─────┘
                                                      │
┌─────────┐    ┌──────────┐    ┌───────────┐         │
│Telegram │◄───│  Deliver │◄───│  Approve  │◄────────┘
│ Channel │    │  (bot)   │    │  (manual) │
└─────────┘    └──────────┘    └───────────┘
```

## 💰 Costi

- **GLM4.7 via OpenRouter**: ~0.002$/1M tokens (riassunto = ~500 tokens)
- **Stima**: ~0.10$/mese per 2 fetch/giorno

## 🛠️ Troubleshooting

**Errore "No articles found"**
- Verifica fonti abilitate in .env
- Controlla rate limiting Reddit

**Telegram non invia**
- Verifica bot è admin nel canale
- Controlla chat ID corretto

**LLM fallback troppo spesso**
- Verifica OPENROUTER_API_KEY
- Controlla quota disponibile

## 📋 Categorie

| Emoji | Categoria | Keywords |
|-------|-----------|----------|
| 🤖 | ai-general | AI generico |
| 💬 | llm | GPT, Claude, LLM |
| 🎨 | vibecoding | AI coding |
| ⚙️ | robotics | Robotica |
| ⚖️ | ethics | Etica AI |
| 🦀 | openclaw | OpenClaw |
| 📄 | research | Paper, ricerca |

## 📝 License

MIT License — uso libero, contributi welcome!

---

*Creato con ❤️ da Emme per Egix*