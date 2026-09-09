import { useState, useCallback, useRef, useEffect } from 'react'
import ConfigPanel   from './components/ConfigPanel.jsx'
import LoadingState  from './components/LoadingState.jsx'
import Dashboard     from './components/Dashboard.jsx'
import MealCard      from './components/MealCard.jsx'
import MealModal     from './components/MealModal.jsx'
import BasketReview  from './components/BasketReview.jsx'

const API_BASE = import.meta.env.VITE_API_URL ?? ''
const STORAGE_KEY = 'mealplanner_session'

// ── localStorage helpers ────────────────────────────────────────────────────
function saveSession(plan, basket, config) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      plan, basket, config, savedAt: Date.now()
    }))
  } catch (_) {}
}

function loadSession() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const s = JSON.parse(raw)
    // No expiry — plan stays until user clicks "Plan New Week"
    return s
  } catch (_) { return null }
}

function clearSession() {
  try { localStorage.removeItem(STORAGE_KEY) } catch (_) {}
}

// status flow:  idle → basket_loading → basket_review → loading → done | error
const STAGE_DURATIONS = [3000, 3000, 14000, 2000]

export default function App() {
  const [status,       setStatus]       = useState('idle')
  const [loadingStage, setLoadingStage] = useState(0)
  const [plan,         setPlan]         = useState(null)
  const [config,       setConfig]       = useState(null)
  const [basket,       setBasket]       = useState(null)
  const [errorMsg,     setErrorMsg]     = useState('')
  const [selectedMeal, setSelectedMeal] = useState(null)
  const [restored,     setRestored]     = useState(false) // show "restored" banner

  const latestConfig = useRef(null)

  // ── Restore last session from localStorage on first load ────────────────
  useEffect(() => {
    const s = loadSession()
    if (s?.plan && s?.basket && s?.config) {
      setPlan(s.plan)
      setBasket(s.basket)
      setConfig(s.config)
      latestConfig.current = s.config
      setStatus('done')
      setRestored(s.savedAt ? new Date(s.savedAt).toLocaleDateString('en-GB', { weekday:'short', day:'numeric', month:'short', hour:'2-digit', minute:'2-digit' }) : true)
    }
  }, [])

  // ── Stage ticker for loading screen ────────────────────────────────
  function startStageTicker(abortRef) {
    let stage = 1
    setLoadingStage(1)
    function tick() {
      if (abortRef.aborted || stage >= 4) return
      stage++
      setLoadingStage(stage)
      if (stage < 4) abortRef.timer = setTimeout(tick, STAGE_DURATIONS[stage - 1])
    }
    abortRef.timer = setTimeout(tick, STAGE_DURATIONS[0])
  }

  // ── Step 1: build the shopping basket ──────────────────────────────
  const handleBuildBasket = useCallback(async (formValues) => {
    setConfig(formValues)
    setStatus('basket_loading')
    setErrorMsg('')

    try {
      const res = await fetch(`${API_BASE}/build-basket`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({
          budget:   formValues.budget,
          diet:     formValues.diet,
          days:     formValues.days,
          servings: formValues.servings,
        }),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }))
        throw new Error(err.detail || `HTTP ${res.status}`)
      }
      const data = await res.json()
      setBasket(data)
      setStatus('basket_review')

      // Store formValues in a ref so handleConfirmBasket always gets the
      // exact values the user submitted, not a potentially-stale state copy.
      latestConfig.current = formValues
    } catch (err) {
      setErrorMsg(err.message || 'Unknown error')
      setStatus('error')
    }
  }, [])

  // ── Step 2: generate plan from confirmed basket ─────────────────────
  const handleConfirmBasket = useCallback(async (basketItems) => {
    // Always read from the ref — guaranteed to be the latest submitted values
    const cfg = latestConfig.current
    if (!cfg) return

    setStatus('loading')
    setLoadingStage(0)
    setPlan(null)

    const abortRef = { aborted: false, timer: null }
    startStageTicker(abortRef)

    try {
      const res = await fetch(`${API_BASE}/generate-plan`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ ...cfg, basket_items: basketItems }),
      })
      abortRef.aborted = true
      clearTimeout(abortRef.timer)

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }))
        throw new Error(err.detail || `HTTP ${res.status}`)
      }

      const data = await res.json()
      setLoadingStage(4)
      await new Promise(r => setTimeout(r, 600))
      setPlan(data)
      setStatus('done')
      saveSession(data, basket, cfg)  // persist for reload
    } catch (err) {
      abortRef.aborted = true
      clearTimeout(abortRef.timer)
      setErrorMsg(err.message || 'Unknown error')
      setStatus('error')
    }
  }, [])

  const allMeals  = plan?.meal_plan?.flatMap(d => d.meals) ?? []
  const mealCount = allMeals.length

  return (
    <div className="min-h-screen flex flex-col" style={{ background: '#e8ede8' }}>

      {/* ── Nav ─────────────────────────────────────────────────────── */}
      <header className="flex items-center justify-between px-6 py-4"
              style={{ borderBottom: '1px solid rgba(45,106,79,0.18)',
                       background: 'rgba(255,255,255,0.6)', backdropFilter: 'blur(12px)' }}>
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl flex items-center justify-center text-xl"
               style={{ background: 'linear-gradient(135deg,#2d6a4f,#40916c)',
                        boxShadow: '0 0 14px rgba(45,106,79,0.4)' }}>
            🛒
          </div>
          <div>
            <h1 className="font-bold text-sm leading-none tracking-wide">
              <span className="gradient-text">Meal Planner</span>
            </h1>
            <p className="text-[10px] font-mono mt-0.5" style={{ color: '#6b8f6b' }}>
              AI-Powered · Budget Cooking
            </p>
          </div>
        </div>

        {/* Status pill */}
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-mono border"
             style={
               status === 'done'           ? { background:'rgba(45,106,79,0.1)',  borderColor:'rgba(45,106,79,0.35)',  color:'#2d6a4f' } :
               status === 'loading'        ? { background:'rgba(64,145,108,0.1)', borderColor:'rgba(64,145,108,0.35)', color:'#40916c' } :
               status === 'basket_loading' ? { background:'rgba(116,198,157,0.1)',borderColor:'rgba(116,198,157,0.35)',color:'#2d6a4f' } :
               status === 'basket_review'  ? { background:'rgba(45,106,79,0.08)', borderColor:'rgba(45,106,79,0.3)',   color:'#2d6a4f' } :
               status === 'error'          ? { background:'rgba(220,38,38,0.08)', borderColor:'rgba(220,38,38,0.3)',   color:'#dc2626' } :
                                             { background:'rgba(107,143,107,0.1)',borderColor:'rgba(107,143,107,0.3)', color:'#6b8f6b' }
             }>
          <span className="w-1.5 h-1.5 rounded-full"
                style={{ background:
                  status === 'done'           ? '#2d6a4f' :
                  status === 'loading'        ? '#40916c' :
                  status === 'basket_loading' ? '#74c69d' :
                  status === 'basket_review'  ? '#2d6a4f' :
                  status === 'error'          ? '#dc2626' : '#a8c5a8',
                  animation: (status==='loading'||status==='basket_loading') ? 'pulse 1.5s infinite' : 'none'
                }} />
          {status === 'idle'           && 'Ready'}
          {status === 'basket_loading' && 'Building basket…'}
          {status === 'basket_review'  && `${basket?.items ?? 0} items in basket`}
          {status === 'loading'        && 'Generating…'}
          {status === 'done'           && `${mealCount} meals planned`}
          {status === 'error'          && 'Error'}
        </div>
      </header>

      {/* ── Main layout ──────────────────────────────────────────────── */}
      <div className="flex flex-col lg:flex-row gap-6 p-6 flex-1 min-h-0">

        {/* Config panel — hidden during basket review / loading / done */}
        {(status === 'idle' || status === 'error') && (
          <ConfigPanel onGenerate={handleBuildBasket} loading={false} />
        )}

        <main className="flex-1 flex flex-col gap-6 min-w-0">

          {/* IDLE */}
          {status === 'idle' && (
            <div className="flex-1 flex flex-col items-center justify-center gap-8 py-20">
              <div className="relative">
                <div className="w-28 h-28 rounded-3xl flex items-center justify-center text-5xl"
                     style={{ background: 'linear-gradient(135deg, rgba(45,106,79,0.15), rgba(64,145,108,0.1))',
                              border: '1px solid rgba(45,106,79,0.25)',
                              boxShadow: '0 0 32px rgba(45,106,79,0.15)' }}>
                  🛒
                </div>
                <div className="absolute -inset-3 rounded-full animate-ping-slow"
                     style={{ border: '1px solid rgba(45,106,79,0.2)' }} />
              </div>
              <div className="text-center max-w-sm">
                <h2 className="text-2xl font-bold mb-3" style={{ color: '#1b2e1b' }}>
                  Ready to plan your <span className="gradient-text">meals?</span>
                </h2>
                <p className="text-sm leading-relaxed" style={{ color: '#6b8f6b' }}>
                  Configure your settings on the left.{' '}
                  <span className="font-semibold" style={{ color: '#2d6a4f' }}>Generate Meal Plan</span>{' '}
                  will first show you a shopping basket that fits your budget — then plan meals from exactly what you'll buy.
                </p>
              </div>
              <div className="grid grid-cols-3 gap-3 w-full max-w-sm">
                {[
                  { icon: '🛒', label: 'Build basket',    sub: 'stays under budget',    color:'rgba(45,106,79,0.1)',   border:'rgba(45,106,79,0.25)'  },
                  { icon: '✓',  label: 'You confirm',     sub: 'what you\'ll buy',      color:'rgba(64,145,108,0.1)', border:'rgba(64,145,108,0.25)' },
                  { icon: '🤖', label: 'AI plans meals',  sub: 'from your basket only', color:'rgba(116,198,157,0.1)',border:'rgba(116,198,157,0.3)' },
                ].map(f => (
                  <div key={f.label} className="rounded-2xl p-4 flex flex-col items-center gap-1.5 text-center"
                       style={{ background: f.color, border: `1px solid ${f.border}` }}>
                    <span className="text-2xl">{f.icon}</span>
                    <p className="text-xs font-semibold" style={{ color: '#1b2e1b' }}>{f.label}</p>
                    <p className="text-[10px] font-mono" style={{ color: '#6b8f6b' }}>{f.sub}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* BASKET LOADING */}
          {status === 'basket_loading' && (
            <div className="flex-1 flex flex-col items-center justify-center gap-6 py-20">
              <div className="w-16 h-16 border-4 rounded-full animate-spin"
                   style={{ borderColor: 'rgba(45,106,79,0.15)', borderTopColor: '#2d6a4f' }} />
              <div className="text-center">
                <h3 className="text-lg font-bold" style={{ color: '#1b2e1b' }}>Building your shopping basket…</h3>
                <p className="text-sm font-mono mt-1" style={{ color: '#6b8f6b' }}>
                  Selecting the best products within €{config?.budget?.toFixed(2)} budget
                </p>
              </div>
            </div>
          )}

          {/* BASKET REVIEW */}
          {status === 'basket_review' && basket && (
            <BasketReview
              basket={basket}
              onConfirm={handleConfirmBasket}
              onBack={() => setStatus('idle')}
            />
          )}

          {/* LOADING */}
          {status === 'loading' && <LoadingState stage={loadingStage} />}

          {/* ERROR */}
          {status === 'error' && (
            <div className="flex-1 flex flex-col items-center justify-center gap-4 py-20">
              <div className="glass rounded-2xl p-8 max-w-lg w-full text-center"
                   style={{ borderColor: 'rgba(220,38,38,0.25)' }}>
                <span className="text-5xl">⚠️</span>
                <h3 className="text-xl font-semibold mt-4 mb-2" style={{ color: '#dc2626' }}>Something went wrong</h3>
                <p className="text-sm font-mono break-all" style={{ color: '#6b8f6b' }}>{errorMsg}</p>
                <button onClick={() => setStatus('idle')}
                  className="mt-6 px-6 py-2.5 rounded-xl text-sm font-mono transition-all cursor-pointer"
                  style={{ border: '1px solid rgba(220,38,38,0.3)', color: '#dc2626' }}>
                  ← Try Again
                </button>
              </div>
            </div>
          )}

          {/* DONE */}
          {status === 'done' && plan && (
            <div className="flex flex-col gap-6">

              {/* Restored session banner */}
              {restored && (
                <div className="flex items-center justify-between gap-3 px-4 py-3 rounded-2xl text-sm font-mono"
                     style={{ background: 'rgba(45,106,79,0.08)', border: '1px solid rgba(45,106,79,0.25)', color: '#2d6a4f' }}>
                  <span>🔄 Plan restored · saved {typeof restored === 'string' ? restored : 'earlier'}</span>
                  <button onClick={() => setRestored(false)}
                    className="text-xs opacity-60 hover:opacity-100 cursor-pointer">✕</button>
                </div>
              )}

              <Dashboard
                budget={config?.budget ?? 0}
                verifiedTotal={plan.verified_total}
                mealCount={mealCount}
                violations={plan.violations}
                plan={plan}
                userMetrics={plan.user_metrics}
                basket={basket}
              />

              {plan.meal_plan.map(dayObj => (
                <section key={dayObj.day}>
                  <div className="flex items-center gap-3 mb-3">
                    <div className="h-px flex-1"
                         style={{ background: 'linear-gradient(to right, rgba(45,106,79,0.35), transparent)' }} />
                    <span className="text-xs font-mono tracking-widest uppercase px-3 py-1 rounded-full"
                          style={{ color: '#2d6a4f', border: '1px solid rgba(45,106,79,0.3)',
                                   background: 'rgba(45,106,79,0.08)' }}>
                      Day {dayObj.day}
                    </span>
                    <span className="text-xs font-mono" style={{ color: '#a8c5a8' }}>
                      €{dayObj.day_total_eur?.toFixed(2)}
                    </span>
                    <div className="h-px flex-1"
                         style={{ background: 'linear-gradient(to left, rgba(64,145,108,0.25), transparent)' }} />
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3">
                    {dayObj.meals.map((meal, i) => (
                      <MealCard key={`d${dayObj.day}-m${i}`} meal={meal} onClick={() => setSelectedMeal(meal)} />
                    ))}
                  </div>
                </section>
              ))}

              <div className="flex justify-center pt-2 pb-4">
                <button onClick={() => { clearSession(); setStatus('idle'); setRestored(false) }}
                  className="px-6 py-2.5 rounded-xl text-sm font-mono transition-all cursor-pointer"
                  style={{ border: '1px solid rgba(45,106,79,0.3)', color: '#40916c' }}>
                  ↻ Plan New Week
                </button>
              </div>
            </div>
          )}
        </main>
      </div>

      {selectedMeal && (
        <MealModal meal={selectedMeal} onClose={() => setSelectedMeal(null)} />
      )}
    </div>
  )
}
