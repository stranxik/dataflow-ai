/**
 * Test pour l'extraction PDF avec l'API
 * Ce fichier permet de tester manuellement que l'API fonctionne correctement
 */

import { processPdf } from './apiService';

/**
 * Fonction de test pour extraire et analyser un PDF
 * @param file Fichier PDF à traiter
 * @returns Un message de statut
 */
export async function testPdfExtraction(file: File): Promise<string> {
  console.log(`Test d'extraction PDF démarré pour: ${file.name} (${file.size} bytes)`);
  
  try {
    // Extraire le PDF avec les différentes options pour vérifier
    console.log('TEST 1: Format JSON');
    const resultJson = await processPdf(file, 'complete', 10, undefined, 'json');
    console.log(`Résultat JSON: ${resultJson.size} bytes, type: ${resultJson.type}`);
    
    console.log('TEST 2: Format ZIP');
    const resultZip = await processPdf(file, 'complete', 10, undefined, 'zip');
    console.log(`Résultat ZIP: ${resultZip.size} bytes, type: ${resultZip.type}`);
    
    // Télécharger le ZIP comme test
    console.log('Création du lien de téléchargement pour le fichier ZIP...');
    const url = URL.createObjectURL(new Blob([resultZip], { type: 'application/zip' }));
    const a = document.createElement('a');
    a.href = url;
    a.download = `${file.name.replace('.pdf', '')}_test_extraction.zip`;
    document.body.appendChild(a);
    a.click();
    
    return `Extraction réussie! Résultat JSON: ${resultJson.size} bytes, ZIP: ${resultZip.size} bytes`;
  } catch (error) {
    console.error('Erreur pendant l\'extraction:', error);
    return `Erreur: ${error instanceof Error ? error.message : 'Erreur inconnue'}`;
  }
}

/**
 * Fonction de test pour extraire uniquement le texte
 * @param file Fichier PDF à traiter
 * @returns Un message de statut
 */
export async function testTextOnlyExtraction(file: File): Promise<string> {
  console.log(`Test d'extraction de texte seulement démarré pour: ${file.name}`);
  
  try {
    const result = await processPdf(file, 'text-only', 0);
    console.log(`Résultat texte uniquement: ${result.size} bytes, type: ${result.type}`);
    return `Extraction de texte réussie! Taille: ${result.size} bytes`;
  } catch (error) {
    console.error('Erreur pendant l\'extraction de texte:', error);
    return `Erreur: ${error instanceof Error ? error.message : 'Erreur inconnue'}`;
  }
}

/**
 * Fonction utilitaire pour télécharger un blob avec un nom de fichier
 * @param url L'URL du blob
 * @param filename Le nom du fichier à télécharger
 */
export function downloadBlob(url: string, filename: string): void {
  const a = document.createElement('a');
  a.href = url;
  a.download = filename || 'download';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 100);
} 