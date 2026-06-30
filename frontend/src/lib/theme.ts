export type Theme = 'light' | 'dark';

export function setTheme(theme: Theme) {
  document.documentElement.dataset.theme = theme;
  localStorage.setItem('fincore-theme', theme);
}

export function initTheme() {
  const saved = localStorage.getItem('fincore-theme') as Theme | null;
  const system: Theme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  setTheme(saved ?? system);
}

export function getTheme(): Theme {
  return (document.documentElement.dataset.theme as Theme) ?? 'light';
}

export function toggleTheme() {
  setTheme(getTheme() === 'dark' ? 'light' : 'dark');
}

/** Inline script for <head> — applies theme before first paint to avoid flash. */
export const THEME_SCRIPT = `(function(){
  var t=localStorage.getItem('fincore-theme')||(window.matchMedia('(prefers-color-scheme:dark)').matches?'dark':'light');
  document.documentElement.dataset.theme=t;
})();`;
