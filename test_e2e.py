"""
EquiSage End-to-End Test Script
Tests multiple NSE stocks and reports results.
"""
import requests
import json
import time
import sys

BASE = "http://localhost:8000"

def test_health():
    r = requests.get(f"{BASE}/api/health", timeout=10)
    h = r.json()
    print(f"Health: {h['status']} | Gemini key: {h['gemini_api_key_configured']} | Agents: {len(h['agents'])}")
    return r.status_code == 200

def test_popular():
    r = requests.get(f"{BASE}/api/popular", timeout=10)
    data = r.json()
    stocks = data.get("stocks", [])
    print(f"Popular stocks: {len(stocks)} loaded -> {[s['symbol'] for s in stocks[:4]]}")
    return len(stocks) > 0

def test_research(symbol):
    print(f"\n{'='*50}")
    print(f"  Testing: {symbol}")
    print(f"{'='*50}")
    t0 = time.time()
    try:
        r = requests.post(f"{BASE}/api/research",
            json={"symbol": symbol}, timeout=300)
        elapsed = time.time() - t0
        
        if r.status_code != 200:
            print(f"  ERROR {r.status_code}: {r.text[:200]}")
            return False

        d = r.json()
        pillars = d.get("pillars", {})
        synthesis = d.get("synthesis", {})
        compliance = d.get("compliance", {})
        trace = d.get("agent_trace", [])
        
        print(f"  Company:    {d.get('company_name', 'N/A')}")
        print(f"  Sector:     {d.get('sector', 'N/A')}")
        print(f"  Price:      Rs {d.get('current_price', 0):.2f}")
        print(f"  Change:     {d.get('day_change_percent', 0):.2f}%")
        print(f"  MCap:       {d.get('market_cap', 0)/1e9:.1f}B")
        print(f"  Source:     {d.get('data_source', 'N/A')}")
        print(f"  Duration:   {elapsed:.1f}s")
        print()
        print(f"  Conviction: {synthesis.get('conviction', 'N/A')}")
        print(f"  Thesis:     {str(synthesis.get('thesis', ''))[:120]}")
        print()
        
        signals = {"bullish":0,"neutral":0,"bearish":0}
        for name, p in pillars.items():
            sig = p.get("signal","neutral")
            sc  = p.get("score", 5)
            summary_short = str(p.get("summary",""))[:80]
            print(f"  [{name:<15}] score={sc}/10  signal={sig:<8}  {summary_short}")
            signals[sig] = signals.get(sig,0) + 1
        
        print(f"\n  Signal summary: {signals}")
        print(f"  Conflicts:  {len(synthesis.get('conflicts', []))}")
        print(f"  Compliant:  {compliance.get('compliant', 'N/A')}")
        print(f"  Takeaways:  {len(synthesis.get('key_takeaways', []))}")
        
        # Check for issues
        issues = []
        for name, p in pillars.items():
            if "AI analysis failed" in str(p.get("summary", "")) or "unavailable" in str(p.get("summary","")).lower():
                issues.append(f"{name}: LLM failed")
            if not p.get("summary") or len(p.get("summary","")) < 20:
                issues.append(f"{name}: empty summary")
        
        if issues:
            print(f"\n  ⚠ Issues found:")
            for iss in issues:
                print(f"    - {iss}")
        else:
            print(f"\n  ✓ All pillars have valid AI analysis")
        
        return len(issues) == 0

    except Exception as e:
        print(f"  EXCEPTION: {e}")
        return False

if __name__ == "__main__":
    print("\nEquiSage E2E Test Suite")
    print("="*50)
    
    if not test_health():
        print("Backend not running!")
        sys.exit(1)
    
    test_popular()
    
    test_stocks = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS"]
    results = {}
    
    for sym in test_stocks:
        ok = test_research(sym)
        results[sym] = "PASS" if ok else "FAIL"
        if sym != test_stocks[-1]:
            print(f"\n  Waiting 10s before next stock to respect rate limits...")
            time.sleep(10)
    
    print(f"\n{'='*50}")
    print("TEST RESULTS:")
    for sym, res in results.items():
        icon = "✓" if res == "PASS" else "✗"
        print(f"  {icon} {sym}: {res}")
    
    passed = sum(1 for r in results.values() if r == "PASS")
    print(f"\n{passed}/{len(results)} tests passed")
