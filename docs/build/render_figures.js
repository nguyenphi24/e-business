// Đổi các SVG trong thư mục sang PNG (2x) bằng Chrome headless. Cần puppeteer-core và Google Chrome.
// Chạy: cd docs/build && npm install && npm run figures  (cần Google Chrome)
const fs = require("fs");
const path = require("path");
const puppeteer = require("puppeteer-core");

(async () => {
  const dir = process.argv[2];
  const browser = await puppeteer.launch({ executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", headless: true });
  const page = await browser.newPage();
  for (const file of fs.readdirSync(dir).filter((name) => name.endsWith(".svg"))) {
    const svg = fs.readFileSync(path.join(dir, file), "utf8");
    const [, width, height] = svg.match(/width="(\d+)" height="(\d+)"/);
    await page.setViewport({ width: Number(width), height: Number(height), deviceScaleFactor: 2 });
    await page.setContent(`<html><body style="margin:0">${svg}</body></html>`);
    await page.screenshot({ path: path.join(dir, file.replace(/\.svg$/, ".png")), clip: { x: 0, y: 0, width: Number(width), height: Number(height) } });
    console.log(file.replace(/\.svg$/, ".png"));
  }
  await browser.close();
})();
