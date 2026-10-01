/**
 * scripts/generate_tutorial.js
 *
 * Automated Playwright script that navigates VoltAI's interface,
 * triggers every feature and interactive state, and captures high-resolution
 * screenshots for the official tutorial documentation.
 */

let playwright;
try {
  playwright = require('playwright');
} catch (e) {
  try {
    playwright = require('/home/sahilsomyani/.npm/_npx/2334a3ea0ef73d73/node_modules/playwright');
  } catch (e2) {
    throw new Error('Playwright not found. Please install it or set NODE_PATH.');
  }
}
const { chromium } = playwright;
const path = require('path');
const fs = require('fs');

const OUTPUT_DIR = path.resolve(__dirname, '../docs/tutorial/images');

async function main() {
  if (!fs.existsSync(OUTPUT_DIR)) {
    fs.mkdirSync(OUTPUT_DIR, { recursive: true });
  }

  console.log('🚀 Launching Playwright Chromium...');
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 960 },
    deviceScaleFactor: 2, // Crisp retina screenshots
  });

  const page = await context.newPage();
  const htmlPath = 'file://' + path.resolve(__dirname, '../index.html');

  console.log(`📄 Navigating to ${htmlPath}...`);
  await page.goto(htmlPath, { waitUntil: 'networkidle' });
  await page.waitForTimeout(1000); // Allow Chart.js and fonts to settle

  console.log('📸 Step 1: Capturing Header & Brand Navigation...');
  const header = await page.$('header');
  if (header) {
    await header.screenshot({ path: path.join(OUTPUT_DIR, '01_overview_header.png') });
  }

  console.log('📸 Step 2: Capturing KPI Metrics Grid...');
  const kpiGrid = await page.$('.kpi-grid');
  if (kpiGrid) {
    await kpiGrid.screenshot({ path: path.join(OUTPUT_DIR, '02_kpi_cards.png') });
  }

  console.log('📸 Step 3: Capturing Interactive Priority Sliders & Presets...');
  const sliderModule = await page.$('.right-column .card');
  if (sliderModule) {
    await sliderModule.screenshot({ path: path.join(OUTPUT_DIR, '03_priority_sliders.png') });
  }

  console.log('📸 Step 4: Interacting with AI Action Center & Testing "Max Savings" Preset...');
  // Click Max Savings preset button
  await page.click('button:has-text("Max Savings")');
  await page.waitForTimeout(500);
  const actionCenter = await page.$('#aiActionCenter');
  if (actionCenter) {
    await actionCenter.screenshot({ path: path.join(OUTPUT_DIR, '04_ai_action_center.png') });
  }

  console.log('📸 Step 5: Capturing Dual-Axis Charging Load & ToD Pricing Chart...');
  const chartCard = await page.$('.left-column .card:first-child');
  if (chartCard) {
    await chartCard.screenshot({ path: path.join(OUTPUT_DIR, '05_dual_axis_chart.png') });
  }

  console.log('📸 Step 6: Capturing EV Fleet Telematics Table (All Vehicles)...');
  const tableCard = await page.$('.left-column .card:nth-child(2)');
  if (tableCard) {
    await tableCard.screenshot({ path: path.join(OUTPUT_DIR, '06_telematics_table_all.png') });
  }

  console.log('📸 Step 7: Filtering Fleet Table by "Critical" Status...');
  await page.click('button:has-text("Critical")');
  await page.waitForTimeout(400);
  if (tableCard) {
    await tableCard.screenshot({ path: path.join(OUTPUT_DIR, '07_telematics_filter_critical.png') });
  }
  // Reset back to All
  await page.click('button:has-text("All EVs")');
  await page.waitForTimeout(300);

  console.log('📸 Step 8: Simulating Off-Grid Islanded Mode...');
  // Click grid toggle pill
  await page.click('#gridStatusPill');
  await page.waitForTimeout(600);
  const gridPill = await page.$('#gridStatusPill');
  if (gridPill) {
    await gridPill.screenshot({ path: path.join(OUTPUT_DIR, '08_grid_toggle_offgrid.png') });
  }
  // Toggle back to online
  await page.click('#gridStatusPill');
  await page.waitForTimeout(400);

  console.log('📸 Step 9: Capturing Full Dashboard in Light Mode...');
  await page.screenshot({ path: path.join(OUTPUT_DIR, '09_full_dashboard_light.png'), fullPage: true });

  console.log('📸 Step 10: Toggling Dark Minimalist Charcoal Theme...');
  await page.click('#themeToggleBtn');
  await page.waitForTimeout(600);
  await page.screenshot({ path: path.join(OUTPUT_DIR, '10_full_dashboard_dark.png'), fullPage: true });

  console.log('📸 Step 11: Capturing Dark Mode Chart & Telematics Modules...');
  if (chartCard) {
    await chartCard.screenshot({ path: path.join(OUTPUT_DIR, '11_dark_mode_chart.png') });
  }

  console.log('📸 Step 12: Switching to Streamlit Engine View Tab...');
  await page.click('#tabStreamlit');
  await page.waitForTimeout(500);
  const iframeContainer = await page.$('#streamlitIframeView');
  if (iframeContainer) {
    await page.screenshot({ path: path.join(OUTPUT_DIR, '12_view_switcher_streamlit_tab.png') });
  }

  await browser.close();
  console.log(`✅ Tutorial screenshots generated successfully in ${OUTPUT_DIR}!`);
}

main().catch((err) => {
  console.error('❌ Error generating tutorial:', err);
  process.exit(1);
});
