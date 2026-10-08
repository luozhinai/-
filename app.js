const stocks = [
  { name: '英伟达', code: 'NVDA', price: '138.25', change: '+2.84%', color: '#78a9e8', path: 'M0 21 C10 24 13 14 23 17 S37 11 46 15 S58 4 68 9' },
  { name: '苹果', code: 'AAPL', price: '226.47', change: '+0.63%', color: '#757d8d', path: 'M0 17 C12 19 15 10 25 15 S38 8 47 12 S58 5 68 7' },
  { name: '特斯拉', code: 'TSLA', price: '258.02', change: '−1.24%', color: '#e57b82', down: true, path: 'M0 5 C12 8 15 10 24 8 S38 19 46 14 S57 22 68 23' },
  { name: '微软', code: 'MSFT', price: '417.13', change: '+0.38%', color: '#6cae9b', path: 'M0 21 C11 17 16 20 24 14 S39 17 47 10 S58 15 68 7' },
];

const rowTemplate = (stock) => `<div class="stock-row"><div class="stock-name"><span class="stock-logo" style="background:${stock.color}">${stock.code.slice(0,1)}</span><div><strong>${stock.name}</strong><small>${stock.code}</small></div></div><span class="stock-price">$${stock.price}</span><span class="stock-change ${stock.down ? 'red' : 'green'}">${stock.change}</span><span class="stock-trend"><svg class="mini-line" viewBox="0 0 68 25" preserveAspectRatio="none"><path style="stroke:${stock.down ? '#e98788' : '#4bbd8c'}" d="${stock.path}" /></svg></span></div>`;

const list = document.querySelector('#watchlist-rows');
list.innerHTML = stocks.map(rowTemplate).join('');

const toast = document.querySelector('#toast');
let toastTimer;
function showToast(message) { toast.textContent = message; toast.classList.add('show'); clearTimeout(toastTimer); toastTimer = setTimeout(() => toast.classList.remove('show'), 2600); }

document.querySelector('#analysis-button').addEventListener('click', () => showToast('智能分析准备中，连接真实数据后即可开始。'));
document.querySelector('#full-report').addEventListener('click', () => showToast('完整分析报告将在分析模块上线后开放。'));
document.querySelector('#view-all').addEventListener('click', () => showToast('当前已展示 4 只自选股票。'));
document.querySelector('#add-stock').addEventListener('click', () => showToast('添加股票功能即将开放。'));
document.querySelector('#add-note').addEventListener('click', () => { document.querySelector('#note').focus(); showToast('开始记录你的分析备忘。'); });
document.querySelector('#save-note').addEventListener('click', () => { localStorage.setItem('finance-note', document.querySelector('#note').value); document.querySelector('#save-state').textContent = '刚刚保存'; showToast('分析备忘已保存到本地。'); });
const savedNote = localStorage.getItem('finance-note'); if (savedNote) document.querySelector('#note').value = savedNote;
document.querySelector('#stock-search').addEventListener('keydown', (event) => { if (event.key === 'Enter' && event.target.value.trim()) showToast(`正在搜索 ${event.target.value.trim()}...`); });
document.addEventListener('keydown', (event) => { if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') { event.preventDefault(); document.querySelector('#stock-search').focus(); } });
