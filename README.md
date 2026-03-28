# PodStream - Podcast Hosting & Streaming Platform

A production-grade podcast hosting and streaming platform built with Django, Django REST Framework, React, PostgreSQL, Redis, and Celery. PodStream provides everything podcasters need to publish, manage, and grow their shows, and everything listeners need to discover, stream, and enjoy podcasts.

## Features

### For Podcasters
- **Audio Upload & Hosting** - Upload episodes in MP3, WAV, FLAC, OGG, or M4A format with automatic transcoding to optimized MP3
- **RSS Feed Generation** - Standards-compliant RSS 2.0 feeds with iTunes/Apple Podcasts and Spotify namespace extensions
- **Episode Management** - Full CRUD for podcasts, seasons, and episodes with scheduling, drafts, and bulk operations
- **Analytics Dashboard** - Real-time insights into downloads, unique listeners, geographic distribution, listening duration, and retention
- **Monetization** - Ad slot management (pre-roll, mid-roll, post-roll), sponsorship deals, and tip jar for listener support
- **Embed Widget** - Embeddable player widget for external websites

### For Listeners
- **Discovery** - Browse trending podcasts, filter by category/tag, full-text search across titles and descriptions
- **Streaming Player** - Full-featured audio player with playback speed control, skip controls, sleep timer, and queue management
- **Subscriptions** - Subscribe to podcasts, build playlists, and maintain listening history with resume support
- **Reviews & Ratings** - Rate and review podcasts to help the community discover great content

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend API | Django 5.0 + Django REST Framework 3.15 |
| Database | PostgreSQL 16 |
| Cache / Broker | Redis 7 |
| Task Queue | Celery 5.3 |
| Audio Processing | FFmpeg + Pydub |
| Frontend | React 18 + Redux Toolkit |
| HTTP Player | HLS.js for adaptive streaming |
| Reverse Proxy | Nginx |
| Containerization | Docker + Docker Compose |

## Architecture

```
                    +-----------+
    Clients ------> |   Nginx   | (reverse proxy, static/media files)
                    +-----+-----+
                          |
              +-----------+-----------+
              |                       |
        +-----v-----+          +-----v-----+
        |  React SPA |          | Django API |
        |  (port 3000)|         | (port 8000)|
        +------------+          +-----+-----+
                                      |
                        +-------------+-------------+
                        |             |             |
                  +-----v---+  +-----v---+  +------v------+
                  |PostgreSQL|  |  Redis  |  |   Celery    |
                  | (5432)   |  | (6379)  |  |  Workers    |
                  +----------+  +---------+  +-------------+
```

## Getting Started

### Prerequisites
- Docker and Docker Compose installed
- At least 4 GB of RAM available for containers

### Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/podstream.git
   cd podstream
   ```

2. **Copy environment file**
   ```bash
   cp .env.example .env
   ```

3. **Edit `.env`** with your own secrets (especially `SECRET_KEY`, `POSTGRES_PASSWORD`, and any Stripe/payment keys).

4. **Build and start all services**
   ```bash
   docker-compose up --build -d
   ```

5. **Run database migrations**
   ```bash
   docker-compose exec backend python manage.py migrate
   ```

6. **Create a superuser**
   ```bash
   docker-compose exec backend python manage.py createsuperuser
   ```

7. **Seed categories (optional)**
   ```bash
   docker-compose exec backend python manage.py seed_categories
   ```

8. **Access the application**
   - Frontend: http://localhost
   - API: http://localhost/api/
   - Admin: http://localhost/admin/
   - API Docs: http://localhost/api/docs/

### Development Mode

To run the backend and frontend outside Docker for development:

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

**Celery Worker:**
```bash
cd backend
celery -A config worker -l info
```

**Frontend:**
```bash
cd frontend
npm install
npm start
```

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register/` | Register new account |
| POST | `/api/v1/auth/login/` | Obtain JWT token pair |
| POST | `/api/v1/auth/token/refresh/` | Refresh access token |
| GET | `/api/v1/auth/profile/` | Get current user profile |

### Podcasts
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/podcasts/` | List all podcasts |
| POST | `/api/v1/podcasts/` | Create a podcast |
| GET | `/api/v1/podcasts/{slug}/` | Get podcast details |
| GET | `/api/v1/podcasts/{slug}/episodes/` | List episodes |
| POST | `/api/v1/podcasts/{slug}/episodes/` | Create episode |
| GET | `/api/v1/podcasts/{slug}/feed/` | RSS feed (XML) |
| GET | `/api/v1/podcasts/trending/` | Trending podcasts |
| GET | `/api/v1/podcasts/categories/` | Browse categories |

### Player & Subscriptions
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/subscriptions/subscribe/` | Subscribe to podcast |
| GET | `/api/v1/subscriptions/feed/` | Subscription feed |
| GET/POST | `/api/v1/subscriptions/playlists/` | Manage playlists |
| POST | `/api/v1/subscriptions/history/` | Record listening progress |

### Analytics (Podcaster only)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/analytics/overview/` | Dashboard overview |
| GET | `/api/v1/analytics/downloads/` | Download statistics |
| GET | `/api/v1/analytics/listeners/` | Listener demographics |
| GET | `/api/v1/analytics/geography/` | Geographic breakdown |
| GET | `/api/v1/analytics/episodes/{id}/` | Per-episode analytics |

### Monetization
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/api/v1/monetization/ad-slots/` | Manage ad slots |
| GET/POST | `/api/v1/monetization/sponsorships/` | Sponsorship deals |
| POST | `/api/v1/monetization/tips/` | Send tips to podcasters |

## Environment Variables

See `.env.example` for all available configuration options. Key variables:

- `SECRET_KEY` - Django secret key (generate a strong random value)
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `AWS_STORAGE_BUCKET_NAME` - S3 bucket for audio file storage (optional, uses local storage by default)
- `STRIPE_SECRET_KEY` - Stripe API key for payment processing

## Testing

```bash
# Run backend tests
docker-compose exec backend python manage.py test

# Run frontend tests
docker-compose exec frontend npm test
```

## Deployment

For production deployment:

1. Set `DEBUG=False` in `.env`
2. Configure a proper `SECRET_KEY`
3. Set up SSL certificates and update Nginx config
4. Configure an S3-compatible storage backend for audio files
5. Set up proper SMTP for email delivery
6. Configure Sentry or similar for error tracking

## License

MIT License. See LICENSE file for details.
