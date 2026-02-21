const REFRESH_INTERVAL = 60; // seconds

let currentCurrency = 'usd';
let allCoins = [];
let countdown = REFRESH_INTERVAL;
let countdownTimer = null;
let fetchTimer = null;

const currencySymbols = { usd: '$', eur: '€', gbp: '£' };

// ── DOM refs ──
const grid       = document.getElementById('coins-grid');
const loader     = document.getElementById('loader');
const errorMsg   = document.getElementById('error-msg');
const searchEl   = document.getElementById('search');
const currencyEl = document.getElementById('currency');
const refreshBtn = document.getElementById('refresh-btn');
const lastUpdEl  = document.getElementById('last-updated');
const countdownEl= document.getElementById('countdown');

// ── Fetch ──
async function fetchCoins() {
  showLoader(true);
  showError('');
  try {
    const url = `/api/coins?currency=${currentCurrency}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    allCoins = await res.json();
    renderCoins(allCoins);
    lastUpdEl.textContent = `Last updated: ${new Date().toLocaleTimeString()}`;
    resetCountdown();
  } catch (err) {
    showError(`Failed to load data: ${err.message}. Check your connection or try again later.`);
  } finally {
    showLoader(false);
  }
}

// ── Render ──
function renderCoins(coins) {
  const query = searchEl.value.trim().toLowerCase();
  const filtered = coins.filter(c =>
    c.name.toLowerCase().includes(query) ||
    c.symbol.toLowerCase().includes(query)
  );

  if (filtered.length === 0) {
    grid.innerHTML = `<p style="color:#8b949e;grid-column:1/-1;text-align:center;padding:2rem">No coins found.</p>`;
    return;
  }

  const sym = currencySymbols[currentCurrency] ?? currentCurrency.toUpperCase() + ' ';

  grid.innerHTML = filtered.map(coin => {
    const change = coin.price_change_percentage_24h ?? 0;
    const changeClass = change >= 0 ? 'positive' : 'negative';
    const changeSign  = change >= 0 ? '+' : '';

    return `
      <div class="coin-card">
        <div class="coin-header">
          <img src="${coin.image}" alt="${coin.name}" loading="lazy" />
          <span class="coin-name">${coin.name}</span>
          <span class="coin-symbol">${coin.symbol}</span>
        </div>
        <div class="coin-price">${sym}${formatPrice(coin.current_price)}</div>
        <div class="coin-meta">
          <span>Market Cap: ${sym}${formatLarge(coin.market_cap)}</span>
          <span class="change ${changeClass}">${changeSign}${change.toFixed(2)}%</span>
        </div>
        <div class="coin-meta">
          <span>24h High: ${sym}${formatPrice(coin.high_24h)}</span>
          <span>24h Low: ${sym}${formatPrice(coin.low_24h)}</span>
        </div>
      </div>
    `;
  }).join('');
}

// ── Helpers ──
function formatPrice(n) {
  if (n === null || n === undefined) return '—';
  if (n >= 1) return n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return n.toPrecision(4);
}

function formatLarge(n) {
  if (n === null || n === undefined) return '—';
  if (n >= 1e12) return (n / 1e12).toFixed(2) + 'T';
  if (n >= 1e9)  return (n / 1e9).toFixed(2) + 'B';
  if (n >= 1e6)  return (n / 1e6).toFixed(2) + 'M';
  return n.toLocaleString();
}

function showLoader(show) {
  loader.classList.toggle('hidden', !show);
}

function showError(msg) {
  if (msg) {
    errorMsg.textContent = msg;
    errorMsg.classList.remove('hidden');
  } else {
    errorMsg.classList.add('hidden');
  }
}

// ── Auto-refresh countdown ──
function resetCountdown() {
  clearInterval(countdownTimer);
  clearTimeout(fetchTimer);
  countdown = REFRESH_INTERVAL;
  countdownEl.textContent = `Next refresh in ${countdown}s`;

  countdownTimer = setInterval(() => {
    countdown--;
    countdownEl.textContent = `Next refresh in ${countdown}s`;
    if (countdown <= 0) clearInterval(countdownTimer);
  }, 1000);

  fetchTimer = setTimeout(fetchCoins, REFRESH_INTERVAL * 1000);
}

// ── Event listeners ──
searchEl.addEventListener('input', () => renderCoins(allCoins));

currencyEl.addEventListener('change', () => {
  currentCurrency = currencyEl.value;
  fetchCoins();
});

refreshBtn.addEventListener('click', fetchCoins);

// ── Init ──
fetchCoins();
