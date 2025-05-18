# Migrations & Scalabilité - DataFlow AI

> Ce document détaille la stratégie de migration et de scalabilité (MinIO, Temporal, Supabase) pour DataFlow AI.

## 1. Architecture actuelle

- **Backend FastAPI** : Orchestration des jobs d'extraction PDF (upload, extraction, rasterisation, analyse IA, génération de rapports)
- **Stockage objet MinIO** : Tous les fichiers (PDF, résultats, logs, progress.json) sont stockés dans un bucket S3-compatible, local ou cloud
- **Abstraction FileStorage** : Toute la logique d'accès au stockage passe par un service Python unique (`FileStorage`), qui permet de swapper facilement de backend (local, MinIO, Supabase, S3...)
- **Feedback de progression** : Chaque job écrit un fichier `progress.json` mis à jour à chaque étape clé (init, extraction, raster, upload, clean, success/failed), consultable par le frontend
- **Nettoyage automatique** : Après upload dans MinIO, les fichiers locaux sont supprimés pour éviter la saturation disque

## 2. Choix techniques & anticipation de la migration

- **Pourquoi MinIO ?**
  - Déploiement rapide, zéro dépendance externe, parfait pour dev/test/local
  - S3-compatible : la logique d'accès est la même qu'en prod (AWS S3, Supabase Storage...)
  - Permet de valider toute la chaîne (upload, download, clean, feedback) sans coût cloud

- **Préparation à Temporal**
  - Toute la logique métier est factorisée dans des fonctions/services purs (pas de dépendance à l'orchestrateur)
  - L'orchestration (gestion des jobs, retries, monitoring) est séparée de la logique métier
  - Les endpoints API ne font que déclencher des jobs, pas de logique métier lourde
  - Les accès fichiers sont abstraits : Temporal pourra piloter les workers sans changer le code métier

- **Préparation à Supabase Storage**
  - L'abstraction FileStorage permet d'implémenter un backend Supabase (API REST ou S3-compatible) sans toucher au reste du code
  - L'auth, la gestion fine des droits, et l'intégration frontend seront gérés par Supabase en prod

## 3. Migration vers Temporal & Supabase : étapes

- **Temporal**
  1. Déployer un cluster Temporal (ou utiliser Temporal Cloud)
  2. Implémenter des workflows/activities qui appellent les fonctions métiers existantes (extraction, raster, upload...)
  3. Adapter l'API pour déclencher des workflows Temporal au lieu de lancer les jobs en local
  4. Garder la même interface de stockage (FileStorage)

- **Supabase Storage**
  1. Créer un backend Python pour FileStorage utilisant l'API REST ou S3 de Supabase
  2. Changer la config/env pour pointer vers Supabase
  3. L'auth et la gestion des droits sont gérées côté Supabase (JWT, ACL, etc.)

## 4. Points d'attention pour la prod

- Toujours uploader le progress.json dans le backend de stockage avant de supprimer les fichiers locaux
- Ne jamais exposer MinIO sans reverse proxy/auth en prod (préférer Supabase ou S3)
- Monitorer la RAM/CPU si plusieurs jobs lourds en parallèle
- Prévoir un bucket par environnement (dev, staging, prod)

## 5. Schéma de workflow (texte)

1. L'utilisateur upload un PDF via le frontend
2. L'API sauvegarde le PDF dans le backend de stockage (MinIO ou autre)
3. L'API déclenche un job d'extraction (classique + raster)
4. Chaque étape du job met à jour le progress.json (init, extraction, raster, upload, clean, success/failed)
5. Les résultats (JSON, ZIP, rapports) sont uploadés dans le backend de stockage
6. Les fichiers locaux sont nettoyés
7. Le frontend interroge l'API pour suivre la progression et récupérer les résultats

---

**Ce document est à jour avec la logique actuelle et anticipe la migration vers Temporal et Supabase.**
Pour toute question ou adaptation, voir le service `FileStorage` et la config `.env`. 