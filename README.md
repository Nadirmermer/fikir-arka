# Content Manager API v2.0.0

Modern FastAPI + SQLite + AI Backend for intelligent content management with automated web scraping and AI-powered content generation.

## 🚀 Features

- **🕘 Otomatik Web Scraping**: Daily automated content extraction (07:00 AM)
- **👆 Swipe-based Content Review**: Tinder-like interface for content evaluation
- **🤖 Gemini 2.5 AI Integration**: Advanced content generation with Google's latest model
- **📊 Real-time Statistics**: Live dashboard with comprehensive metrics
- **🔄 Multi-platform Support**: YouTube, Instagram, Twitter, RSS feeds, and websites
- **⚡ Intelligent Feed Discovery**: Automatic RSS feed detection from any website URL
- **🎯 Smart Content Filtering**: Quality thresholds and duplicate detection
- **📄 Word Export**: Generate downloadable Word documents from AI content

## 📋 Requirements

- Python 3.8+ (3.13 recommended)
- SQLite (included)
- Gemini API Key (Google AI Studio)

## 🆕 Recent Updates (2025)

- **Updated Dependencies**: All packages updated to latest stable versions
- **Enhanced Scraping**: Replaced deprecated scrapling with requests + BeautifulSoup
- **Modern Feed Discovery**: Improved RSS feed detection using feedparser
- **Latest yt-dlp**: Updated to 2025.6.30 for YouTube content
- **Security Updates**: requests 2.32.3 with latest security patches
- **Performance Improvements**: FastAPI 0.115.6 and uvicorn 0.35.0

## 🛠️ Installation

### 1. Clone and Setup Environment

```bash
git clone <repository-url>
cd content-manager-api
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Environment Configuration

Create `.env` file in the project root:

```env
# Database
DATABASE_URL=sqlite+aiosqlite:///./content_manager.db
DB_ECHO=false

# AI Configuration
GEMINI_API_KEY=your_gemini_api_key_here

# Scheduler
SCHEDULER_TIMEZONE=Europe/Istanbul
SCRAPE_SCHEDULE_HOUR=7
SCRAPE_SCHEDULE_MINUTE=0

# Development
DEBUG=true
```

**🔑 Getting Gemini API Key:**
1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Copy the key to your `.env` file

### 4. Database Initialization

The database will be automatically created when you first run the application:

```bash
python main.py
```

## 🚀 Running the Application

### Development Server

```bash
# With auto-reload
python main.py

# Or using uvicorn directly
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Production Server

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

## 📡 API Endpoints

### Health & Info
- `GET /` - API information and status
- `GET /health` - Health check with database connectivity
- `GET /docs` - Interactive Swagger UI documentation
- `GET /redoc` - ReDoc documentation

### Topics (Content Management)
- `GET /api/topics/` - List all topics with filtering
- `GET /api/topics/pending` - Get pending topics for swipe interface
- `POST /api/topics/{id}/like` - Mark topic as liked
- `POST /api/topics/{id}/dislike` - Mark topic as disliked
- `POST /api/topics/` - Create manual topic

### Sources (Scraping Sources)
- `GET /api/sources/` - List all content sources
- `POST /api/sources/` - Add new source (auto-detects platform and feeds)
- `DELETE /api/sources/{id}` - Remove source

### AI Content Generation
- `GET /api/ai/` - List generated AI content
- `POST /api/ai/generate` - Generate content from liked topic
- `GET /api/ai/{id}/export/word` - Export content as Word document
- `DELETE /api/ai/{id}` - Delete AI content
- `GET /api/ai/test` - Test AI connection

### Statistics
- `GET /api/stats/` - Get comprehensive system statistics

### Settings & Configuration
- `GET /api/settings/` - Get current settings
- `PUT /api/settings/` - Update settings
- `PUT /api/settings/api-key` - Update Gemini API key
- `GET /api/settings/ai-models` - List available AI models

### Manual Operations
- `POST /api/scrape/trigger` - Manually trigger content scraping

## 🔧 Configuration

### Scraping Settings

The scraper supports multiple platforms with intelligent URL detection:

**Supported Platforms:**
- **YouTube**: Channels, playlists, individual videos (auto-converts to channel feed) - ✅ yt-dlp
- **Instagram**: Profiles (requires instaloader) - ✅ instaloader
- **Twitter/X**: Profiles (using requests + BeautifulSoup) - ⚠️ Limited due to API changes
- **RSS/Atom**: Blog feeds, news sites - ✅ feedparser
- **Websites**: Auto-discovers RSS feeds or scrapes content - ✅ requests + BeautifulSoup

