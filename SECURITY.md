# Sécurité du Projet

## 🔒 Bonnes pratiques de sécurité

Ce document décrit les bonnes pratiques à suivre pour éviter la fuite de données sensibles lors du développement sur ce projet.

### 🚫 Ne jamais commiter de données sensibles

- **Clés API** (AWS, OpenAI, etc.)
- **Informations personnelles** (emails, noms, etc.)
- **Données de test réelles**
- **Tokens d'authentification**
- **Identifiants de connexion**

### ✅ Comment manipuler les données sensibles

1. **Utiliser des variables d'environnement**
   - Toujours stocker les clés API dans le fichier `.env` (jamais dans le code)
   - Ne jamais commiter le fichier `.env`

2. **Données de test**
   - Utiliser uniquement des données synthétiques ou anonymisées
   - Nettoyer les données réelles avec `tools/clean_sensitive_data.py` avant de les commiter
   - Stocker les fichiers de données volumineux dans `/files` (exclus du git)

3. **Protection du Git**
   - Un hook pre-commit est configuré pour détecter les fuites potentielles
   - Ne jamais utiliser `--no-verify` sauf si vous êtes absolument certain que c'est sûr

### 🧹 Nettoyage des données sensibles

Pour nettoyer les fichiers de test:

```bash
# Nettoyer un fichier spécifique
python -m tools.clean_sensitive_data path/to/file.json

# Nettoyer un dossier
python -m tools.clean_sensitive_data path/to/directory --output path/to/output
```

### 🚨 Que faire en cas de fuite

1. **Ne paniquez pas** - Mais agissez rapidement
2. **Éliminez immédiatement** la donnée sensible de l'historique Git
   ```bash
   git filter-branch --force --index-filter "git rm --cached --ignore-unmatch path/to/file" --prune-empty --tag-name-filter cat -- --all
   git push origin --force
   ```
3. **Invalidez** les clés ou tokens compromis
4. **Informez** les personnes concernées

### 📋 Checklist avant de commiter

- [ ] Les fichiers ne contiennent pas de données sensibles
- [ ] Les fichiers `.env` et autres fichiers de config locaux sont ignorés
- [ ] Les fichiers de test sont nettoyés ou synthétiques
- [ ] Les fichiers de données volumineux sont dans `/files` ou `/results`
- [ ] Les clés API sont référencées via des variables d'environnement 