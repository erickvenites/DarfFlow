# 📚 DarfFlow Documentation Index

Welcome to the DarfFlow documentation! This index will guide you to the appropriate documentation based on your needs.

---

## 🎯 Quick Navigation

### For Developers
- **[API Reference](API_REFERENCE.md)** - Complete endpoint documentation with examples
- **[Data Models](MODELS.md)** - Database schema and model definitions
- **[Certificate Usage](CERTIFICATE_USAGE.md)** - Digital signature implementation guide

### For Users
- **[Workflow Guide](WORKFLOW.md)** - Step-by-step process from spreadsheet to submission
- **[Setup Guide](SETUP.md)** - Installation and configuration instructions

---

## 📖 Documentation Files

### 1. API Reference
**File:** [API_REFERENCE.md](API_REFERENCE.md)

Complete documentation of all API endpoints including:
- Authentication
- Request/response examples
- Query parameters
- Error codes
- Use cases

**Who should read this:** Developers integrating with the API, frontend developers, API consumers

---

### 2. Certificate Usage Guide
**File:** [CERTIFICATE_USAGE.md](CERTIFICATE_USAGE.md)

Comprehensive guide for digital certificate management:
- Certificate formats (.pfx, .pem, .p12)
- Configuration steps
- Security best practices
- Troubleshooting certificate errors
- Conversion between formats

**Who should read this:** System administrators, DevOps engineers, developers implementing signature features

---

### 3. Data Models
**File:** [MODELS.md](MODELS.md)

Database schema documentation:
- Entity-Relationship diagrams
- Table structures
- Field descriptions
- Relationships
- Indexes

**Who should read this:** Backend developers, database administrators, data analysts

---

### 4. Workflow Guide
**File:** [WORKFLOW.md](WORKFLOW.md)

End-to-end process documentation:
- Upload spreadsheets
- Process to XML
- Sign XMLs
- Submit to Receita Federal
- Handle responses

**Who should read this:** End users, business analysts, project managers

---

### 5. Setup Guide
**File:** [SETUP.md](SETUP.md)

Installation and deployment guide:
- System requirements
- Docker setup
- Environment configuration
- Database initialization
- Production deployment

**Who should read this:** System administrators, DevOps engineers, new developers

---

## 🚀 Getting Started

### First Time Here?

1. **Understand the workflow** → Read [WORKFLOW.md](WORKFLOW.md)
2. **Install the application** → Follow [SETUP.md](SETUP.md)
3. **Configure certificates** → See [CERTIFICATE_USAGE.md](CERTIFICATE_USAGE.md)
4. **Test the API** → Use [API_REFERENCE.md](API_REFERENCE.md)

### Already Using DarfFlow?

- **Need API details?** → [API_REFERENCE.md](API_REFERENCE.md)
- **Certificate issues?** → [CERTIFICATE_USAGE.md](CERTIFICATE_USAGE.md)
- **Database questions?** → [MODELS.md](MODELS.md)
- **Process clarification?** → [WORKFLOW.md](WORKFLOW.md)

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                      DARFFLOW API                        │
└─────────────────────────────────────────────────────────┘

┌──────────┐      ┌──────────┐      ┌──────────┐
│  Client  │ ───> │  Flask   │ ───> │PostgreSQL│
│(Frontend)│ <─── │  (API)   │ <─── │ Database │
└──────────┘      └──────────┘      └──────────┘
                       │
                       │ HTTPS
                       ▼
                ┌──────────┐
                │ EFD-Reinf│
                │Endpoint  │
                └──────────┘

File Storage Structure:
company_id/
  └── event/
      └── year/
          ├── original.xlsx
          ├── converted/
          │   └── *.xml
          ├── signed/
          │   └── *.xml (signed)
          └── responses/
              └── *.xml
```

---

## 🔗 External Resources

### Official Documentation
- **[EFD-Reinf Manual](http://sped.rfb.gov.br/pagina/show/2587)** - Receita Federal official docs
- **[Swagger UI](http://localhost:5000/api/docs)** - Interactive API docs (when running)

### Specifications
- **[XML Digital Signature](https://www.w3.org/TR/xmldsig-core/)** - XML-DSig W3C spec
- **[ICP-Brasil](https://www.gov.br/iti/pt-br)** - Brazilian PKI infrastructure

---

## 🆘 Need Help?

If you can't find what you're looking for:

1. **Check the [Troubleshooting](#)** section in relevant docs
2. **Search the documentation** using your editor's search feature
3. **Review the [main README](../../README.md)** for overview information
4. **Check the Swagger UI** at http://localhost:5000/api/docs for live API testing
5. **Contact support** or open an issue on the project repository

---

**Last updated:** 2025-11-23 | **Version:** 1.0
