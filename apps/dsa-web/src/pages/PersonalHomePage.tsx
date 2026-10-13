import type React from 'react';
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useWatchlist } from '../hooks/useWatchlist';

const PersonalHomePage: React.FC = () => {
  const { user, logout } = useAuth();
  const { watchlistCodes, isLoading, isActioning, actionMessage, addToWatchlist, removeFromWatchlist } = useWatchlist();
  const [stockCode, setStockCode] = useState('');

  const addStock = async (event: React.FormEvent) => {
    event.preventDefault();
    const code = stockCode.trim();
    if (!code) return;
    await addToWatchlist(code);
    setStockCode('');
  };

  return (
    <main className="min-h-screen bg-[#f6f7f8] px-5 py-8 text-slate-900">
      <div className="mx-auto max-w-4xl">
        <header className="flex items-center justify-between gap-4 border-b border-slate-200 pb-6">
          <div>
            <p className="text-xs font-semibold tracking-[.2em] text-slate-500">FINANCE ANALYSIS</p>
            <h1 className="mt-2 text-2xl font-semibold">金融分析的实力辅助</h1>
            <p className="mt-1 text-sm text-slate-500">你好，{user?.username}</p>
          </div>
          <div className="flex items-center gap-3">
            <Link to="/settings" className="rounded-lg border border-slate-300 px-4 py-2 text-sm hover:bg-white">我的设置</Link>
            <button type="button" className="rounded-lg border border-slate-300 px-4 py-2 text-sm hover:bg-white" onClick={() => void logout()}>
              退出登录
            </button>
          </div>
        </header>

        <section className="mt-8 rounded-2xl border border-slate-200 bg-white p-6" aria-labelledby="personal-watchlist-title">
          <h2 id="personal-watchlist-title" className="text-lg font-semibold">我的自选股</h2>
          <p className="mt-1 text-sm text-slate-500">这里的股票列表只属于你的账号。</p>
          <form className="mt-5 flex flex-wrap gap-3" onSubmit={(event) => void addStock(event)}>
            <label htmlFor="personal-stock-code" className="sr-only">股票代码</label>
            <input
              id="personal-stock-code"
              className="min-w-0 flex-1 rounded-lg border border-slate-300 px-3 py-2.5 outline-none focus:border-slate-700"
              placeholder="输入股票代码，如 AAPL"
              value={stockCode}
              onChange={(event) => setStockCode(event.target.value)}
              disabled={isActioning}
            />
            <button type="submit" className="rounded-lg bg-slate-900 px-5 py-2.5 text-sm font-medium text-white disabled:opacity-50" disabled={isActioning || !stockCode.trim()}>
              添加
            </button>
          </form>
          {actionMessage && <p className="mt-3 text-sm text-slate-600" role="status">{actionMessage}</p>}
          {isLoading ? <p className="mt-5 text-sm text-slate-500">正在加载自选股…</p> : watchlistCodes.length === 0 ? (
            <p className="mt-5 text-sm text-slate-500">还没有添加股票。</p>
          ) : (
            <ul className="mt-5 divide-y divide-slate-100">
              {watchlistCodes.map((code) => (
                <li key={code} className="flex items-center justify-between py-3">
                  <span className="font-medium">{code}</span>
                  <button type="button" className="text-sm text-slate-500 hover:text-slate-900" disabled={isActioning} onClick={() => void removeFromWatchlist(code)} aria-label={`移除 ${code}`}>
                    移除
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="mt-6 rounded-2xl border border-slate-200 bg-white p-6" aria-labelledby="personal-next-title">
          <h2 id="personal-next-title" className="text-lg font-semibold">其他功能正在接入</h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">报告、AI 问股、持仓、回测和告警正在按账号隔离。完成前这些功能暂不向普通账号开放，避免显示别人的数据。</p>
        </section>
      </div>
    </main>
  );
};

export default PersonalHomePage;