**Rate Limiting (per minute):**
- YouTube: 60 requests
- Instagram: 20 requests  
- Twitter: 30 requests
- RSS: 120 requests
- Websites: 90 requests

### Quality Thresholds

```python
quality_thresholds = {
    'min_title_length': 10,
    'min_content_length': 50,
    'max_title_length': 300,
    'max_content_length': 5000
}
```

### AI Configuration

**Supported Models:**
- `gemini-2.0-flash-exp` (Recommended - fastest and most advanced)
- `gemini-1.5-pro` (Balanced performance)
- `gemini-1.5-flash` (Fast processing)

**Default Settings:**
- Temperature: 0.7
- Max Tokens: 2000

## 📅 Scheduling

### Automatic Scraping

Content is automatically scraped daily at 07:00 AM (configurable). The scheduler:

- Processes all active sources
- Applies rate limiting per platform
- Filters content by quality thresholds
- Detects and skips duplicates
- Provides detailed performance metrics

### Manual Triggering

You can manually trigger scraping via:
- API endpoint: `POST /api/scrape/trigger`
- Admin interface
- Direct scheduler call

## 🧪 Testing

### Test Individual Components

```bash
# Test database connection
curl http://localhost:8000/health

# Test AI service
curl http://localhost:8000/api/ai/test

# Test source analysis
curl -X POST http://localhost:8000/api/sources/ \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

### Development Testing

```bash
# Run with debug logging
export DEBUG=true
python main.py
```

## 📊 Monitoring

### Logs

The application provides structured logging:

```
2024-01-15 07:00:00 - INFO - 🕘 Starting scheduled content scraping...
2024-01-15 07:00:05 - INFO - ✅ YouTube RSS: 3 new videos from 15 processed
2024-01-15 07:00:08 - INFO - ✅ Enhanced scheduled scraping completed: 5 new items from 3/4 sources
2024-01-15 07:00:08 - INFO - 📊 Performance: 75% success rate, 2.5s avg per source
```

### Metrics Available

- Total topics and their status distribution
- Source performance and activity
- AI generation statistics
- Scraping performance metrics
- Real-time system status

## 🚨 Troubleshooting

### Common Issues

**1. Gemini API Errors**
```
Error: API key not configured
Solution: Add GEMINI_API_KEY to .env file
```

**2. Scraping Failures**
```
Error: Scrapling not available
Solution: pip install scrapling
```

**3. YouTube Channel Resolution**
```
Error: yt-dlp not available
Solution: pip install yt-dlp
```

**4. Database Locked**
```
Error: database is locked
Solution: Check if another instance is running
```

### Debug Mode

Enable detailed logging:

```env
DEBUG=true
DB_ECHO=true
```

### Performance Optimization

**For High Volume:**
- Increase worker count: `--workers 4`
- Adjust rate limits in scraper configuration
- Use SQLite WAL mode for concurrent access
- Consider PostgreSQL for production

## 🔒 Security

- API key stored in environment variables
- Content sanitization for XSS prevention
- Rate limiting prevents abuse
- Input validation on all endpoints

## 📚 Dependencies

### Core Dependencies (2025 Updates)
- `fastapi==0.115.6` - Latest modern web framework
- `uvicorn[standard]==0.35.0` - Latest ASGI server with performance improvements
- `sqlalchemy==2.0.36` - Latest database ORM
- `aiosqlite==0.20.0` - Latest async SQLite driver
- `pydantic==2.10.4` - Latest data validation

### Scraping & AI
- `requests==2.32.3` - Latest HTTP client with security patches
- `beautifulsoup4==4.12.3` - Latest HTML parsing
- `lxml==5.3.0` - Fast XML/HTML processing
- `feedparser==6.0.11` - RSS/Atom feed parsing (replaces feedsearch)
- `yt-dlp==2025.6.30` - Latest YouTube metadata extraction
- `python-multipart==0.0.17` - File upload support

### Background Processing
- `apscheduler==3.10.4` - Task scheduling

### Removed/Replaced Dependencies
- ❌ `scrapling==0.2.1` - Replaced with requests + BeautifulSoup for better compatibility
- ❌ `feedsearch==2.0.1` - Replaced with feedparser for better RSS discovery
- ❌ `youtube-dl==2021.12.17` - Completely deprecated, replaced with yt-dlp
- ❌ `openai` - Currently using Gemini, can be added back if needed

## 📄 License

This project is licensed under the MIT License.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📞 Support

For issues and questions:
- Check the logs in debug mode
- Review the API documentation at `/docs`
- Ensure all environment variables are set correctly #   f i k i r - a r k a  
 