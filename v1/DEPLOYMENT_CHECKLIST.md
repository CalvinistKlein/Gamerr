# ROMarr Deployment Checklist

## System Requirements
- Docker and Docker Compose
- 2GB RAM minimum, 4GB recommended
- 10GB storage for ROMs (expandable)

## Quick Start

### 1. Clone and Configure
```bash
git clone <repository>
cd romarr
cp .env.example .env
# Edit .env with your settings
```

### 2. Docker Deployment
```bash
docker-compose up -d
```

### 3. Access Web Interface
- URL: http://localhost:5000
- Default credentials: none (no authentication by default)

## Configuration

### Environment Variables (.env)
```bash
# Flask Configuration
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///instance/romarr.db

# External Services
PROWLARR_URL=http://localhost:9696
PROWLARR_API_KEY=your-prowlarr-api-key

QBITTORRENT_URL=http://localhost:8080
QBITTORRENT_USERNAME=admin
QBITTORRENT_PASSWORD=adminadmin

# Paths
ROMS_PATH=/data/roms
```

### Volume Mounts
- `/data/roms` - ROM storage directory
- `/data/db` - Database storage (SQLite)
- `/app/config` - Configuration files

## Database Initialization

The container automatically:
1. Creates database schema on first run
2. Initializes default platforms and genres
3. Sets up default settings
4. Can import ROMs from mounted directories

## Health Checks

Container includes health checks:
- HTTP endpoint: `/health`
- Checks database connectivity
- Returns service status

## Backup and Recovery

### Database Backup
```bash
# Backup SQLite database
docker exec romarr-container sqlite3 /data/db/romarr.db ".backup /backup/romarr.db.backup"

# Or copy the file
docker cp romarr-container:/data/db/romarr.db ./backup/
```

### ROMs Backup
```bash
# Backup ROMs directory
tar -czf roms-backup.tar.gz /data/roms
```

## Monitoring

### Logs
```bash
# Container logs
docker-compose logs -f romarr

# Application logs (inside container)
docker exec romarr-container tail -f /app/logs/app.log
```

### Health Status
```bash
curl http://localhost:5000/health
```

## Troubleshooting

### Common Issues

1. **Container won't start**
   ```bash
   docker-compose logs romarr
   # Check for missing dependencies or permissions
   ```

2. **Database initialization fails**
   ```bash
   # Force reinitialization
   docker-compose down -v
   docker-compose up -d
   ```

3. **ROMs not appearing**
   ```bash
   # Check volume mounts
   docker volume ls
   # Ensure ROMs directory has correct permissions
   ```

4. **External service connections fail**
   ```bash
   # Test connections
   python test_connections.py
   ```

## Scaling Considerations

### For Larger Deployments
1. **Switch to PostgreSQL**:
   ```yaml
   # docker-compose.yml
   services:
     postgres:
       image: postgres:15
       environment:
         POSTGRES_DB: romarr
         POSTGRES_USER: romarr
         POSTGRES_PASSWORD: your-password
       volumes:
         - postgres_data:/var/lib/postgresql/data
   
     romarr:
       environment:
         DATABASE_URL: postgresql://romarr:your-password@postgres/romarr
   ```

2. **Add Redis for caching**
3. **Use Nginx for load balancing**

## Maintenance

### Regular Tasks
1. **Backup database weekly**
2. **Update container images monthly**
3. **Monitor disk space for ROMs**
4. **Review logs for errors**

### Updates
```bash
# Pull latest images
docker-compose pull

# Restart with new images
docker-compose up -d
```

## Security Considerations

1. **Change default passwords** in `.env`
2. **Use HTTPS** in production (add reverse proxy)
3. **Restrict network access** to necessary ports only
4. **Regular security updates** for base images

## Performance Tuning

### For Large ROM Collections
1. **Increase database cache**:
   ```sql
   PRAGMA cache_size = -2000;  -- 2MB cache
   ```

2. **Add indexes** for frequently queried columns
3. **Schedule heavy operations** during off-hours

### Container Resources
```yaml
# docker-compose.yml
services:
  romarr:
    deploy:
      resources:
        limits:
          memory: 1G
        reservations:
          memory: 512M
```

## Support

- Check logs in `/app/logs/` inside container
- Health endpoint: `http://localhost:5000/health`
- API documentation: `http://localhost:5000/api/docs` (if enabled)

## Migration from Previous Versions

1. **Backup existing database**
2. **Export ROM metadata** if needed
3. **Follow upgrade instructions** in release notes

---

*Last updated: $(date)*
*ROMarr Version: 1.0.0*