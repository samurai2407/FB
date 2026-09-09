const G = {
  primary: '#2d6a4f', mid: '#40916c', light: '#74c69d',
  text: '#1b2e1b', textMid: '#3a5c3a', textMuted: '#6b8f6b',
  border: 'rgba(45,106,79,0.2)', bgCard: 'rgba(255,255,255,0.5)',
}

function MetricCard({ label, value, sub, style }) {
  return (
    <div className="glass rounded-2xl p-5 flex flex-col gap-1 flex-1 min-w-0" style={style}>
      <p className="text-xs font-mono tracking-widest uppercase" style={{ color: G.mid }}>{label}</p>
      <p className="text-3xl font-bold font-mono truncate" style={{ color: G.text }}>{value}</p>
      {sub && <p className="text-xs font-mono" style={{ color: G.textMuted }}>{sub}</p>}
    </div>
  )
}

function NutritionBar({ label, value, target, color, unit = 'g' }) {
  if (!value && value !== 0) return null
  const pct     = target ? Math.min(100, (value / target) * 100) : null
  const display = unit === 'kcal' ? Math.round(value) : value.toFixed(1)
  return (
    <div className="flex flex-col gap-1">
      <div className="flex justify-between text-xs font-mono">
        <span style={{ color }}>{label}</span>
        <span style={{ color: G.textMid }}>
          {display}{unit}
          {target && <span style={{ color: G.textMuted }}> / {target}{unit}</span>}
        </span>
      </div>
      {pct !== null && (
        <div className="w-full h-1.5 rounded-full overflow-hidden"
             style={{ background: 'rgba(45,106,79,0.1)' }}>
          <div className="h-full rounded-full transition-all duration-700"
               style={{ width: `${pct}%`,
                        background: `linear-gradient(90deg, ${color}, ${color}cc)`,
                        boxShadow: `0 0 6px ${color}66` }} />
        </div>
      )}
    </div>
  )
}

