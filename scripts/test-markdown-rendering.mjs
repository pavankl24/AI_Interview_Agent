import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { createServer } from 'vite';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const vite = await createServer({
  configFile: path.join(root, 'vite.config.ts'),
  server: { middlewareMode: true },
  appType: 'custom',
  logLevel: 'error',
});

try {
  const { default: MarkdownMessage } = await vite.ssrLoadModule('/src/components/MarkdownMessage.tsx');
  const source = [
    '# Interview question',
    '',
    '**Bold** and `inline code`.',
    '',
    '- first item',
    '- second item',
    '',
    '| Skill | Score |',
    '| --- | ---: |',
    '| Python | 9 |',
    '',
    '```python',
    'def answer():',
    '    return True',
    '```',
    '',
    '<img src=x onerror=alert(1)>',
    '[unsafe](javascript:alert(1))',
  ].join('\n');
  const html = renderToStaticMarkup(React.createElement(MarkdownMessage, null, source));

  assert.match(html, /<h1>Interview question<\/h1>/);
  assert.match(html, /<strong>Bold<\/strong>/);
  assert.match(html, /<code>inline code<\/code>/);
  assert.match(html, /<ul>[\s\S]*first item[\s\S]*second item[\s\S]*<\/ul>/);
  assert.match(html, /<table>/);
  assert.match(html, /<pre><code class="hljs language-python">/);
  assert.match(html, /class="hljs-keyword">def<\/span>/);
  assert.doesNotMatch(html, /<img\b/i);
  assert.doesNotMatch(html, /href="javascript:/i);
  const styles = await readFile(path.join(root, 'web/src/components/markdown.css'), 'utf8');
  assert.match(styles, /overflow-x:auto/);
  assert.match(styles, /@media\(max-width:560px\)/);
  assert.match(styles, /data-theme=light/);
  console.log('Markdown rendering, safety, and responsive theme checks passed.');
} finally {
  await vite.close();
}
