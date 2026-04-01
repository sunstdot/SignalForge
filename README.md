# TokenBurner 🔥

Personal AI learning and experimentation system. Transform idle AI tokens into valuable cognitive growth.

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Input     │────→│  Processing │────→│   Output    │
│  (Sources)  │     │   (AI Pipeline)   │     │ (Briefing)  │
└─────────────┘     └─────────────┘     └─────────────┘
```

## Quick Start

### Prerequisites
- Node.js 20+
- pnpm 8+
- OpenRouter API key

### Installation

```bash
# Install dependencies
pnpm install

# Set up environment
cp .env.example .env
# Edit .env and add your OPENROUTER_API_KEY

# Run collector (fetch and process data)
pnpm collect

# Start web dashboard
pnpm web dev
```

### Configuration

Edit `config/collector.yaml` to customize:
- arXiv categories
- GitHub languages
- RSS subscriptions (see RSS section below)

## Project Structure

```
token-burn/
├── apps/
│   ├── collector/    # Data collection and AI processing service
│   └── web/          # Next.js dashboard
├── packages/
│   ├── shared/       # Shared types and utilities
│   └── ai-client/    # OpenRouter API client
├── config/
│   └── collector.yaml
└── docs/
    └── daily-briefings/
```

## RSS Configuration

TokenBurner supports custom RSS feeds via RSSHub.

### 1. RSSHub Setup

Edit `config/rsshub.yaml`:
```yaml
rsshub:
  instanceUrl: "https://your-rsshub-instance.com"
  accessKey: ""  # Optional
  isSelfHosted: false
```

### 2. Add RSS Subscriptions

Edit `config/collector.yaml` and add to `sources.rss.subscriptions`:

```yaml
subscriptions:
  # Direct RSS feed
  - name: "阮一峰的网络日志"
    type: "direct"
    url: "https://www.ruanyifeng.com/blog/atom.xml"
    category: ["tech", "frontend"]
    fetchInterval: 3600

  # Via RSSHub
  - name: "Twitter User"
    type: "rsshub"
    rsshubRoute: "/twitter/user/username"
    category: ["social"]
    fetchInterval: 1800
```

Enable RSS in collector.yaml:
```yaml
sources:
  rss:
    enabled: true
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENROUTER_API_KEY` | OpenRouter API key | Yes |
| `DATABASE_PATH` | SQLite database path | No (default: ./data/tokenburner.db) |
| `CONFIG_PATH` | Collector config path | No (default: ./config/collector.yaml) |

## License

MIT
