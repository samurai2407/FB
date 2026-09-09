import { useState, useEffect } from 'react'

const G = {
  primary: '#2d6a4f', mid: '#40916c', light: '#74c69d',
  text: '#1b2e1b', textMid: '#3a5c3a', textMuted: '#6b8f6b',
  border: 'rgba(45,106,79,0.2)', borderMid: 'rgba(45,106,79,0.15)',
}

export default function MealModal({ meal, onClose }) {
  const [tab, setTab] = useState('ingredients')

  useEffect(() => {
    const onKey = e => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  if (!meal) return null

  const totalCost = meal.ingredients?.reduce((s, i) => s + (i.cost_eur || 0), 0) || 0

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: 'rgba(27,46,27,0.55)', backdropFilter: 'blur(8px)' }}
      onClick={e => { if (e.target === e.currentTarget) onClose() }}
    >
      <div className="rounded-2xl w-full max-w-2xl max-h-[90vh] flex flex-col overflow-hidden"
           style={{ background: 'rgba(248,252,248,0.98)', border: `1px solid ${G.border}`,
                    boxShadow: '0 0 50px rgba(45,106,79,0.2), 0 25px 50px rgba(27,46,27,0.25)' }}>

        {/* Header */}
        <div className="flex items-start justify-between gap-4 px-6 pt-6 pb-4"
             style={{ borderBottom: `1px solid ${G.borderMid}` }}>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-mono tracking-widest uppercase mb-1 capitalize" style={{ color: G.mid }}>
              {meal.meal_type}
            </p>
            <h2 className="text-xl font-bold leading-snug line-clamp-2" style={{ color: G.text }}>{meal.name}</h2>
            <p className="text-sm font-mono mt-1" style={{ color: G.textMuted }}>
              {meal.servings} serving{meal.servings!==1?'s':''} ·{' '}
              <span className="font-bold" style={{ color: G.primary }}>€{meal.meal_cost_eur?.toFixed(2)}</span>
            </p>
          </div>
          <button onClick={onClose}
            className="text-2xl leading-none transition-colors cursor-pointer mt-0.5 shrink-0"
            style={{ color: G.textMuted }}
            onMouseEnter={e => e.currentTarget.style.color = G.primary}
            onMouseLeave={e => e.currentTarget.style.color = G.textMuted}>×</button>
        </div>

        {/* Tabs */}
        <div className="flex px-6" style={{ borderBottom: `1px solid ${G.borderMid}` }}>
          {[
            { id: 'ingredients', label: '🛒 Ingredients' },
            { id: 'procedure',   label: '🍳 Procedure'   },
            { id: 'nutrition',   label: '📊 Nutrition'   },
          ].map(t => (
            <button key={t.id} onClick={() => setTab(t.id)}
              className="py-3 px-4 text-sm font-semibold border-b-2 -mb-px transition-all mr-2 cursor-pointer"
              style={tab===t.id ? { borderColor: G.primary, color: G.primary }
                                : { borderColor: 'transparent', color: G.textMuted }}>
              {t.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="overflow-y-auto flex-1 px-6 py-5">

          {tab === 'ingredients' && (
            <div className="flex flex-col gap-2">
              <div className="grid grid-cols-[1fr_auto_auto] gap-x-4 px-3 mb-1">
                <span className="text-[10px] font-mono uppercase tracking-wider" style={{ color: G.textMuted }}>Product</span>
                <span className="text-[10px] font-mono uppercase tracking-wider text-right" style={{ color: G.textMuted }}>Weight</span>
                <span className="text-[10px] font-mono uppercase tracking-wider text-right" style={{ color: G.textMuted }}>Cost</span>
              </div>
              {meal.ingredients?.map((ing, i) => (
                <div key={i} className="grid grid-cols-[1fr_auto_auto] gap-x-4 items-center rounded-xl px-3 py-3"
                     style={{ background: 'rgba(45,106,79,0.05)', border: `1px solid ${G.borderMid}` }}>
                  <div className="min-w-0">
                    <p className="text-sm truncate" style={{ color: G.text }}>{ing.product_title}</p>
                    <p className="text-xs font-mono mt-0.5" style={{ color: G.textMuted }}>Pack: €{ing.price_eur?.toFixed(2)}</p>
                  </div>
                  <span className="text-sm font-mono text-right whitespace-nowrap" style={{ color: G.textMid }}>
                    {ing.qty_used_kg?.toFixed(3)} kg
                  </span>
                  <span className="text-sm font-bold font-mono text-right whitespace-nowrap" style={{ color: G.primary }}>
                    €{ing.cost_eur?.toFixed(2)}
                  </span>
                </div>
              ))}
              <div className="flex justify-between items-center mt-3 pt-3"
                   style={{ borderTop: `1px solid ${G.borderMid}` }}>
                <span className="text-sm font-mono" style={{ color: G.textMuted }}>Total ingredient cost</span>
                <span className="text-lg font-bold font-mono" style={{ color: G.primary }}>€{totalCost.toFixed(2)}</span>
              </div>
            </div>
          )}

          {tab === 'procedure' && (
            <ol className="flex flex-col gap-4">
              {meal.instructions?.map((step, i) => (
                <li key={i} className="flex gap-4">
                  <span className="shrink-0 w-7 h-7 rounded-full font-mono font-bold text-xs flex items-center justify-center mt-0.5"
                        style={{ background: i%2===0 ? 'rgba(45,106,79,0.12)' : 'rgba(64,145,108,0.1)',
                                 border: `1px solid ${i%2===0 ? 'rgba(45,106,79,0.35)' : 'rgba(64,145,108,0.3)'}`,
                                 color: i%2===0 ? G.primary : G.mid }}>
                    {i+1}
                  </span>
                  <p className="text-sm leading-relaxed" style={{ color: G.textMid }}>{step}</p>
                </li>
              ))}
            </ol>
          )}

          {tab === 'nutrition' && (
            <div className="flex flex-col gap-4">
              {meal.nutrition_per_serving ? (
                <>
                  <p className="text-xs font-mono" style={{ color: G.textMuted }}>Per single serving (AI-estimated)</p>
                  <div className="grid grid-cols-2 gap-3">
                    {[
                      { label:'Calories', value:`${Math.round(meal.nutrition_per_serving.calories_kcal)} kcal`, color:G.primary, bg:'rgba(45,106,79,0.08)',  border:'rgba(45,106,79,0.2)'  },
                      { label:'Protein',  value:`${meal.nutrition_per_serving.protein_g?.toFixed(1)} g`,        color:G.mid,     bg:'rgba(64,145,108,0.08)', border:'rgba(64,145,108,0.2)' },
                      { label:'Carbs',    value:`${meal.nutrition_per_serving.carbs_g?.toFixed(1)} g`,          color:'#74c69d', bg:'rgba(116,198,157,0.08)',border:'rgba(116,198,157,0.22)'},
                      { label:'Fat',      value:`${meal.nutrition_per_serving.fat_g?.toFixed(1)} g`,            color:'#a16207', bg:'rgba(161,98,7,0.07)',   border:'rgba(161,98,7,0.2)'   },
                    ].map(item => (
                      <div key={item.label} className="rounded-xl p-4 flex flex-col gap-1"
                           style={{ background: item.bg, border: `1px solid ${item.border}` }}>
                        <p className="text-[10px] font-mono uppercase tracking-wider" style={{ color: G.textMuted }}>{item.label}</p>
                        <p className="text-2xl font-bold font-mono" style={{ color: item.color }}>{item.value}</p>
                      </div>
                    ))}
                  </div>
                  <div className="rounded-xl px-4 py-3"
                       style={{ background: 'rgba(45,106,79,0.04)', border: `1px solid ${G.borderMid}` }}>
                    <p className="text-[10px] font-mono uppercase tracking-wider mb-2" style={{ color: G.textMuted }}>
                      Total for {meal.servings} serving{meal.servings!==1?'s':''}
                    </p>
                    <div className="grid grid-cols-4 gap-2 text-center">
                      {[
                        { label:'kcal',    value: Math.round((meal.nutrition_per_serving.calories_kcal||0)*meal.servings), color:G.primary },
                        { label:'protein', value:`${((meal.nutrition_per_serving.protein_g||0)*meal.servings).toFixed(1)}g`, color:G.mid },
                        { label:'carbs',   value:`${((meal.nutrition_per_serving.carbs_g||0)*meal.servings).toFixed(1)}g`,   color:'#74c69d' },
                        { label:'fat',     value:`${((meal.nutrition_per_serving.fat_g||0)*meal.servings).toFixed(1)}g`,     color:'#a16207' },
                      ].map(t => (
                        <div key={t.label}>
                          <p className="text-base font-bold font-mono" style={{ color: t.color }}>{t.value}</p>
                          <p className="text-[10px] font-mono" style={{ color: G.textMuted }}>{t.label}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                  <p className="text-[10px] font-mono" style={{ color: 'rgba(45,106,79,0.4)' }}>
                    * Estimated by AI. Not a substitute for professional dietary advice.
                  </p>
                </>
              ) : (
                <p className="text-sm font-mono text-center py-8" style={{ color: G.textMuted }}>
                  Nutrition data not available for this meal.
                </p>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 flex justify-end" style={{ borderTop: `1px solid ${G.borderMid}` }}>
          <button onClick={onClose}
            className="px-5 py-2 rounded-xl text-sm font-mono transition-all cursor-pointer"
            style={{ border: `1px solid ${G.border}`, color: G.textMuted }}
            onMouseEnter={e => { e.currentTarget.style.borderColor = G.primary; e.currentTarget.style.color = G.primary }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = G.border;  e.currentTarget.style.color = G.textMuted }}>
            Close
          </button>
        </div>
      </div>
    </div>
  )
}
