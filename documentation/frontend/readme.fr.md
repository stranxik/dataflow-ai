# Frontend DataFlow AI

## Présentation

Le frontend de DataFlow AI est une interface utilisateur moderne et réactive construite avec React et TypeScript. Il offre une expérience utilisateur intuitive pour l'ensemble des fonctionnalités d'analyse et de traitement de données proposées par notre plateforme.

## Technologies utilisées

- **React** - Bibliothèque front-end pour la construction d'interfaces utilisateur
- **TypeScript** - Langage de programmation typé basé sur JavaScript
- **Tailwind CSS** - Framework CSS utilitaire pour un design rapide et responsif
- **Shadcn/UI** - Composants UI réutilisables basés sur Radix UI
- **Vite** - Outil de build moderne pour les applications web
- **React Router** - Navigation entre les différentes pages
- **React Dropzone** - Gestion des téléchargements de fichiers par glisser-déposer
- **i18n** - Internationalisation (français et anglais)

## Structure du projet

```
frontend/
├── public/             # Fichiers statiques et fonts
├── src/
│   ├── api/            # Services API et intégration backend
│   ├── components/     # Composants React réutilisables
│   │   ├── layout/     # Composants de mise en page (Navbar, Footer)
│   │   └── ui/         # Composants d'interface utilisateur
│   ├── lib/            # Utilitaires et fonctions helpers
│   ├── pages/          # Composants de page
│   ├── App.tsx         # Composant racine de l'application
│   ├── index.css       # Styles globaux
│   └── main.tsx        # Point d'entrée
├── index.html          # Template HTML
├── package.json        # Dépendances npm
├── tailwind.config.js  # Configuration de Tailwind CSS
├── tsconfig.json       # Configuration TypeScript
└── vite.config.ts      # Configuration de Vite
```

## Fonctionnalités principales

- **Traitement de PDF** - Extraction avancée de texte et d'images avec analyse GPT-4.1
- **Traitement JSON** - Nettoyage, compression et découpage de fichiers JSON
- **Traitement Unifié** - Intégration JIRA et Confluence avec correspondance automatique
- **Design adaptable** - Interface responsive fonctionnant sur tous les appareils
- **Mode sombre/clair** - Thème personnalisable selon les préférences de l'utilisateur
- **Multilingue** - Support complet français et anglais

## Installation

1. Assurez-vous d'avoir Node.js installé (v14+ recommandé)
2. Clonez le dépôt et naviguez dans le dossier `frontend`
3. Installez les dépendances :

```bash
npm install
```

4. Lancez le serveur de développement :

```bash
npm run dev
```

5. Ouvrez votre navigateur sur `http://localhost:5173`

## Production

Pour construire l'application pour la production :

```bash
npm run build
```

Les fichiers de production seront générés dans le dossier `dist/`.

## Intégration avec l'API

Le frontend communique avec le backend FastAPI via des appels API REST définis dans le dossier `src/api/apiService.ts`. L'API expose des endpoints pour toutes les fonctionnalités de traitement de données.

## Personnalisation

Le thème et les styles peuvent être personnalisés via:
- `tailwind.config.js` - Configuration des couleurs et styles principaux
- `src/index.css` - Styles globaux et variables CSS

## Contribuer

Pour contribuer au développement du frontend, veuillez suivre les pratiques et conventions de code établies dans la base de code existante. 