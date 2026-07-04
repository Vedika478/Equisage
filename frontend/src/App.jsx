import React, { useState } from 'react';
import { 
  ResponsiveContainer, 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip 
} from 'recharts';
import { 
  Search, 
  Loader2, 
  AlertTriangle, 
  CheckCircle2, 
  TrendingUp, 
  TrendingDown, 
  HelpCircle,
  Shield,
  Activity,
  FileText,
  PieChart,
  RefreshCw,
  Info
} from 'lucide-react';

// Initial verified symbols with mock data for instant load
const INITIAL_STOCKS = [
  {
    symbol: 'RELIANCE.NS',
    name: 'Reliance Industries Limited',
    logo: 'R',
    price: 2530.45,
    change: 12.30,
    changePct: 0.49,
    sparkline: [2500, 2520, 2490, 2510, 2530, 2515, 2530],
    conviction: 'high',
    pillars: {
      fundamentals: 85,
      technical: 78,
      sentiment: 90,
      macro: 65,
      peers: 80
    },
    conflicts: [],
    stats: {
      prevClose: 2518.15,
      open: 2525.00,
      yearChange: 14.50,
      dayRange: '2515.00 - 2540.00',
      volume: '8.2M',
      marketCap: '₹17.1L Cr',
      convictionLevel: 'High',
      complianceStatus: 'Cleared'
    },
    research: {
      snapshot: 'Reliance Industries demonstrates strong fundamental growth, supported by positive sentiment in the retail and telecom sectors, offset slightly by flat refining margins.',
      conflictsFlagged: 'No major conflicts detected across pillars. All indicators are generally supportive.',
      summary: 'Pillar analysis shows robust fundamentals (85) and positive sentiment (90). Technicals suggest steady upward momentum with price trading above all major moving averages. Macro factors are stable.'
    }
  },
  {
    symbol: 'TCS.NS',
    name: 'Tata Consultancy Services',
    logo: 'T',
    price: 3450.10,
    change: -45.20,
    changePct: -1.29,
    sparkline: [3500, 3480, 3490, 3460, 3450, 3455, 3450],
    conviction: 'conflict',
    pillars: {
      fundamentals: 88,
      technical: 45,
      sentiment: 60,
      macro: 50,
      peers: 75
    },
    conflicts: [['Fundamentals', 'Technical']],
    stats: {
      prevClose: 3495.30,
      open: 3480.00,
      yearChange: -5.20,
      dayRange: '3440.00 - 3490.00',
      volume: '2.1M',
      marketCap: '₹12.6L Cr',
      convictionLevel: 'Mixed',
      complianceStatus: 'Cleared'
    },
    research: {
      snapshot: 'TCS maintains exceptional fundamental metrics and peer positioning with robust cash flow, but technical indicators suggest short-term chart weakness and distribution.',
      conflictsFlagged: '⚠ CONFLICT [1]: Fundamentals: Positive vs Technicals: Negative\n\n- Nature: Exceptional return on equity and profit margins contradict a short-term death cross and declining volume trend.\n- Implication: Institutional selling is depressing price action despite solid earnings health.\n- Resolution: Weight fundamentals higher for long-term horizons, but defer entry if trading short-term.',
      summary: 'While long-term value is intact with an 88 fundamentals rating, current chart patterns show a downtrend overriding the strong balance sheet. Compliance has verified all forward projections are hedged.'
    }
  },
  {
    symbol: 'INFY.NS',
    name: 'Infosys Limited',
    logo: 'I',
    price: 1560.80,
    change: 5.40,
    changePct: 0.35,
    sparkline: [1540, 1550, 1545, 1560, 1555, 1550, 1560],
    conviction: 'neutral',
    pillars: {
      fundamentals: 75,
      technical: 65,
      sentiment: 70,
      macro: 80,
      peers: 72
    },
    conflicts: [],
    stats: {
      prevClose: 1555.40,
      open: 1560.00,
      yearChange: 8.90,
      dayRange: '1550.00 - 1570.00',
      volume: '4.8M',
      marketCap: '₹6.5L Cr',
      convictionLevel: 'Moderate',
      complianceStatus: 'Cleared'
    },
    research: {
      snapshot: 'Infosys shows stable business growth with expanding order book, and tailwinds from RBI digital banking directives supporting IT infrastructure budgets.',
      conflictsFlagged: 'No major conflicts detected. Valuation is currently in-line with peer averages.',
      summary: 'Macro conditions are supportive (80) with favorable interest rate sensitivity. Technicals show consolidation patterns. Safe and stable candidate.'
    }
  }
];

