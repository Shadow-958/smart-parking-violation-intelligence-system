# System Architecture

## High-level components

```
┌─────────────┐     ┌──────────────────┐     ┌───────────────────────┐
│   React     │────▶│   FastAPI        │────▶│  PostgreSQL + PostGIS │
│  Frontend   │◀────│   Backend        │◀────│                       │
└─────────────┘     │  (REST + JWT)    │     └───────────────────────┘
                     └────────┬─────────┘
                              │
             ┌────────────────┼─────────────────┐
             ▼                ▼                 ▼
      ┌─────────────┐  ┌─────────────┐   ┌──────────────┐
      │  NLP        │  │  Computer   │   │  ML          │
      │  (spaCy,    │  │  Vision     │   │  Prediction   │
      │  Transformers,│ (YOLOv8)   │   │  (XGBoost /   │
      │  Sentence-  │  │             │   │  Random      │
      │  BERT)      │  │             │   │  Forest)      │
      └─────────────┘  └─────────────┘   └──────────────┘
```

## AI workflow pipeline

Each complaint moves through this pipeline (per the original spec, item 11):

1. **Complaint submission** — citizen portal, mobile app, email, or social media
2. **Text preprocessing** — clean, tokenize, lemmatize, remove stop words
3. **NER** — extract candidate location mentions from free text
4. **Violation classification** — assign one of 5 complaint types with a confidence score
5. **Duplicate detection** — Sentence-BERT embeddings + cosine similarity against recent complaints
6. **Image detection (optional)** — YOLOv8 vehicle detection + illegal-parking heuristic
7. **Geocoding** — resolve the extracted location to lat/lng via Nominatim/OSM
8. **GIS mapping** — store as a PostGIS point, render on the Leaflet map
9. **Hotspot detection** — periodic spatial clustering of approved complaints
10. **ML prediction** — forecast future hotspots, violation probability, enforcement timing, officer deployment
11. **Dashboard** — surface all of the above to city staff
12. **Enforcement recommendation** — actionable suggestions in the Admin Panel

## Why this order

Duplicate detection runs *before* image detection and geocoding so that
expensive CV/geocoding work isn't wasted on a complaint that's about to be
merged into an existing one. Classification confidence and duplicate
status both feed into `Complaint.status`, which gates whether a complaint
counts toward hotspot/ML training data — keeping low-confidence or
duplicate reports from skewing enforcement recommendations.

## Service boundaries

The backend is a single FastAPI app in this delivery, with NLP/CV/ML logic
organized under `ai_models/` and invoked via `app/services/`. If model
inference load grows, `ai_models/computer_vision` (YOLOv8) is the most
likely candidate to split into its own service, since it's GPU-bound and
has very different scaling characteristics than the rest of the API.
