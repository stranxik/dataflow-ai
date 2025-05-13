# DataFlow AI Frontend

## Overview

The DataFlow AI frontend is a modern and responsive user interface built with React and TypeScript. It provides an intuitive user experience for all the data analysis and processing features offered by our platform.

## Technologies Used

- **React** - Front-end library for building user interfaces
- **TypeScript** - Typed programming language based on JavaScript
- **Tailwind CSS** - Utility-first CSS framework for rapid UI development
- **Shadcn/UI** - Reusable UI components based on Radix UI
- **Vite** - Modern build tool for web applications
- **React Router** - Navigation between different pages
- **React Dropzone** - Drag and drop file upload handling
- **i18n** - Internationalization (French and English)

## Project Structure

```
frontend/
├── public/             # Static files and fonts
├── src/
│   ├── api/            # API services and backend integration
│   ├── components/     # Reusable React components
│   │   ├── layout/     # Layout components (Navbar, Footer)
│   │   └── ui/         # UI components
│   ├── lib/            # Utilities and helper functions
│   ├── pages/          # Page components
│   ├── App.tsx         # Root application component
│   ├── index.css       # Global styles
│   └── main.tsx        # Entry point
├── index.html          # HTML template
├── package.json        # npm dependencies
├── tailwind.config.js  # Tailwind CSS configuration
├── tsconfig.json       # TypeScript configuration
└── vite.config.ts      # Vite configuration
```

## Key Features

- **PDF Processing** - Advanced text and image extraction with GPT-4.1 analysis
- **JSON Processing** - Cleaning, compression, and chunking of JSON files
- **Unified Processing** - JIRA and Confluence integration with automatic matching
- **Responsive Design** - Interface works on all devices
- **Dark/Light Mode** - Theme customization based on user preferences
- **Multilingual** - Complete French and English support

## Installation

1. Make sure you have Node.js installed (v14+ recommended)
2. Clone the repository and navigate to the `frontend` folder
3. Install dependencies:

```bash
npm install
```

4. Start the development server:

```bash
npm run dev
```

5. Open your browser at `http://localhost:5173`

## Production

To build the application for production:

```bash
npm run build
```

The production files will be generated in the `dist/` folder.

## API Integration

The frontend communicates with the FastAPI backend through REST API calls defined in the `src/api/apiService.ts` folder. The API exposes endpoints for all data processing features.

## Customization

The theme and styles can be customized via:
- `tailwind.config.js` - Configuration of main colors and styles
- `src/index.css` - Global styles and CSS variables

## Contributing

To contribute to the frontend development, please follow the established code practices and conventions in the existing codebase. 