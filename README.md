# 🌊 DarfFlow - EFD-Reinf API

> **Automated EFD-Reinf Event Processing**: Convert spreadsheets to XML, digitally sign, and transmit to the Brazilian Federal Revenue.

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/Flask-3.0+-green.svg)](https://flask.palletsprojects.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**DarfFlow** is a complete solution for automating EFD-Reinf event submissions through XLSX to XML conversion, digital signature, and transmission to Receita Federal.

---

## ✨ Features

- 📊 **Spreadsheet Processing** - Convert XLSX spreadsheets to EFD-Reinf XML events
- ✍️ **Digital Signature** - Sign XMLs with ICP-Brasil certificates (A1/A3)
- 📤 **Automatic Submission** - Send signed events to Receita Federal
- 🔐 **JWT Authentication** - Secure API access with token-based auth
- 📚 **Swagger Documentation** - Interactive API documentation
- 🐳 **Docker Ready** - Easy deployment with Docker Compose
- 🗄️ **PostgreSQL Database** - Robust data persistence
- 📝 **23 Event Types** - Support for all EFD-Reinf events (1000-9015)

---

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- EFD-Reinf Digital Certificate (.pfx or .pem)
- PostgreSQL (included in Docker setup)

### 1. Clone & Configure

```bash
# Clone the repository
git clone <your-repo-url>
cd DarfFlow

# Create environment file
cp .env.example .env

# Edit .env with your settings
nano .env
```

### 2. Configure Environment

Create a `.env` file in the root directory:

```bash
# Database
POSTGRES_DB=darfflow
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_password
DEV_DATABASE_URL=postgresql+psycopg2://postgres:your_secure_password@postgres:5432/darfflow

# Flask
FLASK_ENV=development
SECRET_KEY=your_secret_key_here
DEBUG=True

# API
ENDPOINT_URL=https://pre-reinf.receita.economia.gov.br/recepcao/lotes

# Certificate
CERTIFICATE_PATH=certificate/certificate_final.pem
CERTIFICATE_PASSWORD=

# CORS
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5000
```

### 3. Start Application

```bash
# Build and start containers
docker-compose up --build -d

# View logs
docker-compose logs -f app

# Access the API
open http://localhost:5000/api/docs
```

### 4. Initialize Database

The database is automatically initialized on first run. To manually run migrations:

```bash
# Access container
docker exec -it darfflow-app-1 bash

# Run migrations
alembic upgrade head
```

---

## 📖 Documentation

### Quick Links

- **[API Reference](app/docs/API_REFERENCE.md)** - Complete endpoint documentation
- **[Certificate Usage](app/docs/CERTIFICATE_USAGE.md)** - Digital signature setup
- **[Setup Guide](app/docs/SETUP.md)** - Detailed installation instructions
- **[Data Models](app/docs/MODELS.md)** - Database schema
- **[Workflow](app/docs/WORKFLOW.md)** - Complete processing workflow

### Swagger UI

Interactive API documentation is available at:

```
http://localhost:5000/api/docs
```

---

## 🔑 Authentication

All protected endpoints require a JWT Bearer token:

```bash
# Example request
curl -X GET "http://localhost:5000/api/spreadsheets" \
  -H "Authorization: Bearer your_jwt_token_here"
```

> **Note**: User authentication is currently managed externally. See [Roadmap](#roadmap) for upcoming user management features.

---

## 📋 API Endpoints

### Core Resources

| Resource        | Base Path              | Description                    |
| --------------- | ---------------------- | ------------------------------ |
| Health          | `/api/health`          | Application health check       |
| Spreadsheets    | `/api/spreadsheets`    | Upload and manage spreadsheets |
| Processed Files | `/api/processed-files` | View converted XMLs            |
| Signed Files    | `/api/signed`          | Sign and send XMLs             |

### Workflow

```mermaid
graph LR
    A[Upload Spreadsheet] --> B[Process to XML]
    B --> C[Sign XML]
    C --> D[Send to Receita]
    D --> E[Get Response]
```

### Example: Complete Flow

```bash
# 1. Upload spreadsheet
curl -X POST "http://localhost:5000/api/spreadsheets/upload?company_id=COMPANY001&event=4020" \
  -H "Authorization: Bearer $TOKEN" \
  -F "spreadsheet=@data.xlsx"

# 2. Process spreadsheet
curl -X POST "http://localhost:5000/api/spreadsheets/process?spreadsheet_id=$ID&cnpj=12345678000190" \
  -H "Authorization: Bearer $TOKEN"

# 3. Sign XMLs
curl -X POST "http://localhost:5000/api/signed/sign?spreadsheet_id=$ID&event=4020" \
  -H "Authorization: Bearer $TOKEN"

# 4. Send to Receita Federal
curl -X POST "http://localhost:5000/api/signed/send?spreadsheet_id=$ID&event=4020&company_id=COMPANY001&cnpj=12345678000190&year=2024" \
  -H "Authorization: Bearer $TOKEN"
```

---

## 🛠️ Development

### Project Structure

```
DarfFlow/
├── app/
│   ├── src/
│   │   ├── controllers/       # API endpoints
│   │   ├── models/           # Database models
│   │   ├── service/          # Business logic
│   │   ├── utils/            # Helper functions
│   │   ├── config/           # App configuration
│   │   └── swagger_docs/     # Swagger documentation
│   ├── docs/                 # Documentation
│   ├── alembic/              # Database migrations
│   └── uploads/              # File storage
├── certificate/              # Digital certificates
├── docker-compose.yml
└── Dockerfile
```

### Running Tests

```bash
# Access container
docker exec -it darfflow-app-1 bash

# Run tests
pytest

# With coverage
pytest --cov=src tests/
```

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

---

## 🎯 Supported Events

DarfFlow supports all 23 EFD-Reinf event types:

| Code     | Event Type                                                            |
| -------- | --------------------------------------------------------------------- |
| **1000** | Contributor Information                                               |
| **2010** | Social Security Withholding - Services Taken                          |
| **2020** | Social Security Withholding - Services Provided                       |
| **4020** | Payment to Legal Entity Beneficiary                                   |
| **4040** | Payment to Individual Beneficiary                                     |
| **9000** | Event Deletion                                                        |
| ...      | [See complete list](app/docs/CERTIFICATE_USAGE.md#eventos-suportados) |

---

## 🗺️ Roadmap

### Version 2.0 (Planned)

#### 🔐 User Management System

- **User Registration & Authentication**
  - User sign-up with email verification
  - Password reset and recovery
  - Role-based access control (Admin, User, Viewer)
  - Multi-factor authentication (MFA)

#### 📜 Certificate Management per User

- **Personal Certificate Upload**

  - Each user uploads their own A1/A3 certificate
  - Encrypted certificate storage
  - Certificate expiration warnings
  - Support for multiple certificates per user

- **Certificate Validation**
  - Automatic certificate chain validation
  - ICP-Brasil compliance verification
  - Certificate revocation checking (CRL/OCSP)

#### 🏢 Multi-Company Support

- **Company Management**
  - Users can manage multiple companies
  - Company-specific certificates
  - CNPJ validation and verification
  - Company-level permissions

#### 📊 Enhanced Features

- **XML Editing** - Edit XML data before signing
- **Batch Processing** - Process multiple spreadsheets at once
- **Scheduled Submissions** - Automated event scheduling
- **Response Tracking** - Track submission status and responses
- **Audit Logs** - Complete activity history

### Version 2.1 (Future)

- **Dashboard** - Real-time metrics and analytics
- **Notifications** - Email/SMS alerts for events
- **API Key Management** - Generate and manage API keys
- **Webhook Support** - Real-time event notifications
- **Export Reports** - Generate submission reports

---

## 🐳 Docker Commands

### Basic Operations

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f app

# Rebuild after code changes
docker-compose up --build -d

# Access application shell
docker exec -it darfflow-app-1 bash

# Access database
docker exec -it darfflow-postgres-1 psql -U postgres -d darfflow
```

### Troubleshooting

```bash
# Check container status
docker-compose ps

# View all logs
docker-compose logs

# Restart specific service
docker-compose restart app

# Remove all containers and volumes
docker-compose down -v
```

---

## 🔧 Configuration

### Production Setup

For production deployment:

1. **Update `.env`**:

   ```bash
   FLASK_ENV=production
   DEBUG=False
   ALLOWED_ORIGINS=https://yourdomain.com
   ```

2. **Use Gunicorn** (already configured):

   ```bash
   # Runs automatically in production mode
   gunicorn -c gunicorn.conf.py "src:app"
   ```

3. **Enable HTTPS**:

   - Configure reverse proxy (nginx/Apache)
   - Use SSL certificates (Let's Encrypt)

4. **Secure Certificate Storage**:
   - Use secret managers (AWS Secrets, Azure Key Vault)
   - Never commit `.pfx` files to repository

---

## 🔒 Security

### Best Practices

- ✅ Never commit `.env` files
- ✅ Use strong `SECRET_KEY` in production
- ✅ Store certificates in secure locations
- ✅ Use environment variables for sensitive data
- ✅ Enable HTTPS in production
- ✅ Regular security updates
- ✅ Implement rate limiting
- ✅ Use strong database passwords

### Certificate Security

- Store certificates outside application directory
- Use encrypted certificate storage
- Implement certificate rotation
- Monitor certificate expiration
- Use different certificates for dev/prod

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 🆘 Support

### Common Issues

**Port already in use:**

```bash
# Change port in docker-compose.yml
ports:
  - "5001:5000"  # Use port 5001 instead
```

**Database connection failed:**

```bash
# Check PostgreSQL is running
docker-compose ps

# Restart database
docker-compose restart postgres
```

**Certificate errors:**

- Verify certificate path in `.env`
- Check certificate format (.pfx or .pem)
- See [Certificate Usage Guide](app/docs/CERTIFICATE_USAGE.md)

### Getting Help

- 📖 Check [Documentation](app/docs/)
- 🐛 Report issues on GitHub
- 💬 Contact support team

---

## 🙏 Acknowledgments

- **Receita Federal** - EFD-Reinf specification
- **Python Community** - Flask, SQLAlchemy, signxml
- **Contributors** - All who helped improve this project