const PILLARS_KEYS = ['Fundamentals', 'Technical', 'Sentiment', 'Macro', 'Peers'];

// Polar to Cartesian conversion helper for Radar Chart
const polarToCartesian = (value, index, scale, center = 150) => {
  const r = (value / 100) * scale;
  const angle = (Math.PI * 2 * index) / 5 - Math.PI / 2;
  return {
    x: center + r * Math.cos(angle),
    y: center + r * Math.sin(angle)
  };
};

export default function App() {
  const [stocks, setStocks] = useState(INITIAL_STOCKS);
  const [selectedStock, setSelectedStock] = useState(INITIAL_STOCKS[0]);
  const [loading, setLoading] = useState(false);
  const [searchSymbol, setSearchSymbol] = useState('');
  const [activeTab, setActiveTab] = useState('Price chart');
  const [timeframe, setTimeframe] = useState('1M');

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!searchSymbol.trim()) return;

    let symbol = searchSymbol.toUpperCase().trim();
    if (!symbol.includes('.')) {
      symbol += '.NS';
    }

    setLoading(true);
    try {
      const response = await fetch('http://localhost:8000/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbol, sector: 'Unknown', peers: [] })
      });

      if (!response.ok) {
        throw new Error(`API error: ${response.statusText}`);
      }

      const data = await response.json();
      
      setStocks((prev) => {
        const idx = prev.findIndex((s) => s.symbol === data.symbol);
        if (idx >= 0) {
          const updated = [...prev];
          updated[idx] = data;
          return updated;
        }
        return [data, ...prev];
      });
      setSelectedStock(data);
      setSearchSymbol('');
    } catch (err) {
      console.error('Analysis failed:', err);
      alert(`Failed to analyze stock. Please make sure the FastAPI server is running on port 8000.\nError: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Prepare Recharts price history format
  const chartData = selectedStock.sparkline.map((price, idx) => ({
    day: `Day ${idx + 1}`,
    price: price
  }));

  // Render Radar Chart polygon coordinates
  const radarPoints = PILLARS_KEYS.map((key, idx) => {
    const val = selectedStock.pillars[key.toLowerCase()] || 50;
    return polarToCartesian(val, idx, 100, 150);
  });
  const radarPolygonPoints = radarPoints.map((p) => `${p.x},${p.y}`).join(' ');

  // Sidebar metrics
  const highConviction = stocks.filter((s) => s.conviction === 'high');
  const conflictStocks = stocks.filter((s) => s.conviction === 'conflict');

  return (
    <div className="flex h-screen bg-[#F1F2EC] text-[#1B2430] font-sans overflow-hidden">
      
      {/* LEFT NAVIGATION / Watchlist Panel */}
      <div className="w-80 border-r border-[rgba(92,120,87,0.2)] bg-white flex flex-col shrink-0 overflow-y-auto">
        <div className="p-6 border-b border-[rgba(92,120,87,0.1)]">
          <h1 className="font-display text-3xl font-bold tracking-tight text-[#9C6F2A]">EquiSage</h1>
          <p className="text-xs text-[#6B7268] mt-1 font-mono uppercase tracking-wider">Multi-Agent Equity Research</p>
          
          <form onSubmit={handleSearch} className="mt-6 relative">
            <input
              type="text"
              placeholder="Search NSE stock (e.g. TCS)"
              value={searchSymbol}
              onChange={(e) => setSearchSymbol(e.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-[#F1F2EC] border border-[rgba(92,120,87,0.15)] rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-[#B6873A] font-medium"
            />
            <Search className="absolute left-3 top-2.5 text-[#6B7268]" size={16} />
          </form>
        </div>

        {/* Watchlist Section */}
        <div className="p-6 pb-2">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-[#5C7857] mb-4">Stock Watchlist</h2>
          <div className="space-y-3">
            {stocks.map((stock) => {
              const isSelected = selectedStock.symbol === stock.symbol;
              const isUp = stock.change >= 0;
              let badgeColor = 'bg-[#6B7268]';
              if (stock.conviction === 'high') badgeColor = 'bg-[#B6873A]';
              if (stock.conviction === 'conflict') badgeColor = 'bg-[#B14631]';

              return (
                <div
                  key={stock.symbol}
                  onClick={() => setSelectedStock(stock)}
                  className={`bg-white border rounded-xl p-4 cursor-pointer transition-all hover:shadow-md flex justify-between items-center ${
                    isSelected 
                      ? 'border-[#B6873A] ring-1 ring-[#B6873A]/30' 
                      : 'border-[rgba(92,120,87,0.15)] hover:border-[#5C7857]/40'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-[#F1F2EC] flex items-center justify-center font-display text-lg text-[#9C6F2A] border border-[rgba(92,120,87,0.1)]">
                      {stock.logo}
                    </div>
                    <div>
                      <h3 className="font-semibold text-sm leading-tight text-[#1B2430]">{stock.symbol.split('.')[0]}</h3>
                      <div className="flex items-center gap-1.5 mt-0.5">
                        <span className="text-xs text-[#6B7268] font-mono">{stock.symbol}</span>
                        <span className={`w-2 h-2 rounded-full ${badgeColor}`} title={`Conviction: ${stock.conviction}`} />
                      </div>
                    </div>
                  </div>
                  
                  <div className="text-right">
                    <div className="font-mono text-sm font-semibold">₹{stock.price.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</div>
                    <div className={`font-mono text-xs font-semibold flex items-center justify-end gap-0.5 ${isUp ? 'text-[#3F8F63]' : 'text-[#B14631]'}`}>
                      {isUp ? '▲' : '▼'} {Math.abs(stock.changePct)}%
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* CENTER ANALYSIS & DETAIL PANEL */}
      <div className="flex-1 flex flex-col h-full bg-white overflow-y-auto">
        <div className="p-8 pb-4">
          <div className="flex justify-between items-start mb-6">
            <div className="flex items-center gap-4">
              <div className="w-14 h-14 rounded-xl bg-[#F1F2EC] flex items-center justify-center font-display text-3xl font-bold text-[#9C6F2A] border border-[rgba(92,120,87,0.2)]">
                {selectedStock.logo}
              </div>
              <div>
                <div className="flex items-center gap-3">
                  <h2 className="text-3xl font-bold tracking-tight text-[#1B2430]">{selectedStock.symbol}</h2>
                  <span className="text-sm font-medium text-[#6B7268] font-mono">/ {selectedStock.name}</span>
                </div>
                
                <div className="flex items-baseline gap-3 mt-1.5">
                  <span className="font-mono text-4xl font-bold text-[#1B2430]">
                    ₹{selectedStock.price.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                  </span>
                  <span className={`font-mono text-sm font-semibold flex items-center gap-1 ${selectedStock.change >= 0 ? 'text-[#3F8F63]' : 'text-[#B14631]'}`}>
                    {selectedStock.change >= 0 ? '+' : ''}{selectedStock.change.toFixed(2)} ({selectedStock.changePct.toFixed(2)}%)
                  </span>
                </div>
              </div>
            </div>

            <div className="flex gap-2">
              <button 
                onClick={() => handleSearch({ preventDefault: () => {}, target: { value: selectedStock.symbol } })}
                className="flex items-center gap-2 px-4 py-2 border border-[rgba(92,120,87,0.2)] rounded-lg text-sm font-medium text-[#5C7857] hover:bg-[#F1F2EC] transition-colors"
              >
                <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
                Refresh
              </button>
            </div>
          </div>

          {/* Analysis Tab Switchers */}
          <div className="flex justify-between items-end border-b border-[rgba(92,120,87,0.2)]">
            <div className="flex gap-8">
              {['Price chart', 'Signal map', 'Research card'].map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`pb-3 text-sm font-semibold transition-colors relative ${
                    activeTab === tab ? 'text-[#9C6F2A]' : 'text-[#6B7268] hover:text-[#1B2430]'
                  }`}
                >
                  {tab}
                  {activeTab === tab && (
                    <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#B6873A]" />
                  )}
                </button>
              ))}
            </div>

            {activeTab === 'Price chart' && (
              <div className="flex gap-2 pb-3 font-mono">
                {['1D', '5D', '1M', '6M', '1Y'].map((t) => (
                  <button
                    key={t}
                    onClick={() => setTimeframe(t)}
                    className={`px-2.5 py-1 text-xs rounded transition-colors ${
                      timeframe === t ? 'bg-[#F1F2EC] text-[#1B2430] font-bold' : 'text-[#6B7268] hover:text-[#1B2430]'
                    }`}
                  >
                    {t}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Tab Contents */}
        <div className="px-8 py-6 min-h-[420px]">
          {activeTab === 'Price chart' && (
            <div className="w-full h-[360px] bg-white rounded-xl border border-[rgba(92,120,87,0.1)] p-4 shadow-sm">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 20, right: 20, left: 10, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#F1F2EC" />
                  <XAxis dataKey="day" tick={{ fill: '#6B7268', fontSize: 11, fontFamily: 'IBM Plex Mono' }} />
                  <YAxis domain={['auto', 'auto']} orientation="right" tick={{ fill: '#6B7268', fontSize: 11, fontFamily: 'IBM Plex Mono' }} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#FFFFFF', borderColor: 'rgba(92,120,87,0.2)', borderRadius: '8px' }}
                    labelStyle={{ fontFamily: 'Work Sans', fontWeight: 'bold' }}
                    itemStyle={{ color: '#1B2430', fontFamily: 'IBM Plex Mono' }}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="price" 
                    stroke={selectedStock.change >= 0 ? '#3F8F63' : '#B14631'} 
                    strokeWidth={2.5} 
                    dot={{ r: 3 }} 
                    activeDot={{ r: 6 }} 
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}

          {activeTab === 'Signal map' && (
            <div className="flex flex-col md:flex-row items-center justify-center gap-8 bg-white border border-[rgba(92,120,87,0.1)] rounded-xl p-8 shadow-sm">
              <div className="relative w-[300px] h-[300px] shrink-0">
                <svg width={300} height={300} viewBox="0 0 300 300">
                  {/* Grid Rings */}
                  {[20, 40, 60, 80, 100].map((ring, ringIdx) => (
                    <polygon
                      key={ringIdx}
                      points={PILLARS_KEYS.map((_, idx) => polarToCartesian(ring, idx, 100, 150)).map(p => `${p.x},${p.y}`).join(' ')}
                      fill="none"
                      stroke="rgba(92, 120, 87, 0.15)"
                      strokeWidth="1"
                    />
                  ))}
                  {/* Spokes */}
                  {PILLARS_KEYS.map((_, idx) => {
                    const outer = polarToCartesian(100, idx, 100, 150);
                    return (
                      <line
                        key={idx}
                        x1={150}
                        y1={150}
                        x2={outer.x}
                        y2={outer.y}
                        stroke="rgba(92, 120, 87, 0.15)"
                        strokeWidth="1"
                      />
                    );
                  })}
                  {/* Radar Polygon Area */}
                  <polygon
                    points={radarPolygonPoints}
                    fill="rgba(182, 135, 58, 0.15)"
                    stroke="#B6873A"
                    strokeWidth="2"
                    className="transition-all duration-500 ease-in-out"
                  />
                  {/* Dashed Conflict Connections */}
                  {selectedStock.conflicts && selectedStock.conflicts.map((conflict, conflictIdx) => {
                    const idx1 = PILLARS_KEYS.findIndex(key => key.toLowerCase() === conflict[0].toLowerCase());
                    const idx2 = PILLARS_KEYS.findIndex(key => key.toLowerCase() === conflict[1].toLowerCase());
                    if (idx1 >= 0 && idx2 >= 0) {
                      const p1 = radarPoints[idx1];
                      const p2 = radarPoints[idx2];
                      return (
                        <line
                          key={conflictIdx}
                          x1={p1.x}
                          y1={p1.y}
                          x2={p2.x}
                          y2={p2.y}
                          stroke="#B14631"
                          strokeWidth="2"
                          strokeDasharray="4 4"
                          className="animate-pulse"
                        />
                      );
                    }
                    return null;
                  })}
                  {/* Dots */}
                  {radarPoints.map((p, idx) => (
                    <circle
                      key={idx}
                      cx={p.x}
                      cy={p.y}
                      r="4.5"
                      fill="#FFFFFF"
                      stroke="#B6873A"
                      strokeWidth="2"
                    />
                  ))}
                </svg>
                {/* Labels */}
                {PILLARS_KEYS.map((label, idx) => {
                  const labelPos = polarToCartesian(120, idx, 100, 150);
                  return (
                    <div
                      key={label}
                      className="absolute text-[10px] font-bold text-[#5C7857] uppercase tracking-widest -translate-x-1/2 -translate-y-1/2"
                      style={{ left: labelPos.x, top: labelPos.y }}
                    >
                      {label}
                    </div>
                  );
                })}
              </div>

              {/* Pillar Scores Table */}
              <div className="flex-1 space-y-4 w-full">
                <h3 className="text-sm font-semibold uppercase tracking-wider text-[#5C7857]">Pillar Analysis Scores</h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {PILLARS_KEYS.map((key) => {
                    const val = selectedStock.pillars[key.toLowerCase()] || 50;
                    return (
                      <div key={key} className="bg-[#F1F2EC] rounded-lg p-3 flex justify-between items-center border border-[rgba(92,120,87,0.08)]">
                        <span className="font-semibold text-sm text-[#1B2430]">{key}</span>
                        <div className="flex items-center gap-2">
                          <div className="w-20 bg-white rounded-full h-1.5 overflow-hidden">
                            <div className="bg-[#B6873A] h-full" style={{ width: `${val}%` }} />
                          </div>
                          <span className="font-mono text-sm font-bold text-[#9C6F2A] w-6 text-right">{val}</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
                {selectedStock.conflicts && selectedStock.conflicts.length > 0 && (
                  <div className="bg-[#B14631]/5 border border-[#B14631]/20 rounded-lg p-3 flex items-start gap-2.5 mt-4">
                    <AlertTriangle className="text-[#B14631] shrink-0 mt-0.5" size={16} />
                    <span className="text-xs text-[#B14631] font-semibold leading-normal">
                      Radar displays red dashed lines representing actively flagged signal conflicts.
                    </span>
                  </div>
                )}
              </div>
            </div>
          )}

          {activeTab === 'Research card' && (
            <div className="space-y-6 bg-white border border-[rgba(92,120,87,0.1)] rounded-xl p-8 shadow-sm">
              <div>
                <h3 className="text-xs font-semibold text-[#5C7857] uppercase tracking-widest mb-2 flex items-center gap-1.5">
                  <Info size={14} /> Company Snapshot
                </h3>
                <p className="text-sm text-[#1B2430] leading-relaxed font-normal">{selectedStock.research.snapshot}</p>
              </div>

              {selectedStock.conflicts && selectedStock.conflicts.length > 0 && (
                <div className="border border-[#B14631]/30 bg-[#B14631]/5 p-5 rounded-lg">
                  <h4 className="text-sm font-semibold text-[#B14631] mb-2.5 flex items-center gap-1.5">
                    <AlertTriangle size={16} /> Signal Conflicts Flagged
                  </h4>
                  <pre className="text-xs text-[#1B2430] leading-relaxed font-sans whitespace-pre-wrap">
                    {selectedStock.research.conflictsFlagged}
                  </pre>
                </div>
              )}

              <div className="border-t border-[rgba(92,120,87,0.1)] pt-6">
                <h3 className="text-xs font-semibold text-[#5C7857] uppercase tracking-widest mb-3 flex items-center gap-1.5">
                  <FileText size={14} /> Comprehensive Summary
                </h3>
                <div className="text-sm text-[#1B2430] leading-relaxed whitespace-pre-wrap">
                  {selectedStock.research.summary}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* METRICS GRID FOOTER */}
        <div className="mt-auto p-8 border-t border-[rgba(92,120,87,0.2)] bg-[#F1F2EC]/40">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            {[
              { label: 'Prev. Close', value: `₹${selectedStock.stats.prevClose.toLocaleString('en-IN')}` },
              { label: 'Open', value: `₹${selectedStock.stats.open.toLocaleString('en-IN')}` },
              { label: 'Volume', value: selectedStock.stats.volume },
              { label: 'Market Cap', value: selectedStock.stats.marketCap },
              { label: '1-Year Change', value: `${selectedStock.stats.yearChange >= 0 ? '+' : ''}${selectedStock.stats.yearChange}%` },
              { label: "Day's Range", value: selectedStock.stats.dayRange },
              { label: 'Conviction', value: selectedStock.stats.convictionLevel },
              { label: 'Compliance Status', value: selectedStock.stats.complianceStatus }
            ].map((stat, idx) => (
              <div key={idx} className="flex justify-between items-center pr-4 border-r border-[rgba(92,120,87,0.1)] last:border-0">
                <span className="text-xs font-medium text-[#6B7268]">{stat.label}</span>
                <span className="text-sm font-mono font-bold text-[#1B2430]">{stat.value}</span>
              </div>
            ))}
          </div>
        </div>

        {/* BOTTOM SEBI disclaimer */}
        <div className="bg-[#F1F2EC] border-t border-[rgba(92,120,87,0.2)] p-4 text-center shrink-0">
          <p className="text-[10px] font-mono text-[#6B7268] max-w-4xl mx-auto leading-normal">
            **DISCLAIMER**: The outputs displayed here are generated by an automated multi-agent system. Under no circumstances should they be construed as investment advice, trading recommendations, or a guarantee of returns. Consult a SEBI-registered advisor before committing capital.
          </p>
        </div>
      </div>

      {/* RIGHT SIDEBAR - CONVICTIONS & ANOMALIES */}
      <div className="w-80 border-l border-[rgba(92,120,87,0.2)] bg-[#F1F2EC]/30 flex flex-col shrink-0 overflow-y-auto">
        <div className="p-6">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-[#5C7857] flex items-center gap-1.5">
              <CheckCircle2 size={16} className="text-[#B6873A]" /> High Conviction Signals
            </h3>
            <span className="text-xs font-mono font-bold text-[#9C6F2A] bg-[#B6873A]/10 px-2 py-0.5 rounded">
              {highConviction.length}
            </span>
          </div>

          <div className="space-y-3">
            {highConviction.map((s) => (
              <div
                key={s.symbol}
                onClick={() => setSelectedStock(s)}
                className="bg-white border border-[rgba(92,120,87,0.15)] rounded-xl p-3.5 hover:shadow-md cursor-pointer transition-all"
              >
                <div className="flex justify-between items-start">
                  <div className="font-semibold text-sm text-[#1B2430]">{s.symbol.split('.')[0]}</div>
                  <span className="font-mono text-xs font-bold text-[#9C6F2A] bg-[#B6873A]/10 px-1.5 py-0.5 rounded">
                    Score: {Math.round((s.pillars.fundamentals + s.pillars.sentiment) / 2)}
                  </span>
                </div>
                <div className="text-xs text-[#6B7268] mt-1.5 line-clamp-2 leading-relaxed">
                  {s.research.snapshot}
                </div>
              </div>
            ))}
            {highConviction.length === 0 && (
              <div className="text-center py-6 text-xs text-[#6B7268] border border-dashed border-[rgba(92,120,87,0.15)] rounded-xl bg-white/50">
                No high conviction candidates.
              </div>
            )}
          </div>

          <div className="flex justify-between items-center mb-4 mt-8">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-[#B14631] flex items-center gap-1.5">
              <AlertTriangle size={16} /> Review Conflicts
            </h3>
            <span className="text-xs font-mono font-bold text-[#B14631] bg-[#B14631]/10 px-2 py-0.5 rounded">
              {conflictStocks.length}
            </span>
          </div>

          <div className="space-y-3">
            {conflictStocks.map((s) => (
              <div
                key={s.symbol}
                onClick={() => setSelectedStock(s)}
                className="bg-white border border-[#B14631]/20 rounded-xl p-3.5 hover:shadow-md cursor-pointer transition-all"
              >
                <div className="flex justify-between items-start">
                  <div className="font-semibold text-sm text-[#1B2430] flex items-center gap-1.5">
                    <AlertTriangle size={14} className="text-[#B14631]" />
                    {s.symbol.split('.')[0]}
                  </div>
                  <span className="font-mono text-[10px] font-bold text-[#B14631] bg-[#B14631]/10 px-1.5 py-0.5 rounded uppercase">
                    Mixed
                  </span>
                </div>
                <div className="text-xs text-[#B14631] font-semibold mt-1 font-mono">
                  {s.conflicts.map(c => c.join(' vs ')).join(', ')}
                </div>
                <div className="text-xs text-[#6B7268] mt-2 line-clamp-2 leading-relaxed">
                  {s.research.snapshot}
                </div>
              </div>
            ))}
            {conflictStocks.length === 0 && (
              <div className="text-center py-6 text-xs text-[#6B7268] border border-dashed border-[rgba(92,120,87,0.15)] rounded-xl bg-white/50">
                No active conflicts to review.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* OVERLAY LOADING SPINNER SCREEN */}
      {loading && (
        <div className="absolute inset-0 bg-white/80 backdrop-blur-md z-50 flex flex-col items-center justify-center">
          <Loader2 className="h-12 w-12 text-[#B6873A] animate-spin mb-4" />
          <h3 className="text-xl font-bold tracking-tight text-[#1B2430]">Analyzing Multiple Pillars...</h3>
          <p className="text-sm text-[#6B7268] mt-2 max-w-sm text-center leading-relaxed">
            Specialist agents are concurrently collecting metrics, technical patterns, sentiment signals, and RBI regulatory context.
          </p>
        </div>
      )}

    </div>
  );
}
