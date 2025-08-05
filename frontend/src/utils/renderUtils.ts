/**
 * Utility functions for safe rendering of potentially problematic values
 */

/**
 * Safely render a value that might be an object, array, or primitive
 */
export const safeRender = (value: any): string => {
  if (value === null || value === undefined) {
    return '';
  }
  
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
    return String(value);
  }
  
  if (typeof value === 'object') {
    try {
      return JSON.stringify(value);
    } catch {
      return '[Object]';
    }
  }
  
  return String(value);
};

/**
 * Safely render a value with a fallback
 */
export const safeRenderWithFallback = (value: any, fallback: string = 'Unknown'): string => {
  if (value === null || value === undefined) {
    return fallback;
  }
  
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
    return String(value);
  }
  
  return fallback;
};

/**
 * Check if a value is safely renderable in React
 */
export const isSafeToRender = (value: any): boolean => {
  return (
    value === null ||
    value === undefined ||
    typeof value === 'string' ||
    typeof value === 'number' ||
    typeof value === 'boolean'
  );
};