export default function Dashboard({ budget, verifiedTotal, mealCount, violations, plan, userMetrics }) {
  const remaining  = budget - verifiedTotal
  const pct        = Math.min(100, (verifiedTotal / budget) * 100)
  const overBudget = verifiedTotal > budget
  const barColor   = overBudget ? '#dc2626' : pct > 85 ? '#ca8a04' : '#2d6a4f'

  const tdee          = userMetrics?.tdee_kcal
  const proteinTarget = userMetrics?.daily_protein_g
  const bmi           = userMetrics?.bmi
  const hasMetrics    = !!(tdee && proteinTarget)

  const dailyNutrition = plan?.meal_plan?.map(day => {
    const n = day.day_nutrition
    if (!n) {
      // Fallback: sum per-serving values across meals (no ×servings — TDEE is per person)
      return (day.meals || []).reduce((acc, meal) => {
        const nut = meal.nutrition_per_serving
        if (!nut) return acc
        return {
          calories: acc.calories + (nut.calories_kcal || 0),
          protein:  acc.protein  + (nut.protein_g     || 0),
          carbs:    acc.carbs    + (nut.carbs_g        || 0),
          fat:      acc.fat      + (nut.fat_g          || 0),
        }
      }, { calories: 0, protein: 0, carbs: 0, fat: 0 })
    }
    return {
      calories: n.total_calories_kcal || 0,
      protein:  n.total_protein_g     || 0,
      carbs:    n.total_carbs_g       || 0,
      fat:      n.total_fat_g         || 0,
    }
  }) ?? []

  const avgNutrition = dailyNutrition.length > 0
    ? dailyNutrition.reduce((acc, d) => ({
        calories: acc.calories + d.calories / dailyNutrition.length,
        protein:  acc.protein  + d.protein  / dailyNutrition.length,
        carbs:    acc.carbs    + d.carbs    / dailyNutrition.length,
        fat:      acc.fat      + d.fat      / dailyNutrition.length,
      }), { calories:0, protein:0, carbs:0, fat:0 })
    : null

  return (
    <div className="flex flex-col gap-4">

      {/* Violations */}
      {violations?.length > 0 && (
        <div className="glass rounded-2xl px-4 py-3 flex items-start gap-3"
             style={{ borderColor: 'rgba(202,138,4,0.35)' }}>
          <span className="text-xl shrink-0">⚠️</span>
          <div>
            <p className="text-sm font-semibold" style={{ color: '#92400e' }}>Budget discrepancies corrected</p>
            <ul className="mt-1 space-y-0.5">
              {violations.map((v, i) => (
                <li key={i} className="text-xs font-mono" style={{ color: '#a16207' }}>{v}</li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {/* Budget metrics */}
      <div className="flex flex-wrap gap-3">
        <MetricCard label="Weekly Budget"  value={`€${budget.toFixed(2)}`}
          sub="your configured limit"
          style={{ borderColor: 'rgba(45,106,79,0.22)' }} />
        <MetricCard label="Estimated Cost" value={`€${verifiedTotal.toFixed(2)}`}
          sub={`${mealCount} meal${mealCount!==1?'s':''} planned`}
          style={{ borderColor: 'rgba(64,145,108,0.4)', boxShadow: '0 0 16px rgba(64,145,108,0.1)',
                   background: 'rgba(64,145,108,0.06)' }} />
        <MetricCard label="Remaining Funds" value={`€${remaining.toFixed(2)}`}
          sub={overBudget ? 'over budget ⚠️' : 'left this week'}
          style={{ borderColor: overBudget ? 'rgba(220,38,38,0.35)' : 'rgba(45,106,79,0.25)' }} />
      </div>

      {/* Budget bar */}
      <div className="glass rounded-2xl px-5 py-4">
        <div className="flex justify-between text-xs font-mono mb-2">
          <span style={{ color: G.textMuted }}>Budget utilisation</span>
          <span style={{ color: barColor }}>{pct.toFixed(1)}%</span>
        </div>
        <div className="w-full h-2.5 rounded-full overflow-hidden"
             style={{ background: 'rgba(45,106,79,0.1)' }}>
          <div className="h-full rounded-full transition-all duration-700"
               style={{ width: `${Math.min(100,pct)}%`,
                        background: `linear-gradient(90deg, ${barColor}, ${barColor}cc)`,
                        boxShadow: `0 0 10px ${barColor}66` }} />
        </div>
      </div>

      {/* Nutrition panel */}
      <div className="glass rounded-2xl px-5 py-5 flex flex-col gap-4"
           style={{ borderColor: 'rgba(45,106,79,0.2)' }}>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs font-mono tracking-widest uppercase" style={{ color: G.mid }}>
              Nutrition Overview
            </p>
            <p className="text-[10px] font-mono mt-0.5" style={{ color: G.textMuted }}>
              {hasMetrics ? 'Targets from Mifflin-St Jeor BMR formula' : 'AI-estimated values per serving'}
            </p>
          </div>
          {bmi && (
            <div className="text-right">
              <p className="text-xs font-mono" style={{ color: G.textMuted }}>BMI</p>
              <p className="text-xl font-bold font-mono"
                 style={{ color: bmi<18.5?'#3b82f6':bmi<25?G.primary:bmi<30?'#ca8a04':'#dc2626' }}>
                {bmi}
              </p>
              <p className="text-[10px] font-mono"
                 style={{ color: bmi<18.5?'#3b82f6':bmi<25?G.primary:bmi<30?'#ca8a04':'#dc2626' }}>
                {bmi<18.5?'Underweight':bmi<25?'Healthy':bmi<30?'Overweight':'Obese'}
              </p>
            </div>
          )}
        </div>

        {hasMetrics && (
          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-xl px-3 py-2.5 flex flex-col gap-0.5"
                 style={{ background: 'rgba(45,106,79,0.08)', border: '1px solid rgba(45,106,79,0.2)' }}>
              <p className="text-[10px] font-mono uppercase tracking-wider" style={{ color: G.textMuted }}>Daily Target</p>
              <p className="text-lg font-bold font-mono" style={{ color: G.primary }}>{tdee} kcal</p>
              <p className="text-[10px] font-mono" style={{ color: G.textMuted }}>TDEE · {userMetrics.activity_level}</p>
            </div>
            <div className="rounded-xl px-3 py-2.5 flex flex-col gap-0.5"
                 style={{ background: 'rgba(64,145,108,0.08)', border: '1px solid rgba(64,145,108,0.2)' }}>
              <p className="text-[10px] font-mono uppercase tracking-wider" style={{ color: G.textMuted }}>Protein Target</p>
              <p className="text-lg font-bold font-mono" style={{ color: G.mid }}>{proteinTarget}g</p>
              <p className="text-[10px] font-mono" style={{ color: G.textMuted }}>1.6g × {userMetrics.weight_kg}kg</p>
            </div>
          </div>
        )}

        {avgNutrition && (
          <div className="flex flex-col gap-2.5">
            <p className="text-[10px] font-mono uppercase tracking-wider" style={{ color: G.textMuted }}>
              Avg daily intake from this plan
            </p>
            <NutritionBar label="Calories" value={avgNutrition.calories} target={tdee}   color={G.primary} unit="kcal" />
            <NutritionBar label="Protein"  value={avgNutrition.protein}  target={proteinTarget} color={G.mid} />
            <NutritionBar label="Carbs"    value={avgNutrition.carbs}    color={G.light} />
            <NutritionBar label="Fat"      value={avgNutrition.fat}      color="#ca8a04" />
          </div>
        )}

        <p className="text-[10px] font-mono" style={{ color: 'rgba(45,106,79,0.35)' }}>
          * Nutrition values are AI-estimated. Consult a dietitian for medical advice.
        </p>
      </div>
    </div>
  )
}
