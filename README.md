# Content Manager API v2.0.0 🚀

**PRODUCTION READY** - Modern FastAPI + SQLite + AI Backend for intelligent content management with automated web scraping and AI-powered content generation.

## ✅ Production Status

**LATEST UPDATE: 2025-01-10** - All critical bugs fixed, production optimizations added!

### 🛠️ Recent Bug Fixes & Improvements
- ✅ **FIXED**: Scraper service duplication (removed v4, consolidated to main service)
- ✅ **FIXED**: AI model configuration inconsistency (standardized to gemini-2.0-flash-exp)
- ✅ **FIXED**: Frontend-backend platform compatibility (removed Facebook support)
- ✅ **FIXED**: CORS configuration now uses environment-based settings
- ✅ **ADDED**: Production-ready logging and error handling
- ✅ **ADDED**: Enhanced scraping status with detailed metrics
- ✅ **ADDED**: Environment-based production optimizations

## 🚀 Key Features

- **🕘 Otomatik Web Scraping**: Daily automated content extraction (07:00 AM)
- **👆 Swipe-based Content Review**: Tinder-like interface for content evaluation  
- **🤖 Gemini 2.0 AI Integration**: Advanced content generation with Google's latest model
- **📊 Real-time Statistics**: Live dashboard with comprehensive metrics
- **🔄 Multi-platform Support**: YouTube, Instagram, Twitter, RSS feeds, and websites
- **⚡ Intelligent Feed Discovery**: Automatic RSS feed detection from any website URL
- **🎯 Smart Content Filtering**: Quality thresholds and duplicate detection
- **🛡️ Production Ready**: Error handling, logging, rate limiting, performance optimizations

## 📋 Requirements

- Python 3.8+ (3.13 recommended)
- SQLite (included)
- Gemini API Key (Google AI Studio)

## ⚡ Quick Start

### 1. Environment Setup
```bash
git clone <repository-url>
cd content-manager-api
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Configuration
Create `.env` file:
```env
# Required
GEMINI_API_KEY=your_gemini_api_key_here

# Production (optional)
PRODUCTION=false
LOG_LEVEL=INFO
```

### 3. Run
```bash
# Development
python main.py

# Production
PRODUCTION=true python main.py
```

## 🌐 Production Deployment

### Docker Deployment (Recommended)

```dockerfile
FROM python:3.13-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p data

# Production environment
ENV PRODUCTION=true
ENV LOG_LEVEL=WARNING
ENV GEMINI_API_KEY=${GEMINI_API_KEY}

EXPOSE 8000
CMD ["python", "main.py"]
```

### Environment Variables

```bash
# Production Settings
PRODUCTION=true                    # Enables production optimizations
LOG_LEVEL=WARNING                  # Reduces log verbosity
GEMINI_API_KEY=your_key_here      # Required for AI features

# Database (optional)
DATABASE_URL=sqlite+aiosqlite:///./data/content_manager.db

# CORS (optional - for custom domains)
CORS_ORIGINS=["https://yourdomain.com","https://app.yourdomain.com"]
```

### Production Optimizations

When `PRODUCTION=true`:
- ✅ API documentation disabled (`/docs`, `/redoc`)
- ✅ Debug mode disabled
- ✅ Enhanced error handling (no sensitive data exposure)
- ✅ File logging enabled (`app.log`)
- ✅ Multiple workers (4 vs 1)
- ✅ Access logs disabled for performance
- ✅ Auto-reload disabled

## 📡 API Documentation

### Core Endpoints
- `GET /` - API health and feature info
- `GET /health` - Database connectivity check
- `GET /docs` - Swagger UI (development only)

### Content Management
- `GET /api/topics/` - List topics with filters
- `GET /api/topics/pending` - Swipe interface content
- `POST /api/topics/{id}/like` - Like content
- `POST /api/topics/{id}/dislike` - Dislike content

### Source Management  
- `GET /api/sources/` - List scraping sources
- `POST /api/sources/` - Add source (auto-detects platform)
- `DELETE /api/sources/{id}` - Remove source

### AI Content Generation
- `POST /api/ai/generate` - Generate content from liked topics
- `GET /api/ai/` - List generated content
- `GET /api/ai/{id}/export/word` - Export as Word document

### System Operations
- `POST /api/scrape/trigger` - Manual scraping
- `GET /api/scrape/status` - Detailed scraping metrics
- `GET /api/stats/` - System statistics

## 🔧 Supported Platforms

| Platform | Status | Features |
|----------|--------|----------|
| YouTube | ✅ Full Support | RSS feeds, metadata extraction |
| Instagram | ✅ Full Support | Profile scraping via instaloader |
| Twitter/X | ⚠️ Limited | Basic profile content (API restrictions) |
| RSS/Atom | ✅ Full Support | Auto-discovery, feed parsing |
| Websites | ✅ Full Support | Content extraction, RSS discovery |

## 🛡️ Security & Performance

### Rate Limiting (per minute)
- YouTube: 60 requests
- Instagram: 20 requests  
- Twitter: 30 requests
- RSS: 120 requests
- Websites: 90 requests

### Data Quality
- Minimum title length: 10 characters
- Minimum content length: 50 characters
- Duplicate detection using content hashing
- Quality score calculation based on engagement

## 🔑 AI Configuration

**Supported Models:**
- `gemini-2.0-flash-exp` (Default - fastest, most advanced)
- `gemini-1.5-pro` (Balanced performance)
- `gemini-1.5-flash` (Fast processing)

Get your API key: [Google AI Studio](https://makersuite.google.com/app/apikey)

## 🐛 Troubleshooting

### Common Issues

**1. Import Errors**
```bash
pip install --upgrade -r requirements.txt
```

**2. Database Issues**
```bash
# Delete and recreate database
rm -rf data/
python main.py
```

**3. Scraping Failures**
- Check internet connection
- Verify source URLs are accessible
- Review rate limiting settings
- Check logs for detailed error messages

### Production Monitoring

Check application health:
```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/scrape/status
```

Monitor logs:
```bash
tail -f app.log
```

## 📞 Support

- Check `/health` endpoint for system status
- Review logs in `app.log` (production) or console (development)
- Monitor scraping status via `/api/scrape/status`
- Use `/docs` for API exploration (development only)

---

**Version**: 2.0.0 | **Status**: Production Ready ✅ | **Last Updated**: 2025-01-10
