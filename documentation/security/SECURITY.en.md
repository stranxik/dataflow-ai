# Project Security

## 🔒 Security Best Practices

This document describes the best practices to follow to avoid leaking sensitive data during development on this project.

### 🚫 Never Commit Sensitive Data

- **API keys** (AWS, OpenAI, etc.)
- **Personal information** (emails, names, etc.)
- **Real test data**
- **Authentication tokens**
- **Login credentials**

### ✅ How to Handle Sensitive Data

1. **Use environment variables**
   - Always store API keys in the `.env` file (never in the code)
   - Never commit the `.env` file

2. **Test data**
   - Only use synthetic or anonymized data
   - Clean real data with `tools/clean_sensitive_data.py` before committing
   - Store large data files in `/files` (excluded from git)

3. **Git Protection**
   - A pre-commit hook is configured to detect potential leaks
   - Never use `--no-verify` unless you are absolutely sure it is safe

### 🧹 Cleaning Sensitive Data

To clean test files:

```bash
# Clean a specific file
python -m tools.clean_sensitive_data path/to/file.json

# Clean a directory
python -m tools.clean_sensitive_data path/to/directory --output path/to/output
```

### 🚨 What to Do in Case of a Leak

1. **Don't panic** – But act quickly
2. **Immediately remove** the sensitive data from Git history
   ```bash
   git filter-branch --force --index-filter "git rm --cached --ignore-unmatch path/to/file" --prune-empty --tag-name-filter cat -- --all
   git push origin --force
   ```
3. **Invalidate** compromised keys or tokens
4. **Inform** the concerned parties

### 📋 Pre-commit Checklist

- [ ] Files do not contain sensitive data
- [ ] `.env` and other local config files are ignored
- [ ] Test files are cleaned or synthetic
- [ ] Large data files are in `/files` or `/results`
- [ ] API keys are referenced via environment variables 