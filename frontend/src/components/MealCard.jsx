const MEAL_STYLES = {
  breakfast: {
    gradient: 'linear-gradient(135deg, rgba(180,120,40,0.08), rgba(180,120,40,0.02))',
    border:   'rgba(180,120,40,0.22)',
    badge:    { bg: 'rgba(180,120,40,0.1)', border: 'rgba(180,120,40,0.3)', color: '#7a4f10' },
    icon:     '🌅',
    cost:     '#a16207',
  },
  lunch: {
    gradient: 'linear-gradient(135deg, rgba(45,106,79,0.1), rgba(45,106,79,0.03))',
    border:   'rgba(45,106,79,0.22)',
    badge:    { bg: 'rgba(45,106,79,0.1)', border: 'rgba(45,106,79,0.3)', color: '#1b4332' },
    icon:     '☀️',
    cost:     '#2d6a4f',
  },
  dinner: {
    gradient: 'linear-gradient(135deg, rgba(64,145,108,0.1), rgba(116,198,157,0.04))',
    border:   'rgba(64,145,108,0.22)',
    badge:    { bg: 'rgba(64,145,108,0.1)', border: 'rgba(64,145,108,0.3)', color: '#1b4332' },
    icon:     '🌙',
    cost:     '#40916c',
  },
  snack: {
    gradient: 'linear-gradient(135deg, rgba(116,198,157,0.1), rgba(116,198,157,0.03))',
    border:   'rgba(116,198,157,0.25)',
    badge:    { bg: 'rgba(116,198,157,0.12)', border: 'rgba(116,198,157,0.35)', color: '#1b4332' },
    icon:     '🍎',
    cost:     '#74c69d',
  },
}

// Nutrition chip colors (forest-green spectrum)
const CHIP_COLORS = [
  { color: '#2d6a4f', bg: 'rgba(45,106,79,0.1)',   border: 'rgba(45,106,79,0.25)'   }, // calories
  { color: '#40916c', bg: 'rgba(64,145,108,0.1)',  border: 'rgba(64,145,108,0.25)'  }, // protein
  { color: '#74c69d', bg: 'rgba(116,198,157,0.1)', border: 'rgba(116,198,157,0.28)' }, // carbs
  { color: '#a16207', bg: 'rgba(161,98,7,0.08)',   border: 'rgba(161,98,7,0.22)'    }, // fat
]

export default function MealCard({ meal, onClick }) {
  const type     = meal.meal_type || 'dinner'
  const styles   = MEAL_STYLES[type] || MEAL_STYLES.dinner
  const ingCount  = meal.ingredients?.length || 0
  const stepCount = meal.instructions?.length || 0

  return (
    <button
      onClick={onClick}
      className="w-full text-left rounded-2xl p-5 transition-all duration-250 cursor-pointer focus:outline-none"
      style={{ background: styles.gradient, border: `1px solid ${styles.border}`,
               backdropFilter: 'blur(12px)' }}
      onMouseEnter={e => { e.currentTarget.style.transform = 'translateY(-3px)'; e.currentTarget.style.boxShadow = `0 8px 28px ${styles.border}` }}
      onMouseLeave={e => { e.currentTarget.style.transform = ''; e.currentTarget.style.boxShadow = '' }}
    >
      {/* Top row */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-2">
          <span className="text-2xl leading-none">{styles.icon}</span>
          <span className="text-[10px] font-mono font-bold uppercase tracking-widest px-2 py-0.5 rounded-full"
                style={{ background: styles.badge.bg, border: `1px solid ${styles.badge.border}`, color: styles.badge.color }}>
            {type}
          </span>
        </div>
        <span className="text-lg font-bold font-mono shrink-0" style={{ color: styles.cost }}>
          €{meal.meal_cost_eur?.toFixed(2)}
        </span>
      </div>

      {/* Title */}
      <h3 className="font-semibold text-base leading-snug mb-4 line-clamp-2" style={{ color: '#1b2e1b' }}>
        {meal.name}
      </h3>

      {/* Stats */}
      <div className="flex items-center gap-3 text-xs font-mono" style={{ color: '#6b8f6b' }}>
        <span>🛒 {ingCount} ingredient{ingCount!==1?'s':''}</span>
        <span style={{ color: '#a8c5a8' }}>·</span>
        <span>📋 {stepCount} step{stepCount!==1?'s':''}</span>
        <span style={{ color: '#a8c5a8' }}>·</span>
        <span>👥 {meal.servings}</span>
      </div>

      {/* Nutrition chips */}
      {meal.nutrition_per_serving && (
        <div className="flex flex-wrap gap-1.5 mt-2">
          {[
            `${Math.round(meal.nutrition_per_serving.calories_kcal)} kcal`,
            `${meal.nutrition_per_serving.protein_g?.toFixed(1)}g protein`,
            `${meal.nutrition_per_serving.carbs_g?.toFixed(1)}g carbs`,
            `${meal.nutrition_per_serving.fat_g?.toFixed(1)}g fat`,
          ].map((label, i) => (
            <span key={label} className="text-[10px] font-mono px-1.5 py-0.5 rounded-md"
                  style={{ color: CHIP_COLORS[i].color, background: CHIP_COLORS[i].bg,
                           border: `1px solid ${CHIP_COLORS[i].border}` }}>
              {label}
            </span>
          ))}
          <span className="text-[10px] font-mono self-center" style={{ color: '#a8c5a8' }}>per serving</span>
        </div>
      )}

      <p className="mt-3 text-[10px] font-mono text-right" style={{ color: '#a8c5a8' }}>
        Tap to expand →
      </p>
    </button>
  )
}
