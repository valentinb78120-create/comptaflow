# ComptaFlow

SaaS B2B d'OCR automatique de factures pour cabinets comptables français.  
Upload → OCR (Mistral) → Validation humaine → Export EBP / Sage 50.

---

## Stack

| Couche | Techno |
|---|---|
| Backend | Python 3.11, FastAPI, SQLAlchemy async, Alembic |
| OCR | Mistral OCR API (`mistral-ocr-latest`) + fallback Tesseract |
| Queue | Celery + Redis |
| Base de données | PostgreSQL 16 |
| Frontend | React 18, TypeScript, TailwindCSS, TanStack Query/Table |
| Paiement | Stripe (14 jours gratuits, puis 79 €/mois) |
| Dev | Docker Compose |

---

## Démarrage rapide

### 1. Prérequis

- Docker Desktop installé et lancé
- Une clé API Mistral : <https://console.mistral.ai>

### 2. Configuration

```bash
cd backend
cp .env.example .env
# Éditez .env et renseignez MISTRAL_API_KEY (les autres valeurs fonctionnent tel quel en dev)
```

### 3. Lancer tout le projet

```bash
# Depuis la racine ComptaFlow/
docker compose up --build
```

| Service | URL |
|---|---|
| API FastAPI + Swagger | <http://localhost:8000/docs> |
| Frontend React | <http://localhost:5173> |
| PostgreSQL | `localhost:5432` |
| Redis | `localhost:6379` |

### 4. Créer les tables (première fois)

```bash
docker compose exec api alembic upgrade head
```

---

## Développement local sans Docker

### Backend

```bash
cd backend
python -m venv .venv
# Windows :
.venv\Scripts\activate
# macOS/Linux :
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env   # renseignez vos valeurs

# Démarrer PostgreSQL et Redis localement (ou via Docker partiel)
docker compose up db redis -d

alembic upgrade head
uvicorn app.main:app --reload
```

### Celery worker

```bash
# Dans un second terminal (même venv activé)
celery -A app.workers.celery_app worker --loglevel=info
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

---

## Architecture

```
ComptaFlow/
├── backend/
│   ├── app/
│   │   ├── api/routes/       # Endpoints FastAPI
│   │   │   ├── invoices.py   # Upload, GET, PATCH, export
│   │   │   └── cabinets.py   # Gestion cabinets
│   │   ├── core/
│   │   │   ├── config.py     # Settings Pydantic (env vars)
│   │   │   └── database.py   # Engine async + session
│   │   ├── models/
│   │   │   ├── invoice.py    # Invoice + InvoiceStatus enum
│   │   │   ├── line_item.py  # Lignes de facture
│   │   │   └── cabinet.py    # Cabinet comptable (client)
│   │   ├── schemas/          # Pydantic I/O schemas
│   │   ├── services/
│   │   │   ├── mistral_ocr.py    # Appel API + parsing regex
│   │   │   ├── pcg_categorizer.py # Règles mots-clés → compte PCG
│   │   │   └── exporter.py       # CSV EBP / Sage 50
│   │   └── workers/
│   │       └── celery_app.py # Task OCR async
│   ├── alembic/              # Migrations DB
│   └── requirements.txt
└── frontend/
    └── src/
        ├── components/
        │   ├── UploadZone.tsx     # Drag & drop
        │   ├── InvoiceTable.tsx   # Liste avec TanStack Table
        │   ├── InvoiceEditModal.tsx # Correction + export
        │   └── StatusBadge.tsx
        ├── pages/Dashboard.tsx    # Page principale
        ├── lib/
        │   ├── api.ts            # Client Axios
        │   └── utils.ts          # Formatage, constantes
        └── types/invoice.ts      # Types TypeScript
```

---

## API — Endpoints principaux

| Méthode | URL | Description |
|---|---|---|
| `POST` | `/api/v1/invoices/upload` | Upload fichier + lance OCR |
| `GET` | `/api/v1/invoices/?cabinet_id=...` | Liste des factures |
| `GET` | `/api/v1/invoices/{id}` | Détail + statut OCR |
| `PATCH` | `/api/v1/invoices/{id}` | Correction manuelle |
| `POST` | `/api/v1/invoices/{id}/export?format=ebp` | Export CSV EBP |
| `POST` | `/api/v1/invoices/{id}/export?format=sage50` | Export CSV Sage 50 |
| `POST` | `/api/v1/invoices/export/bulk?cabinet_id=...` | Export global |
| `GET` | `/health` | Liveness probe |

Swagger interactif disponible sur `/docs`.

---

## Pipeline OCR

```
Upload fichier
     ↓
Sauvegarde disk + record DB (status: pending)
     ↓
Celery task (async)
     ↓
Mistral OCR API → texte markdown
     ↓
Parsing regex → fournisseur, date, HT/TVA/TTC, n° facture
     ↓
PCG categorizer (règles mots-clés)
     ↓
Calcul confiance (0–1)
     ↓
status: validated (≥70%) | needs_review (<70%)
     ↓
Interface de validation → corrections éventuelles
     ↓
Export CSV EBP ou Sage 50
```

---

## Catégorisation PCG

Le fichier [`backend/app/services/pcg_categorizer.py`](backend/app/services/pcg_categorizer.py) contient ~25 règles couvrant :

- Énergie (606100), Télécom (626000), Loyers (613000)
- Assurances (616000), Fournitures (606400), Carburant (606110)
- Transport SNCF/avion (625100), Restauration (625700)
- Informatique logiciels (618500), Honoraires (622000)
- Publicité (623100), Frais bancaires (627000)…

Extensible : ajouter une `PCGRule` dans la liste `DEFAULT_RULES`.

---

## Variables d'environnement

| Variable | Description | Défaut dev |
|---|---|---|
| `DATABASE_URL` | URL PostgreSQL async | `postgresql+asyncpg://compta:compta@localhost:5432/comptaflow` |
| `REDIS_URL` | URL Redis | `redis://localhost:6379/0` |
| `MISTRAL_API_KEY` | **Obligatoire** pour l'OCR | — |
| `STRIPE_SECRET_KEY` | Paiements Stripe | — |
| `UPLOAD_DIR` | Répertoire stockage fichiers | `/tmp/comptaflow/uploads` |
| `MAX_UPLOAD_SIZE_MB` | Taille max upload | `20` |
| `DEBUG` | Mode debug SQLAlchemy | `false` |

---

## Roadmap V2

- Auth JWT multi-utilisateurs par cabinet
- Tableau de bord analytique (dépenses par compte PCG)
- Intégration API directe EBP / Sage (webhook)
- Règles PCG personnalisées par cabinet (interface admin)
- OCR avec structured output Mistral pour meilleure précision
