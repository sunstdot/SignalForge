import { chromium } from 'playwright';
import { pathToFileURL } from 'node:url';

const [, , htmlPath, outputPath] = process.argv;

if (!htmlPath || !outputPath) {
  console.error('Usage: node render_social_cover.mjs <input.html> <output.png>');
  process.exit(2);
}

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1200, height: 1560 }, deviceScaleFactor: 1 });

try {
  await page.goto(pathToFileURL(htmlPath).href, { waitUntil: 'networkidle' });
  await page.locator('#xhs-cover').screenshot({ path: outputPath });
} finally {
  await browser.close();
}
