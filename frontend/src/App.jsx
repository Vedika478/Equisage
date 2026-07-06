import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  LineChart, Line, ResponsiveContainer, Tooltip,
  XAxis, YAxis, RadarChart, Radar,
  PolarGrid, PolarAngleAxis, PolarRadiusAxis,
} from "recharts";

// ─── Design tokens (matching index.css) ──────────────────────────────────────
const T = {
  bg:        "#F1F2EC",
  panel:     "#FFFFFF",
  brass:     "#B6873A",
  brassDeep: "#9C6F2A",
  sage:      "#5C7857",
  gain:      "#3F8F63",
  loss:      "#B14631",
  text:      "#1B2430",
  muted:     "#6B7268",
  border:    "#E2E4DC",
  borderMid: "#C9CCC3",
};

// ─── Formatters ───────────────────────────────────────────────────────────────
const fmt = {
  price: (v) => v != null ? `₹${Number(v).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : "—",
  pct:   (v) => v != null ? `${v >= 0 ? "+" : ""}${Number(v).toFixed(2)}%` : "—",
  vol:   (v) => {
    if (!v) return "—";
    if (v >= 1e7) return `${(v / 1e7).toFixed(2)} Cr`;
    if (v >= 1e5) return `${(v / 1e5).toFixed(2)} L`;
    return Number(v).toLocaleString("en-IN");
  },
  mcap:  (v) => {
    if (!v) return "—";
    if (v >= 1e12) return `₹${(v / 1e12).toFixed(2)}T`;
    if (v >= 1e9)  return `₹${(v / 1e9).toFixed(2)}B`;
    if (v >= 1e7)  return `₹${(v / 1e7).toFixed(2)} Cr`;
    return `₹${v}`;
  },
  num:   (v, d = 2) => (v != null && v !== 0) ? Number(v).toFixed(d) : "—",
};

function pctColor(v) { return v >= 0 ? T.gain : T.loss; }

// ─── Conviction engine ────────────────────────────────────────────────────────
function conviction(data) {
  const c       = data?.synthesis?.conviction || "LOW";
  const pillars = data?.pillars || {};
  const sigs    = Object.values(pillars).map(p => p?.signal || "neutral");
  const bull    = sigs.filter(s => s === "bullish").length;
  const bear    = sigs.filter(s => s === "bearish").length;

  if (c === "HIGH"   && bull >= 3)          return { label: "STRONG BUY",  color: "#1E7A4B", bg: "#E8F5EE", border: "#A8D5BC" };
  if ((c === "HIGH" || c === "MEDIUM") && bull > bear) return { label: "BUY",  color: "#2A6E45", bg: "#EEF7F2", border: "#B8DAC5" };
  if (c === "HIGH"   && bear >= 3)          return { label: "STRONG SELL", color: "#B14631", bg: "#FBF0EE", border: "#E8B5A8" };
  if ((c === "HIGH" || c === "MEDIUM") && bear > bull) return { label: "SELL", color: "#A03A28", bg: "#FCF2F0", border: "#ECC0B5" };
  if (c === "CONFLICTED")                   return { label: "HOLD / WATCH",color: "#7A5C1A", bg: "#FBF5E8", border: "#E0C882" };
  return { label: "NEUTRAL", color: T.muted, bg: "#F5F5F2", border: T.border };
}

const sigColor  = s => s === "bullish" ? T.gain : s === "bearish" ? T.loss : T.muted;
const scoreColor= n => n >= 7 ? T.gain : n >= 5 ? T.brass : T.loss;

// ─── Sub-components ───────────────────────────────────────────────────────────

function PillarScoreRow({ label, pillar }) {
  const score = pillar?.score || 5;
  const sig   = pillar?.signal || "neutral";
  return (
    <div style={{ display:"flex", alignItems:"center", gap:8, marginBottom:5 }}>
      <div style={{ width:88, fontSize:11, color:T.muted, fontFamily:"IBM Plex Mono,monospace" }}>{label}</div>
      <div style={{ flex:1, height:4, background:T.border, borderRadius:2, overflow:"hidden" }}>
        <div style={{ width:`${score*10}%`, height:"100%", background:sigColor(sig), borderRadius:2, transition:"width .4s" }} />
      </div>
      <div style={{ width:22, fontSize:11, fontWeight:700, color:scoreColor(score), textAlign:"right", fontFamily:"IBM Plex Mono,monospace" }}>{score}</div>
    </div>
  );
}

function PillarCard({ title, icon, data }) {
  const [open, setOpen] = useState(false);
  if (!data) return null;
  const { score=5, signal="neutral", summary="", key_insights=[], metrics={},
    tailwinds=[], headwinds=[], competitive_advantages=[], competitive_risks=[],
    catalysts=[], risks=[], top_headlines=[] } = data;
  const sc = sigColor(signal);
  return (
    <div
      onClick={() => setOpen(o => !o)}
      style={{ background:T.panel, border:`1px solid ${T.border}`, borderLeft:`3px solid ${sc}`,
        borderRadius:10, padding:"14px 16px", cursor:"pointer", marginBottom:10,
        boxShadow:"0 1px 3px rgba(27,36,48,0.06)", transition:"box-shadow .2s" }}
      onMouseEnter={e => e.currentTarget.style.boxShadow="0 3px 8px rgba(27,36,48,0.12)"}
      onMouseLeave={e => e.currentTarget.style.boxShadow="0 1px 3px rgba(27,36,48,0.06)"}
    >
      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center" }}>
        <div style={{ display:"flex", alignItems:"center", gap:8 }}>
          <span style={{ fontSize:15 }}>{icon}</span>
          <span style={{ fontSize:13, fontWeight:600, color:T.text }}>{title}</span>
          <span style={{ fontSize:10, fontWeight:700, color:sc, textTransform:"uppercase",
            fontFamily:"IBM Plex Mono,monospace", letterSpacing:0.5 }}>{signal}</span>
        </div>
        <div style={{ display:"flex", alignItems:"center", gap:8 }}>
          <span style={{ fontSize:12, fontWeight:700, color:scoreColor(score),
            background:`${scoreColor(score)}15`, borderRadius:4,
            padding:"2px 8px", fontFamily:"IBM Plex Mono,monospace" }}>{score}/10</span>
          <span style={{ color:T.muted, fontSize:11 }}>{open ? "▲" : "▼"}</span>
        </div>
      </div>
      <p style={{ color:T.muted, fontSize:12.5, lineHeight:1.65, margin:"8px 0 0", fontWeight:400 }}>{summary}</p>
      {open && (
        <div style={{ marginTop:12, paddingTop:12, borderTop:`1px solid ${T.border}` }}>
          {key_insights.length > 0 && (
            <div style={{ marginBottom:10 }}>
              <div style={{ fontSize:10, color:T.muted, fontWeight:700, letterSpacing:1,
                textTransform:"uppercase", marginBottom:6, fontFamily:"IBM Plex Mono,monospace" }}>Key Insights</div>
              {key_insights.map((ins, i) => (
                <div key={i} style={{ display:"flex", gap:8, color:T.text, fontSize:12.5, lineHeight:1.6, marginBottom:4 }}>
                  <span style={{ color:sc, flexShrink:0 }}>•</span>{ins}
                </div>
              ))}
            </div>
          )}
          {[
            { label:"Tailwinds",             items:tailwinds,             color:T.gain },
            { label:"Headwinds",             items:headwinds,             color:T.loss },
            { label:"Competitive Advantages",items:competitive_advantages,color:T.gain },
            { label:"Competitive Risks",     items:competitive_risks,     color:T.loss },
            { label:"Catalysts",             items:catalysts,             color:T.gain },
            { label:"Risks",                 items:risks,                 color:T.loss },
          ].filter(g => g.items?.length > 0).map(group => (
            <div key={group.label} style={{ marginBottom:8 }}>
              <div style={{ fontSize:10, color:group.color, fontWeight:700, letterSpacing:1,
                textTransform:"uppercase", marginBottom:4, fontFamily:"IBM Plex Mono,monospace" }}>{group.label}</div>
              {group.items.map((item,i) => (
                <div key={i} style={{ fontSize:12, color:T.text, marginBottom:3 }}>
                  {group.color===T.gain ? "✓" : "✗"} {item}
                </div>
              ))}
            </div>
          ))}
          {top_headlines.length > 0 && (
            <div>
              <div style={{ fontSize:10, color:T.muted, fontWeight:700, letterSpacing:1,
                textTransform:"uppercase", marginBottom:6, fontFamily:"IBM Plex Mono,monospace" }}>Headlines</div>
              {top_headlines.map((h,i) => (
                <div key={i} style={{ display:"flex", justifyContent:"space-between",
                  fontSize:12, color:T.muted, marginBottom:4, gap:8 }}>
                  <span>{h.title || h}</span>
                  {h.sentiment && <span style={{ color:sigColor(h.sentiment==="positive"?"bullish":h.sentiment==="negative"?"bearish":"neutral"), flexShrink:0 }}>{h.sentiment}</span>}
                </div>
              ))}
            </div>
          )}
          {Object.keys(metrics).length > 0 && (
            <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill,minmax(100px,1fr))", gap:8, marginTop:8 }}>
              {Object.entries(metrics).map(([k,v]) => (
                <div key={k} style={{ background:T.bg, borderRadius:6, padding:"6px 10px", border:`1px solid ${T.border}` }}>
                  <div style={{ color:T.muted, fontSize:9.5, textTransform:"uppercase", letterSpacing:0.5,
                    fontFamily:"IBM Plex Mono,monospace" }}>{k.replace(/_/g," ")}</div>
                  <div style={{ color:T.text, fontSize:12.5, fontWeight:600, marginTop:2 }}>
                    {typeof v==="number" ? fmt.num(v) : String(v)}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function MetricCell({ label, value, color }) {
  return (
    <div style={{ background:T.bg, border:`1px solid ${T.border}`, borderRadius:8, padding:"10px 12px" }}>
      <div style={{ fontSize:9.5, color:T.muted, textTransform:"uppercase", letterSpacing:0.5,
        fontFamily:"IBM Plex Mono,monospace", marginBottom:4 }}>{label}</div>
      <div style={{ fontSize:14, fontWeight:700, color:color || T.text,
        fontFamily:"IBM Plex Mono,monospace" }}>{value || "—"}</div>
    </div>
  );
}

// ─── Pillar meta ──────────────────────────────────────────────────────────────
const PILLARS = [
  { key:"fundamentals",  label:"Fundamentals",        icon:"📊" },
  { key:"technical",     label:"Technical Analysis",  icon:"📈" },
  { key:"news_sentiment",label:"News & Sentiment",    icon:"📰" },
  { key:"macro",         label:"Macro Environment",   icon:"🌍" },
  { key:"competitive",   label:"Competitive Position",icon:"🏆" },
];

const QUICK_SEARCHES = ["Infosys", "Zomato", "Bajaj Finance", "IRCTC", "HDFC Bank", "Sun Pharma", "JSW Steel", "Asian Paints"];

// ─── Main App ─────────────────────────────────────────────────────────────────
const SUGG_CACHE = {};

export default function App() {
  const [watchlist,     setWatchlist]     = useState([]);
  const [selected,      setSelected]      = useState(null);
  const [loading,       setLoading]       = useState(false);
  const [loadingMsg,    setLoadingMsg]    = useState("");
  const [error,         setError]         = useState(null);
  const [query,         setQuery]         = useState("");
  const [suggestions,   setSuggestions]   = useState([]);
  const [showSugg,      setShowSugg]      = useState(false);
  const [activeTab,     setActiveTab]     = useState("overview");
  const searchRef  = useRef(null);
  const debRef     = useRef(null);

  useEffect(() => {
    const fn = e => { if (searchRef.current && !searchRef.current.contains(e.target)) setShowSugg(false); };
    document.addEventListener("mousedown", fn);
    return () => document.removeEventListener("mousedown", fn);
  }, []);

  const fetchSuggestions = useCallback(async (val) => {
    if (val.length < 2) { setSuggestions([]); setShowSugg(false); return; }
    if (SUGG_CACHE[val]) { setSuggestions(SUGG_CACHE[val]); setShowSugg(true); return; }
    try {
      const r = await fetch(`${import.meta.env.PROD ? "https://shaurya0606-equisage.hf.space" : ""}/api/search?q=${encodeURIComponent(val)}`);
      const d = await r.json();
      const results = d.results || [];
      SUGG_CACHE[val] = results;
      setSuggestions(results);
      setShowSugg(results.length > 0);
    } catch { setSuggestions([]); }
  }, []);

  const analyzeStock = useCallback(async (symbol, displayName) => {
    setShowSugg(false); setQuery(""); setSuggestions([]);
    setError(null); setLoading(true); setActiveTab("overview");

    const msgs = [
      `Resolving ${displayName || symbol}…`,
      "Fetching live market data…",
      "Fundamentals Agent running…",
      "Technical Analysis Agent running…",
      "News & Sentiment Agent running…",
      "Macro Environment Agent (RAG)…",
      "Competitive Analysis Agent running…",
      "Synthesising all 5 analyses…",
      "Generating investment verdict…",
    ];
    let mi = 0;
    setLoadingMsg(msgs[0]);
    const iv = setInterval(() => { mi = Math.min(mi+1, msgs.length-1); setLoadingMsg(msgs[mi]); }, 8000);

    try {
      const res = await fetch(`${import.meta.env.PROD ? "https://shaurya0606-equisage.hf.space" : ""}/analyze`, {
        method:"POST", headers:{"Content-Type":"application/json"},
        body:JSON.stringify({ symbol }),
      });
      clearInterval(iv);
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Server error ${res.status}`);
      }
      const data = await res.json();
      setWatchlist(prev => {
        const idx = prev.findIndex(s => s.symbol === data.symbol);
        if (idx >= 0) { const u=[...prev]; u[idx]=data; return u; }
        return [data, ...prev];
      });
      setSelected(data);
    } catch(err) {
      clearInterval(iv);
      setError(err.message);
    } finally {
      setLoading(false); setLoadingMsg("");
    }
  }, []);

  const handleQueryChange = e => {
    const val = e.target.value; setQuery(val);
    clearTimeout(debRef.current);
    debRef.current = setTimeout(() => fetchSuggestions(val.trim()), 350);
  };

  const handleSubmit = e => {
    e.preventDefault();
    if (!query.trim()) return;
    if (suggestions.length > 0) analyzeStock(suggestions[0].symbol, suggestions[0].name);
    else analyzeStock(query.trim(), query.trim());
  };

  const conv    = selected ? conviction(selected) : null;
  const pillars = selected?.pillars || {};

  // ─── Render ────────────────────────────────────────────────────────────────
  return (
    <div style={{ display:"flex", height:"100vh", background:T.bg,
      color:T.text, fontFamily:"Work Sans,sans-serif", overflow:"hidden" }}>

      {/* ── SIDEBAR ────────────────────────────────────────────────────────── */}
      <div style={{ width:268, flexShrink:0, background:T.panel,
        borderRight:`1px solid ${T.border}`, display:"flex", flexDirection:"column", overflow:"hidden" }}>

        {/* Logo */}
        <div style={{ padding:"22px 20px 14px", borderBottom:`1px solid ${T.border}` }}>
          <div style={{ fontFamily:"Instrument Serif,serif", fontSize:26, color:T.text, letterSpacing:-0.3 }}>
            Equi<span style={{ color:T.brass }}>Sage</span>
          </div>
          <div style={{ fontSize:10, color:T.muted, letterSpacing:2, textTransform:"uppercase", marginTop:2,
            fontFamily:"IBM Plex Mono,monospace" }}>AI Investment Research</div>
        </div>

        {/* Search */}
        <div style={{ padding:"14px 14px 10px", position:"relative" }} ref={searchRef}>
          <form onSubmit={handleSubmit}>
            <div style={{ display:"flex", alignItems:"center", background:T.bg,
              border:`1.5px solid ${T.borderMid}`, borderRadius:8, padding:"0 12px",
              gap:8, transition:"border-color .2s" }}
              onFocus={e => e.currentTarget.style.borderColor=T.brass}
              onBlur={e => e.currentTarget.style.borderColor=T.borderMid}>
              <span style={{ color:T.muted, fontSize:13 }}>🔍</span>
              <input
                value={query}
                onChange={handleQueryChange}
                onFocus={() => suggestions.length && setShowSugg(true)}
                placeholder="Company name or symbol…"
                style={{ flex:1, background:"transparent", border:"none", outline:"none",
                  color:T.text, fontSize:13, padding:"10px 0", fontFamily:"Work Sans,sans-serif" }}
              />
              {loading && (
                <div style={{ width:13, height:13, border:`2px solid ${T.brass}`,
                  borderTopColor:"transparent", borderRadius:"50%",
                  animation:"spin .8s linear infinite", flexShrink:0 }} />
              )}
            </div>
          </form>
          {/* Autocomplete dropdown */}
          {showSugg && suggestions.length > 0 && (
            <div style={{ position:"absolute", top:"100%", left:14, right:14, background:T.panel,
              border:`1px solid ${T.borderMid}`, borderRadius:8, zIndex:1000,
              boxShadow:"0 8px 24px rgba(27,36,48,0.12)", overflow:"hidden" }}>
              {suggestions.map(s => (
                <div key={s.symbol} onClick={() => analyzeStock(s.symbol, s.name)}
                  style={{ padding:"9px 14px", cursor:"pointer",
                    borderBottom:`1px solid ${T.border}`, display:"flex",
                    justifyContent:"space-between", alignItems:"center" }}
                  onMouseEnter={e => e.currentTarget.style.background=T.bg}
                  onMouseLeave={e => e.currentTarget.style.background=T.panel}>
                  <div>
                    <div style={{ fontSize:13, fontWeight:600, color:T.text }}>{s.name}</div>
                    <div style={{ fontSize:10.5, color:T.muted, marginTop:1,
                      fontFamily:"IBM Plex Mono,monospace" }}>{s.symbol}</div>
                  </div>
                  <span style={{ fontSize:9.5, color:T.brass, background:`${T.brass}18`,
                    borderRadius:4, padding:"2px 6px", fontWeight:700,
                    fontFamily:"IBM Plex Mono,monospace" }}>{s.exchange}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Watchlist */}
        <div style={{ flex:1, overflowY:"auto", padding:"0 8px 12px" }}>
          {watchlist.length === 0 ? (
            <div style={{ padding:"14px 12px", color:T.muted, fontSize:12, lineHeight:1.7 }}>
              Search any Indian stock above — like{" "}
              <span style={{ color:T.brass, fontWeight:600 }}>Infosys</span>,{" "}
              <span style={{ color:T.brass, fontWeight:600 }}>Zomato</span>, or{" "}
              <span style={{ color:T.brass, fontWeight:600 }}>IRCTC</span>.
            </div>
          ) : (
            <>
              <div style={{ fontSize:9.5, color:T.muted, textTransform:"uppercase",
                letterSpacing:1.5, fontWeight:700, padding:"8px 12px 4px",
                fontFamily:"IBM Plex Mono,monospace" }}>Analysed Stocks</div>
              {watchlist.map(s => {
                const cv  = conviction(s);
                const sel = selected?.symbol === s.symbol;
                return (
                  <div key={s.symbol}
                    onClick={() => { setSelected(s); setActiveTab("overview"); }}
                    style={{ display:"flex", alignItems:"center", gap:10, padding:"9px 12px",
                      borderRadius:8, cursor:"pointer", marginBottom:2,
                      background:sel ? `${T.brass}12` : "transparent",
                      border:sel ? `1px solid ${T.brass}44` : "1px solid transparent",
                      transition:"all .15s" }}>
                    <div style={{ width:34, height:34, borderRadius:8,
                      background:`${cv.color}15`, border:`1px solid ${cv.color}44`,
                      display:"flex", alignItems:"center", justifyContent:"center",
                      fontSize:13, fontWeight:800, color:cv.color, flexShrink:0,
                      fontFamily:"IBM Plex Mono,monospace" }}>
                      {(s.company_name || s.symbol).charAt(0)}
                    </div>
                    <div style={{ flex:1, minWidth:0 }}>
                      <div style={{ fontSize:12.5, fontWeight:600, color:T.text,
                        overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>
                        {s.company_name || s.symbol}
                      </div>
                      <div style={{ fontSize:11, color:T.muted, marginTop:1,
                        fontFamily:"IBM Plex Mono,monospace" }}>
                        {fmt.price(s.current_price)}{" "}
                        <span style={{ color:pctColor(s.day_change_percent) }}>
                          {fmt.pct(s.day_change_percent)}
                        </span>
                      </div>
                    </div>
                    <div style={{ fontSize:9, fontWeight:800, color:cv.color,
                      background:cv.bg, border:`1px solid ${cv.border}`,
                      borderRadius:4, padding:"2px 5px", textTransform:"uppercase",
                      letterSpacing:0.3, flexShrink:0, fontFamily:"IBM Plex Mono,monospace" }}>{cv.label}</div>
                  </div>
                );
              })}
            </>
          )}
        </div>
      </div>

      {/* ── MAIN AREA ──────────────────────────────────────────────────────── */}
      <div style={{ flex:1, display:"flex", flexDirection:"column", overflow:"hidden", position:"relative" }}>

        {/* Loading overlay */}
        {loading && (
          <div style={{ position:"absolute", inset:0, zIndex:800,
            background:"rgba(241,242,236,0.94)", backdropFilter:"blur(3px)",
            display:"flex", flexDirection:"column", alignItems:"center", justifyContent:"center", gap:18 }}>
            <div style={{ position:"relative", width:56, height:56 }}>
              <div style={{ position:"absolute", inset:0, border:`2px solid ${T.border}`, borderRadius:"50%" }} />
              <div style={{ position:"absolute", inset:0, border:`2px solid transparent`,
                borderTopColor:T.brass, borderRadius:"50%", animation:"spin 1s linear infinite" }} />
            </div>
            <div style={{ fontSize:15, color:T.brassDeep, fontWeight:700 }}>{loadingMsg}</div>
            <div style={{ fontSize:12, color:T.muted, maxWidth:320, textAlign:"center", lineHeight:1.6 }}>
              5 AI agents are researching fundamentals, technicals, news, macro conditions, and competitive positioning.
              This takes 45–90 seconds.
            </div>
          </div>
        )}

        {/* Error banner */}
        {error && !loading && (
          <div style={{ margin:"14px 20px 0", padding:"12px 16px", borderRadius:8,
            background:"#FBF0EE", border:`1px solid ${T.loss}44`,
            color:T.loss, fontSize:13, display:"flex",
            justifyContent:"space-between", alignItems:"center" }}>
            <span>⚠ {error}</span>
            <button onClick={() => setError(null)}
              style={{ background:"none", border:"none", color:T.muted,
                cursor:"pointer", fontSize:16, padding:0 }}>✕</button>
          </div>
        )}

        {/* Empty state */}
        {!selected && !loading && (
          <div style={{ flex:1, display:"flex", flexDirection:"column",
            alignItems:"center", justifyContent:"center", gap:18, padding:40 }}>
            <div style={{ fontFamily:"Instrument Serif,serif", fontSize:36,
              color:T.text, textAlign:"center", lineHeight:1.2 }}>
              Research any Indian stock<br/>
              <span style={{ color:T.brass }}>in minutes.</span>
            </div>
            <div style={{ fontSize:14, color:T.muted, maxWidth:440, textAlign:"center", lineHeight:1.75 }}>
              Type a company name in the search bar — our 5 AI agents will analyse
              fundamentals, technicals, news, macro conditions, and competitive position.
            </div>
            <div style={{ display:"flex", gap:8, flexWrap:"wrap", justifyContent:"center", marginTop:4 }}>
              {QUICK_SEARCHES.map(n => (
                <button key={n} onClick={() => analyzeStock(n, n)} style={{
                  padding:"7px 15px", borderRadius:20, fontSize:12.5, fontWeight:600,
                  background:T.panel, border:`1.5px solid ${T.borderMid}`,
                  color:T.muted, cursor:"pointer", transition:"all .15s",
                  fontFamily:"Work Sans,sans-serif",
                }}
                  onMouseEnter={e => { e.currentTarget.style.borderColor=T.brass; e.currentTarget.style.color=T.brass; }}
                  onMouseLeave={e => { e.currentTarget.style.borderColor=T.borderMid; e.currentTarget.style.color=T.muted; }}>
                  {n}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* ── STOCK DASHBOARD ────────────────────────────────────────────────── */}
        {selected && !loading && (
          <div style={{ flex:1, overflow:"hidden", display:"flex", flexDirection:"column" }}>

            {/* Header */}
            <div style={{ padding:"16px 24px 14px", borderBottom:`1px solid ${T.border}`,
              background:T.panel, flexShrink:0 }}>
              <div style={{ display:"flex", justifyContent:"space-between",
                alignItems:"flex-start", flexWrap:"wrap", gap:14 }}>
                <div>
                  <div style={{ display:"flex", alignItems:"center", gap:8, flexWrap:"wrap", marginBottom:3 }}>
                    <h1 style={{ margin:0, fontSize:22, fontWeight:700, color:T.text,
                      fontFamily:"Instrument Serif,serif" }}>
                      {selected.company_name || selected.symbol}
                    </h1>
                    <span style={{ fontSize:10.5, color:T.muted, background:T.bg,
                      border:`1px solid ${T.border}`, borderRadius:4, padding:"2px 7px",
                      fontFamily:"IBM Plex Mono,monospace" }}>{selected.symbol}</span>
                    <span style={{ fontSize:10.5, color:T.muted, background:T.bg,
                      border:`1px solid ${T.border}`, borderRadius:4, padding:"2px 7px",
                      fontFamily:"IBM Plex Mono,monospace" }}>{selected.exchange}</span>
                    {selected.data_source === "real-time" && (
                      <span style={{ fontSize:10, color:T.gain, background:"#E8F5EE",
                        border:"1px solid #A8D5BC", borderRadius:4, padding:"2px 7px",
                        fontWeight:700, fontFamily:"IBM Plex Mono,monospace" }}>● LIVE</span>
                    )}
                  </div>
                  <div style={{ fontSize:11.5, color:T.muted, marginBottom:8 }}>
                    {selected.sector}{selected.industry ? ` · ${selected.industry}` : ""}
                  </div>
                  <div style={{ display:"flex", alignItems:"baseline", gap:10 }}>
                    <span style={{ fontSize:32, fontWeight:800, color:T.text,
                      fontFamily:"IBM Plex Mono,monospace" }}>{fmt.price(selected.current_price)}</span>
                    <span style={{ fontSize:14, fontWeight:700,
                      color:pctColor(selected.day_change_percent) }}>
                      {selected.day_change >= 0 ? "+" : ""}{fmt.price(selected.day_change)}{" "}
                      ({fmt.pct(selected.day_change_percent)})
                    </span>
                  </div>
                </div>

                {/* Verdict badge */}
                {conv && (
                  <div style={{ padding:"14px 20px", background:conv.bg,
                    border:`1px solid ${conv.border}`,
                    borderRadius:10, textAlign:"center", minWidth:130 }}>
                    <div style={{ fontSize:9.5, color:T.muted, textTransform:"uppercase",
                      letterSpacing:1.5, fontWeight:700, fontFamily:"IBM Plex Mono,monospace" }}>AI Verdict</div>
                    <div style={{ fontSize:17, fontWeight:800, color:conv.color,
                      letterSpacing:0.3, marginTop:5, fontFamily:"IBM Plex Mono,monospace" }}>{conv.label}</div>
                    <div style={{ fontSize:10, color:T.muted, marginTop:2 }}>
                      {selected.synthesis?.conviction} conviction
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Tab bar */}
            <div style={{ display:"flex", borderBottom:`1px solid ${T.border}`,
              background:T.panel, flexShrink:0, paddingLeft:24, overflowX:"auto" }}>
              {[
                { id:"overview",   label:"Overview" },
                { id:"research",   label:"Research Report" },
                { id:"pillars",    label:"Pillar Analysis" },
                { id:"technicals", label:"Technicals" },
              ].map(tab => (
                <button key={tab.id} onClick={() => setActiveTab(tab.id)} style={{
                  padding:"10px 18px", background:"none", border:"none", cursor:"pointer",
                  borderBottom:`2px solid ${activeTab===tab.id ? T.brass : "transparent"}`,
                  color:activeTab===tab.id ? T.brass : T.muted,
                  fontWeight:activeTab===tab.id ? 700 : 500,
                  fontSize:13, whiteSpace:"nowrap", marginBottom:-1,
                  fontFamily:"Work Sans,sans-serif", transition:"all .15s",
                }}>{tab.label}</button>
              ))}
            </div>

            {/* Tab content */}
            <div style={{ flex:1, overflowY:"auto", padding:"20px 24px" }}>

              {/* ── OVERVIEW ── */}
              {activeTab === "overview" && (
                <div style={{ display:"grid", gridTemplateColumns:"1fr 260px", gap:18, maxWidth:1080 }}>
                  <div>
                    {/* 30-day price chart */}
                    <div style={{ background:T.panel, border:`1px solid ${T.border}`,
                      borderRadius:10, padding:"16px 20px", marginBottom:16,
                      boxShadow:"0 1px 3px rgba(27,36,48,0.04)" }}>
                      <div style={{ fontSize:10.5, color:T.muted, fontWeight:700, letterSpacing:1,
                        textTransform:"uppercase", marginBottom:12,
                        fontFamily:"IBM Plex Mono,monospace" }}>30-Day Price Chart</div>
                      {selected.sparkline?.length >= 2 ? (
                        <ResponsiveContainer width="100%" height={160}>
                          <LineChart data={selected.sparkline.map((v,i) => ({ d:i+1, p:v }))}>
                            <XAxis dataKey="d" hide />
                            <YAxis domain={["auto","auto"]} hide />
                            <Tooltip
                              contentStyle={{ background:T.panel, border:`1px solid ${T.border}`,
                                borderRadius:6, fontSize:12, fontFamily:"IBM Plex Mono,monospace" }}
                              formatter={v => [fmt.price(v), "Price"]}
                              labelFormatter={l => `Day ${l}`} />
                            <Line type="monotone" dataKey="p"
                              stroke={pctColor(selected.day_change_percent)}
                              strokeWidth={2} dot={false} />
                          </LineChart>
                        </ResponsiveContainer>
                      ) : (
                        <div style={{ height:160, display:"flex", alignItems:"center",
                          justifyContent:"center", color:T.muted, fontSize:13 }}>
                          Price history not available for this stock
                        </div>
                      )}
                    </div>

                    {/* Metrics grid */}
                    <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill,minmax(120px,1fr))", gap:10, marginBottom:16 }}>
                      <MetricCell label="Market Cap" value={fmt.mcap(selected.market_cap)} />
                      <MetricCell label="Volume" value={fmt.vol(selected.volume)} />
                      <MetricCell label="Prev Close" value={fmt.price(selected.prev_close)} />
                      <MetricCell label="Open" value={fmt.price(selected.open)} />
                      <MetricCell label="Day Range" value={selected.day_range || "—"} />
                      <MetricCell label="52W Change" value={fmt.pct(selected.year_change_pct)} color={pctColor(selected.year_change_pct)} />
                      <MetricCell label="P/E Ratio" value={fmt.num(pillars.fundamentals?.metrics?.pe_ratio)} />
                      <MetricCell label="P/B Ratio" value={fmt.num(pillars.fundamentals?.metrics?.pb_ratio)} />
                      <MetricCell label="ROE" value={pillars.fundamentals?.metrics?.roe ? `${fmt.num(pillars.fundamentals.metrics.roe)}%` : "—"} />
                      <MetricCell label="D/E Ratio" value={fmt.num(pillars.fundamentals?.metrics?.debt_to_equity)} />
                      <MetricCell label="Div Yield" value={pillars.fundamentals?.metrics?.dividend_yield ? `${fmt.num(pillars.fundamentals.metrics.dividend_yield)}%` : "—"} />
                      <MetricCell label="EPS" value={pillars.fundamentals?.metrics?.eps ? fmt.price(pillars.fundamentals.metrics.eps) : "—"} />
                      <MetricCell label="RSI (14)"
                        value={fmt.num(pillars.technical?.metrics?.rsi, 1)}
                        color={pillars.technical?.metrics?.rsi > 70 ? T.loss : pillars.technical?.metrics?.rsi < 30 ? T.gain : T.brass} />
                      <MetricCell label="SMA 20" value={fmt.price(pillars.technical?.metrics?.sma_20)} />
                      <MetricCell label="SMA 50" value={fmt.price(pillars.technical?.metrics?.sma_50)} />
                    </div>

                    {/* Key takeaways */}
                    {selected.synthesis?.key_takeaways?.length > 0 && (
                      <div style={{ background:`${T.brass}0D`, border:`1px solid ${T.brass}33`,
                        borderRadius:10, padding:"16px 20px" }}>
                        <div style={{ fontSize:10.5, color:T.brassDeep, fontWeight:700, letterSpacing:1,
                          textTransform:"uppercase", marginBottom:10,
                          fontFamily:"IBM Plex Mono,monospace" }}>Key Takeaways</div>
                        {selected.synthesis.key_takeaways.map((t,i) => (
                          <div key={i} style={{ display:"flex", gap:10, color:T.text,
                            fontSize:13, lineHeight:1.65, marginBottom:6 }}>
                            <span style={{ color:T.brass, flexShrink:0 }}>→</span>{t}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Right column */}
                  <div>
                    {/* Radar + score bars */}
                    <div style={{ background:T.panel, border:`1px solid ${T.border}`,
                      borderRadius:10, padding:"14px 14px 12px",
                      marginBottom:14, boxShadow:"0 1px 3px rgba(27,36,48,0.04)" }}>
                      <div style={{ fontSize:10.5, color:T.muted, fontWeight:700, letterSpacing:1,
                        textTransform:"uppercase", marginBottom:6,
                        fontFamily:"IBM Plex Mono,monospace" }}>Signal Radar</div>
                      <RadarChart cx="50%" cy="50%" outerRadius="68%" width={232} height={190}
                        data={PILLARS.map(({ key, label }) => ({
                          subject: label.split(" ")[0],
                          score: (pillars[key]?.score || 5) * 10,
                          fullMark: 100,
                        }))}>
                        <PolarGrid stroke={T.border} />
                        <PolarAngleAxis dataKey="subject"
                          tick={{ fill:T.muted, fontSize:10, fontFamily:"Work Sans,sans-serif" }} />
                        <PolarRadiusAxis angle={90} domain={[0,100]} tick={false} axisLine={false} />
                        <Radar dataKey="score" stroke={T.brass} fill={T.brass} fillOpacity={0.15} strokeWidth={2} />
                      </RadarChart>
                      <div style={{ paddingTop:6 }}>
                        {PILLARS.map(({ key, label }) => (
                          <PillarScoreRow key={key} label={label.split(" ")[0]} pillar={pillars[key]} />
                        ))}
                      </div>
                    </div>

                    {/* Conflicts */}
                    {selected.synthesis?.conflicts?.length > 0 && (
                      <div style={{ background:"#FBF5E8", border:`1px solid #E0C882`,
                        borderRadius:10, padding:"12px 14px", marginBottom:12 }}>
                        <div style={{ fontSize:10.5, color:"#7A5C1A", fontWeight:700, letterSpacing:1,
                          textTransform:"uppercase", marginBottom:8,
                          fontFamily:"IBM Plex Mono,monospace" }}>⚡ Signal Conflicts</div>
                        {selected.synthesis.conflicts.map((c,i) => (
                          <div key={i} style={{ marginBottom:10 }}>
                            <div style={{ fontSize:11, fontWeight:700, color:"#7A5C1A", marginBottom:3,
                              fontFamily:"IBM Plex Mono,monospace" }}>
                              {(c.type||"Conflict").replace(/_/g," ").toUpperCase()}
                            </div>
                            <div style={{ fontSize:12, color:T.text, lineHeight:1.55 }}>{c.description}</div>
                            {c.implication && (
                              <div style={{ fontSize:11, color:"#7A5C1A", marginTop:4, fontStyle:"italic" }}>
                                → {c.implication}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Time horizon */}
                    {selected.synthesis?.time_horizon_guidance && (
                      <div style={{ background:T.panel, border:`1px solid ${T.border}`,
                        borderRadius:10, padding:"12px 14px" }}>
                        <div style={{ fontSize:10.5, color:T.muted, fontWeight:700, letterSpacing:1,
                          textTransform:"uppercase", marginBottom:10,
                          fontFamily:"IBM Plex Mono,monospace" }}>Time Horizon</div>
                        {Object.entries(selected.synthesis.time_horizon_guidance).map(([h,t]) => (
                          <div key={h} style={{ display:"flex", gap:8, marginBottom:8 }}>
                            <span style={{ fontSize:9.5, fontWeight:800, color:T.brass,
                              textTransform:"uppercase", minWidth:60, paddingTop:1,
                              fontFamily:"IBM Plex Mono,monospace" }}>{h.replace("_"," ")}</span>
                            <span style={{ fontSize:12, color:T.muted, lineHeight:1.55, flex:1 }}>{t}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* ── RESEARCH REPORT ── */}
              {activeTab === "research" && (
                <div style={{ maxWidth:760 }}>
                  {selected.synthesis?.thesis && (
                    <div style={{ background:conv?.bg, border:`1px solid ${conv?.border}`,
                      borderLeft:`4px solid ${conv?.color}`,
                      borderRadius:10, padding:"18px 22px", marginBottom:22 }}>
                      <div style={{ fontSize:10, color:T.muted, fontWeight:700, letterSpacing:1.5,
                        textTransform:"uppercase", marginBottom:8,
                        fontFamily:"IBM Plex Mono,monospace" }}>Investment Thesis</div>
                      <p style={{ margin:0, fontSize:15, color:T.text, lineHeight:1.8,
                        fontWeight:500, fontFamily:"Instrument Serif,serif" }}>
                        {selected.synthesis.thesis}
                      </p>
                    </div>
                  )}

                  {selected.synthesis?.signal_summary && (
                    <div style={{ display:"flex", gap:12, marginBottom:22 }}>
                      {[
                        { l:"Bullish Signals", v:selected.synthesis.signal_summary.bullish_count, c:T.gain },
                        { l:"Neutral",         v:selected.synthesis.signal_summary.neutral_count, c:T.muted },
                        { l:"Bearish Signals", v:selected.synthesis.signal_summary.bearish_count, c:T.loss },
                      ].map(s => (
                        <div key={s.l} style={{ flex:1, background:T.panel,
                          border:`1px solid ${T.border}`, borderRadius:10,
                          padding:"14px 16px", textAlign:"center" }}>
                          <div style={{ fontSize:28, fontWeight:800, color:s.c,
                            fontFamily:"IBM Plex Mono,monospace" }}>{s.v}</div>
                          <div style={{ fontSize:11, color:T.muted, marginTop:3 }}>{s.l}</div>
                        </div>
                      ))}
                    </div>
                  )}

                  {selected.synthesis?.final_report && (
                    <div style={{ marginBottom:24 }}>
                      <div style={{ fontSize:10.5, color:T.muted, fontWeight:700, letterSpacing:1,
                        textTransform:"uppercase", marginBottom:14,
                        fontFamily:"IBM Plex Mono,monospace" }}>Full Research Report</div>
                      {selected.synthesis.final_report.split("\n\n").filter(Boolean).map((para,i) => (
                        <p key={i} style={{ color:T.text, fontSize:14, lineHeight:1.85, marginBottom:16 }}>{para}</p>
                      ))}
                    </div>
                  )}

                  {/* Macro tailwinds/headwinds */}
                  {pillars.macro && (
                    <div style={{ marginBottom:20 }}>
                      <div style={{ fontSize:10.5, color:T.muted, fontWeight:700, letterSpacing:1,
                        textTransform:"uppercase", marginBottom:10, fontFamily:"IBM Plex Mono,monospace" }}>
                        Macro Environment</div>
                      <div style={{ background:T.panel, border:`1px solid ${T.border}`,
                        borderLeft:`3px solid ${sigColor(pillars.macro.signal)}`,
                        borderRadius:10, padding:"14px 18px" }}>
                        <p style={{ color:T.text, fontSize:14, lineHeight:1.8, margin:0 }}>{pillars.macro.summary}</p>
                        <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:12, marginTop:12 }}>
                          {pillars.macro.tailwinds?.length > 0 && (
                            <div>
                              <div style={{ fontSize:10, color:T.gain, fontWeight:700, marginBottom:5,
                                fontFamily:"IBM Plex Mono,monospace" }}>TAILWINDS</div>
                              {pillars.macro.tailwinds.map((t,i) => (
                                <div key={i} style={{ fontSize:12, color:T.text, marginBottom:3 }}>✓ {t}</div>
                              ))}
                            </div>
                          )}
                          {pillars.macro.headwinds?.length > 0 && (
                            <div>
                              <div style={{ fontSize:10, color:T.loss, fontWeight:700, marginBottom:5,
                                fontFamily:"IBM Plex Mono,monospace" }}>HEADWINDS</div>
                              {pillars.macro.headwinds.map((h,i) => (
                                <div key={i} style={{ fontSize:12, color:T.text, marginBottom:3 }}>✗ {h}</div>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* News sentiment */}
                  {pillars.news_sentiment && (
                    <div style={{ marginBottom:20 }}>
                      <div style={{ fontSize:10.5, color:T.muted, fontWeight:700, letterSpacing:1,
                        textTransform:"uppercase", marginBottom:10, fontFamily:"IBM Plex Mono,monospace" }}>
                        News & Sentiment</div>
                      <div style={{ background:T.panel, border:`1px solid ${T.border}`,
                        borderLeft:`3px solid ${sigColor(pillars.news_sentiment.signal)}`,
                        borderRadius:10, padding:"14px 18px" }}>
                        <p style={{ color:T.text, fontSize:14, lineHeight:1.8, margin:0 }}>{pillars.news_sentiment.summary}</p>
                        {pillars.news_sentiment.top_headlines?.length > 0 && (
                          <div style={{ marginTop:12, paddingTop:12, borderTop:`1px solid ${T.border}` }}>
                            <div style={{ fontSize:10, color:T.muted, fontWeight:700, marginBottom:6,
                              fontFamily:"IBM Plex Mono,monospace" }}>RECENT HEADLINES</div>
                            {pillars.news_sentiment.top_headlines.map((h,i) => (
                              <div key={i} style={{ display:"flex", justifyContent:"space-between",
                                marginBottom:5, gap:8 }}>
                                <span style={{ fontSize:12, color:T.muted }}>{h.title || h}</span>
                                {h.sentiment && <span style={{ fontSize:10, flexShrink:0,
                                  color:sigColor(h.sentiment==="positive"?"bullish":h.sentiment==="negative"?"bearish":"neutral") }}>
                                  {h.sentiment}</span>}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Competitive */}
                  {pillars.competitive && (
                    <div style={{ marginBottom:24 }}>
                      <div style={{ fontSize:10.5, color:T.muted, fontWeight:700, letterSpacing:1,
                        textTransform:"uppercase", marginBottom:10, fontFamily:"IBM Plex Mono,monospace" }}>
                        Competitive Position</div>
                      <div style={{ background:T.panel, border:`1px solid ${T.border}`,
                        borderLeft:`3px solid ${sigColor(pillars.competitive.signal)}`,
                        borderRadius:10, padding:"14px 18px" }}>
                        {pillars.competitive.company_position && (
                          <div style={{ fontSize:12, color:T.brass, fontWeight:700, marginBottom:6 }}>
                            Market Position: {pillars.competitive.company_position}
                          </div>
                        )}
                        <p style={{ color:T.text, fontSize:14, lineHeight:1.8, margin:0 }}>{pillars.competitive.summary}</p>
                        <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:12, marginTop:12 }}>
                          {pillars.competitive.competitive_advantages?.length > 0 && (
                            <div>
                              <div style={{ fontSize:10, color:T.gain, fontWeight:700, marginBottom:5,
                                fontFamily:"IBM Plex Mono,monospace" }}>ADVANTAGES</div>
                              {pillars.competitive.competitive_advantages.map((a,i) => (
                                <div key={i} style={{ fontSize:12, color:T.text, marginBottom:3 }}>✓ {a}</div>
                              ))}
                            </div>
                          )}
                          {pillars.competitive.competitive_risks?.length > 0 && (
                            <div>
                              <div style={{ fontSize:10, color:T.loss, fontWeight:700, marginBottom:5,
                                fontFamily:"IBM Plex Mono,monospace" }}>RISKS</div>
                              {pillars.competitive.competitive_risks.map((r,i) => (
                                <div key={i} style={{ fontSize:12, color:T.text, marginBottom:3 }}>✗ {r}</div>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  )}

                  <div style={{ background:T.bg, border:`1px solid ${T.border}`, borderRadius:8,
                    padding:"10px 14px", fontSize:11, color:T.muted, lineHeight:1.6 }}>
                    ⚠ This research is generated by AI for informational purposes only and does not constitute
                    financial or investment advice. Always consult a qualified financial advisor before investing.
                  </div>
                </div>
              )}

              {/* ── PILLAR ANALYSIS ── */}
              {activeTab === "pillars" && (
                <div style={{ maxWidth:720 }}>
                  <div style={{ fontSize:12, color:T.muted, marginBottom:14, lineHeight:1.6 }}>
                    Each pillar is independently analysed by a dedicated AI agent. Click any card to expand.
                  </div>
                  {PILLARS.map(({ key, label, icon }) => (
                    <PillarCard key={key} title={label} icon={icon} data={pillars[key]} />
                  ))}
                  {selected.agent_trace?.length > 0 && (
                    <div style={{ background:T.panel, border:`1px solid ${T.border}`,
                      borderRadius:10, padding:"14px 16px", marginTop:4 }}>
                      <div style={{ fontSize:10, color:T.muted, fontWeight:700, textTransform:"uppercase",
                        letterSpacing:1, marginBottom:8, fontFamily:"IBM Plex Mono,monospace" }}>Agent Performance</div>
                      <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill,minmax(140px,1fr))", gap:8 }}>
                        {selected.agent_trace.map((a,i) => (
                          <div key={i} style={{ fontSize:11, color:T.muted, fontFamily:"IBM Plex Mono,monospace" }}>
                            <span style={{ color:T.text, fontWeight:600 }}>{a.agent}</span>
                            <span style={{ marginLeft:6 }}>{(a.duration_ms/1000).toFixed(1)}s</span>
                          </div>
                        ))}
                        <div style={{ fontSize:11, color:T.muted, fontFamily:"IBM Plex Mono,monospace" }}>
                          Total: {(selected.total_duration_ms/1000).toFixed(1)}s
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* ── TECHNICALS ── */}
              {activeTab === "technicals" && (
                <div style={{ maxWidth:720 }}>
                  <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill,minmax(148px,1fr))", gap:12, marginBottom:20 }}>
                    {(() => {
                      const m = pillars.technical?.metrics || {};
                      const p = selected.current_price;
                      return [
                        { l:"RSI (14)",    v:m.rsi ? fmt.num(m.rsi,1) : "—",
                          note: m.rsi>70 ? "⚠ Overbought" : m.rsi<30 ? "✓ Oversold" : "Neutral",
                          c: m.rsi>70 ? T.loss : m.rsi<30 ? T.gain : T.brass },
                        { l:"MACD",       v:m.macd ? fmt.num(m.macd) : "—",
                          note: m.macd>m.macd_signal ? "Bullish crossover" : "Bearish crossover",
                          c: m.macd>m.macd_signal ? T.gain : T.loss },
                        { l:"MACD Signal",v:m.macd_signal ? fmt.num(m.macd_signal) : "—", note:"", c:T.muted },
                        { l:"SMA 20",     v:m.sma_20 ? fmt.price(m.sma_20) : "—",
                          note: p>m.sma_20 ? "Price above ↑" : "Price below ↓",
                          c: p>m.sma_20 ? T.gain : T.loss },
                        { l:"SMA 50",     v:m.sma_50 ? fmt.price(m.sma_50) : "—",
                          note: p>m.sma_50 ? "Price above ↑" : "Price below ↓",
                          c: p>m.sma_50 ? T.gain : T.loss },
                        { l:"BB Upper",   v:m.bb_upper ? fmt.price(m.bb_upper) : "—",
                          note:"Resistance", c:T.loss },
                        { l:"BB Middle",  v:m.bb_middle ? fmt.price(m.bb_middle) : "—",
                          note:"Fair value", c:T.muted },
                        { l:"BB Lower",   v:m.bb_lower ? fmt.price(m.bb_lower) : "—",
                          note:"Support", c:T.gain },
                      ];
                    })().map(item => (
                      <div key={item.l} style={{ background:T.panel, border:`1px solid ${T.border}`,
                        borderRadius:10, padding:"14px 16px",
                        boxShadow:"0 1px 3px rgba(27,36,48,0.04)" }}>
                        <div style={{ fontSize:10, color:T.muted, textTransform:"uppercase",
                          letterSpacing:0.5, marginBottom:6, fontFamily:"IBM Plex Mono,monospace" }}>{item.l}</div>
                        <div style={{ fontSize:19, fontWeight:800, color:item.c,
                          fontFamily:"IBM Plex Mono,monospace" }}>{item.v}</div>
                        {item.note && (
                          <div style={{ fontSize:11, color:T.muted, marginTop:5 }}>{item.note}</div>
                        )}
                      </div>
                    ))}
                  </div>
                  {pillars.technical?.summary && (
                    <div style={{ background:T.panel, border:`1px solid ${T.border}`,
                      borderLeft:`3px solid ${sigColor(pillars.technical.signal)}`,
                      borderRadius:10, padding:"16px 20px", marginBottom:14 }}>
                      <div style={{ fontSize:10, color:T.muted, fontWeight:700, textTransform:"uppercase",
                        letterSpacing:1, marginBottom:8, fontFamily:"IBM Plex Mono,monospace" }}>Summary</div>
                      <p style={{ color:T.text, fontSize:14, lineHeight:1.8, margin:0 }}>{pillars.technical.summary}</p>
                    </div>
                  )}
                  {pillars.technical?.key_insights?.map((ins,i) => (
                    <div key={i} style={{ display:"flex", gap:10, padding:"10px 14px",
                      background:T.panel, border:`1px solid ${T.border}`, borderRadius:8,
                      fontSize:13, color:T.text, marginBottom:6 }}>
                      <span style={{ color:sigColor(pillars.technical.signal) }}>•</span>{ins}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      <style>{`
        @keyframes spin { to { transform:rotate(360deg); } }
        *, *::before, *::after { box-sizing:border-box; }
        button { font-family:inherit; }
      `}</style>
    </div>
  );
}
