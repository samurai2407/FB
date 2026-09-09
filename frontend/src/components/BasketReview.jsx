const G = {
  primary: '#2d6a4f', mid: '#40916c', light: '#74c69d',
  text: '#1b2e1b', textMid: '#3a5c3a', textMuted: '#6b8f6b',
  border: 'rgba(45,106,79,0.2)', bgInput: 'rgba(255,255,255,0.65)',
}

export default function BasketReview({ basket, onConfirm, onBack }) {
  const { basket: items, total, budget, remaining } = basket
  const pct = Math.min(100, (total / budget) * 100)

  return (
    <div className="flex-1 flex flex-col gap-5">

      {/* Header */}
      <div className="glass rounded-2xl px-6 py-5">
        <div className="flex items-start justify-between gap-4 mb-4">
          <div>
            <p className="text-xs font-mono tracking-widest uppercase mb-1" style={{ color: G.mid }}>
              Step 1 of 2 — Your Shopping Basket
            </p>
            <h2 className="text-xl font-bold" style={{ color: G.text }}>
              Here's what you'll buy at Aldi
            </h2>
            <p className="text-sm mt-1" style={{ color: G.textMuted }}>
              These {items.length} products fit your €{budget.toFixed(2)} budget.
              Meals will be planned using only these items.
            </p>
          </div>
          <div className="text-right shrink-0">
            <p className="text-xs font-mono" style={{ color: G.textMuted }}>Total spend</p>
            <p className="text-3xl font-bold font-mono" style={{ color: G.primary }}>€{total.toFixed(2)}</p>
            <p className="text-xs font-mono" style={{ color: G.textMuted }}>€{remaining.toFixed(2)} left over</p>
          </div>
        </div>

        {/* Budget bar */}
        <div className="w-full h-2 rounded-full overflow-hidden mb-1"
             style={{ background: 'rgba(45,106,79,0.1)' }}>
          <div className="h-full rounded-full transition-all duration-700"
               style={{ width: `${pct}%`,
                        background: 'linear-gradient(90deg, #2d6a4f, #40916c)',
                        boxShadow: '0 0 8px rgba(45,106,79,0.3)' }} />
        </div>
        <div className="flex justify-between text-[10px] font-mono" style={{ color: G.textMuted }}>
          <span>€0</span>
          <span style={{ color: G.primary, fontWeight: 600 }}>
            {pct.toFixed(0)}% of €{budget.toFixed(2)} budget used
          </span>
          <span>€{budget.toFixed(2)}</span>
        </div>
      </div>

      {/* Item grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-2 overflow-y-auto"
           style={{ maxHeight: 'calc(100vh - 420px)' }}>
        {items.map((item, i) => (
          <div key={i}
               className="glass rounded-xl px-4 py-3 flex items-center justify-between gap-3">
            <div className="min-w-0">
              <p className="text-sm font-medium truncate" style={{ color: G.text }}>
                {item.brand ? `${item.brand} ` : ''}{item.title}
              </p>
              <p className="text-[10px] font-mono mt-0.5" style={{ color: G.textMuted }}>
                {item.subcategory || item.category} · {item.weight_kg}kg
              </p>
            </div>
            <span className="text-sm font-bold font-mono shrink-0" style={{ color: G.primary }}>
              €{item.price_eur.toFixed(2)}
            </span>
          </div>
        ))}
      </div>

      {/* Actions */}
      <div className="flex gap-3">
        <button onClick={onBack}
          className="px-5 py-3 rounded-xl text-sm font-mono transition-all cursor-pointer"
          style={{ border: `1px solid ${G.border}`, color: G.textMuted }}>
          ← Change Settings
        </button>
        <button onClick={() => onConfirm(items)}
          className="flex-1 py-3 rounded-xl font-bold text-sm tracking-widest uppercase transition-all duration-300 cursor-pointer"
          style={{ background: 'linear-gradient(135deg, #2d6a4f, #40916c)',
                   border: '1px solid rgba(45,106,79,0.4)', color: '#ffffff',
                   boxShadow: '0 4px 20px rgba(45,106,79,0.3)' }}>
          ✓ Looks Good — Generate Meal Plan
        </button>
      </div>
    </div>
  )
}
