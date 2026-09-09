import { useState, useRef, useEffect } from 'react'

const ALL_CUISINES = [
  { name: 'Italian',        flag: '🇮🇹', region: 'Europe' },
  { name: 'French',         flag: '🇫🇷', region: 'Europe' },
  { name: 'Spanish',        flag: '🇪🇸', region: 'Europe' },
  { name: 'German',         flag: '🇩🇪', region: 'Europe' },
  { name: 'Greek',          flag: '🇬🇷', region: 'Europe' },
  { name: 'British',        flag: '🇬🇧', region: 'Europe' },
  { name: 'Portuguese',     flag: '🇵🇹', region: 'Europe' },
  { name: 'Polish',         flag: '🇵🇱', region: 'Europe' },
  { name: 'Scandinavian',   flag: '🇸🇪', region: 'Europe' },
  { name: 'Russian',        flag: '🇷🇺', region: 'Europe' },
  { name: 'Hungarian',      flag: '🇭🇺', region: 'Europe' },
  { name: 'Austrian',       flag: '🇦🇹', region: 'Europe' },
  { name: 'Turkish',        flag: '🇹🇷', region: 'Middle East' },
  { name: 'Lebanese',       flag: '🇱🇧', region: 'Middle East' },
  { name: 'Persian',        flag: '🇮🇷', region: 'Middle East' },
  { name: 'Moroccan',       flag: '🇲🇦', region: 'Middle East' },
  { name: 'Egyptian',       flag: '🇪🇬', region: 'Middle East' },
  { name: 'Israeli',        flag: '🇮🇱', region: 'Middle East' },
  { name: 'Ethiopian',      flag: '🇪🇹', region: 'Africa' },
  { name: 'West African',   flag: '🌍',  region: 'Africa' },
  { name: 'Japanese',       flag: '🇯🇵', region: 'Asia' },
  { name: 'Chinese',        flag: '🇨🇳', region: 'Asia' },
  { name: 'Korean',         flag: '🇰🇷', region: 'Asia' },
  { name: 'Thai',           flag: '🇹🇭', region: 'Asia' },
  { name: 'Vietnamese',     flag: '🇻🇳', region: 'Asia' },
  { name: 'Indian',         flag: '🇮🇳', region: 'Asia' },
  { name: 'Pakistani',      flag: '🇵🇰', region: 'Asia' },
  { name: 'Sri Lankan',     flag: '🇱🇰', region: 'Asia' },
  { name: 'Indonesian',     flag: '🇮🇩', region: 'Asia' },
  { name: 'Filipino',       flag: '🇵🇭', region: 'Asia' },
  { name: 'Malaysian',      flag: '🇲🇾', region: 'Asia' },
  { name: 'Taiwanese',      flag: '🇹🇼', region: 'Asia' },
  { name: 'Bangladeshi',    flag: '🇧🇩', region: 'Asia' },
  { name: 'Nepali',         flag: '🇳🇵', region: 'Asia' },
  { name: 'Mexican',        flag: '🇲🇽', region: 'Americas' },
  { name: 'Brazilian',      flag: '🇧🇷', region: 'Americas' },
  { name: 'Peruvian',       flag: '🇵🇪', region: 'Americas' },
  { name: 'Argentinian',    flag: '🇦🇷', region: 'Americas' },
  { name: 'Colombian',      flag: '🇨🇴', region: 'Americas' },
  { name: 'American',       flag: '🇺🇸', region: 'Americas' },
  { name: 'Caribbean',      flag: '🌴',  region: 'Americas' },
  { name: 'Mediterranean',  flag: '🌊',  region: 'Fusion' },
  { name: 'Middle Eastern', flag: '🌙',  region: 'Fusion' },
  { name: 'Pan-Asian',      flag: '🥢',  region: 'Fusion' },
  { name: 'Fusion',         flag: '✨',  region: 'Fusion' },
]

const REGIONS = ['Europe', 'Asia', 'Americas', 'Middle East', 'Africa', 'Fusion']

// Green palette tokens
const G = {
  primary:     '#2d6a4f',
  mid:         '#40916c',
  light:       '#74c69d',
  pale:        '#95d5b2',
  text:        '#1b2e1b',
  textMid:     '#3a5c3a',
  textMuted:   '#6b8f6b',
  border:      'rgba(45,106,79,0.25)',
  borderFocus: 'rgba(45,106,79,0.6)',
  bgInput:     'rgba(255,255,255,0.65)',
  bgSelected:  'rgba(45,106,79,0.12)',
  bgHover:     'rgba(45,106,79,0.06)',
}

const DIET_OPTIONS = [
  { value: 'omnivore',   label: 'Non-Veg',    icon: '🍖', color: 'rgba(180,120,40,0.12)',  border: '#b87828', text: '#7a4f10' },
  { value: 'vegetarian', label: 'Vegetarian', icon: '🥗', color: 'rgba(45,106,79,0.12)',   border: '#2d6a4f', text: '#1b4332' },
  { value: 'vegan',      label: 'Vegan',      icon: '🌱', color: 'rgba(64,145,108,0.12)',  border: '#40916c', text: '#1b4332' },
]

function CuisinePicker({ selected, onChange }) {
  const [open,   setOpen]   = useState(false)
  const [search, setSearch] = useState('')
  const [region, setRegion] = useState('All')
  const dropRef = useRef(null)

  useEffect(() => {
    function handle(e) {
      if (dropRef.current && !dropRef.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', handle)
    return () => document.removeEventListener('mousedown', handle)
  }, [])

  const filtered = ALL_CUISINES.filter(c =>
    (region === 'All' || c.region === region) &&
    c.name.toLowerCase().includes(search.toLowerCase())
  )

  function toggle(name) {
    onChange(selected.includes(name) ? selected.filter(s => s !== name) : [...selected, name])
  }

  return (
    <div className="flex flex-col gap-2" ref={dropRef}>
      <div className="flex items-center justify-between">
        <label className="text-xs font-mono tracking-wider uppercase" style={{ color: G.primary }}>
          Cuisine Style
        </label>
        {selected.length > 0 && (
          <button type="button" onClick={() => onChange([])}
            className="text-[10px] font-mono cursor-pointer" style={{ color: G.textMuted }}>
            Clear all
          </button>
        )}
      </div>

      <button type="button" onClick={() => setOpen(o => !o)}
        className="w-full rounded-xl px-3 py-2.5 text-left text-sm font-mono flex items-center justify-between gap-2 transition-all cursor-pointer"
        style={{ background: G.bgInput, border: `1px solid ${open ? G.borderFocus : G.border}` }}>
        <span className="truncate" style={{ color: selected.length ? G.text : G.textMuted }}>
          {selected.length === 0 ? 'Any cuisine (optional)' :
           selected.length === 1 ? selected[0] : `${selected.length} cuisines selected`}
        </span>
        <span style={{ color: G.primary, transform: open ? 'rotate(180deg)' : '', transition: 'transform 0.2s' }}>▾</span>
      </button>

      {selected.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {selected.map(name => {
            const cuisine = ALL_CUISINES.find(c => c.name === name)
            return (
              <span key={name}
                className="flex items-center gap-1 text-[11px] font-mono px-2 py-0.5 rounded-full cursor-pointer"
                style={{ background: G.bgSelected, border: `1px solid ${G.border}`, color: G.primary }}
                onClick={() => toggle(name)}>
                {cuisine?.flag} {name} ×
              </span>
            )
          })}
        </div>
      )}

      {open && (
        <div className="rounded-2xl overflow-hidden flex flex-col"
             style={{ background: 'rgba(255,255,255,0.97)', border: `1px solid ${G.border}`,
                      boxShadow: '0 12px 32px rgba(45,106,79,0.15)', maxHeight: '320px' }}>
          <div className="px-3 pt-3 pb-2">
            <input type="text" placeholder="Search cuisines…" value={search}
              onChange={e => setSearch(e.target.value)}
              className="w-full rounded-lg px-3 py-2 text-sm font-mono focus:outline-none"
              style={{ background: 'rgba(45,106,79,0.06)', border: `1px solid ${G.border}`,
                       color: G.text }}
            />
          </div>
          <div className="flex gap-1 px-3 pb-2 overflow-x-auto" style={{ scrollbarWidth: 'none' }}>
            {['All', ...REGIONS].map(r => (
              <button key={r} type="button" onClick={() => setRegion(r)}
                className="shrink-0 text-[10px] font-mono px-2 py-1 rounded-full transition-all cursor-pointer"
                style={region === r
                  ? { background: G.bgSelected, border: `1px solid ${G.border}`, color: G.primary }
                  : { background: 'transparent', border: '1px solid rgba(45,106,79,0.12)', color: G.textMuted }}>
                {r}
              </button>
            ))}
          </div>
          <div className="overflow-y-auto px-3 pb-3 flex flex-col gap-1">
            {filtered.length === 0 && (
              <p className="text-[10px] font-mono text-center py-4" style={{ color: G.textMuted }}>No cuisines found</p>
            )}
            {filtered.map(c => {
              const isSel = selected.includes(c.name)
              return (
                <button key={c.name} type="button" onClick={() => toggle(c.name)}
                  className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-sm transition-all duration-150 cursor-pointer text-left"
                  style={isSel
                    ? { background: G.bgSelected, border: `1px solid ${G.border}`, color: G.text }
                    : { background: 'transparent', border: '1px solid transparent', color: G.textMid }}>
                  <span className="text-base w-6 text-center">{c.flag}</span>
                  <span className="flex-1 font-medium">{c.name}</span>
                  {isSel && <span style={{ color: G.primary }}>✓</span>}
                </button>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}

export default function ConfigPanel({ onGenerate, loading }) {
  const [budget,      setBudget]      = useState(60)
  const [diet,        setDiet]        = useState('omnivore')
  const [days,        setDays]        = useState(3)
  const [mealsPerDay, setMealsPerDay] = useState(3)
  const [servings,    setServings]    = useState(2)
  const [cuisines,    setCuisines]    = useState([])
  const [weight,      setWeight]      = useState(70)
  const [height,      setHeight]      = useState(175)
  const [age,         setAge]         = useState(25)
  const [gender,      setGender]      = useState('male')
  const [activity,    setActivity]    = useState('moderate')

  function handleSubmit(e) {
    e.preventDefault()
    onGenerate({ budget, diet, days, meals_per_day: mealsPerDay, servings, cuisines,
                 weight_kg: weight, height_cm: height, age, gender, activity_level: activity })
  }

  const ACTIVITY_OPTS = [
    { value: 'sedentary',   label: 'Sedentary',   sub: 'desk job, no exercise' },
    { value: 'light',       label: 'Light',        sub: '1-3 days/week' },
    { value: 'moderate',    label: 'Moderate',     sub: '3-5 days/week' },
    { value: 'active',      label: 'Active',       sub: '6-7 days/week' },
    { value: 'very_active', label: 'Very Active',  sub: 'athlete / physical job' },
  ]

  const labelStyle   = { color: G.primary }
  const inputStyle   = { background: G.bgInput, border: `1px solid ${G.border}`, color: G.text }
  const inactiveBtn  = { background: 'rgba(255,255,255,0.4)', border: `1px solid rgba(45,106,79,0.15)`, color: G.textMuted }
  const activeGreen  = { background: G.bgSelected, border: `1px solid ${G.primary}`, color: G.primary }
  const activeMid    = { background: 'rgba(64,145,108,0.12)', border: '1px solid #40916c', color: '#1b4332' }

  return (
    <aside className="glass rounded-2xl p-6 flex flex-col gap-5 w-full lg:w-80 shrink-0 overflow-y-auto"
           style={{ maxHeight: 'calc(100vh - 120px)' }}>

      <div>
        <p className="text-xs font-mono tracking-widest uppercase mb-1" style={labelStyle}>Configuration</p>
        <h2 className="text-xl font-bold" style={{ color: G.text }}>Meal Plan Settings</h2>
      </div>

      <form onSubmit={handleSubmit} className="flex flex-col gap-5">

        {/* Budget */}
        <div className="flex flex-col gap-2">
          <label className="text-xs font-mono tracking-wider uppercase" style={labelStyle}>Weekly Budget</label>
          <div className="relative">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 font-mono font-bold" style={{ color: G.primary }}>€</span>
            <input type="number" min={5} max={500} step={1} value={budget}
              onChange={e => setBudget(Number(e.target.value))}
              className="w-full rounded-xl pl-8 pr-4 py-2.5 font-mono text-lg focus:outline-none"
              style={inputStyle} />
          </div>
        </div>

        {/* Diet */}
        <div className="flex flex-col gap-2">
          <label className="text-xs font-mono tracking-wider uppercase" style={labelStyle}>Dietary Preference</label>
          <div className="grid grid-cols-3 gap-2">
            {DIET_OPTIONS.map(opt => (
              <button key={opt.value} type="button" onClick={() => setDiet(opt.value)}
                className="flex flex-col items-center gap-1 py-3 px-1 rounded-xl text-xs font-semibold transition-all duration-200 cursor-pointer"
                style={diet === opt.value
                  ? { background: opt.color, border: `1px solid ${opt.border}`, color: opt.text }
                  : inactiveBtn}>
                <span className="text-xl">{opt.icon}</span>{opt.label}
              </button>
            ))}
          </div>
        </div>

        {/* Cuisine */}
        <CuisinePicker selected={cuisines} onChange={setCuisines} />

        {/* Body Metrics */}
        <div className="flex flex-col gap-3 pt-1">
          <div className="flex items-center gap-2">
            <div className="h-px flex-1" style={{ background: 'rgba(45,106,79,0.2)' }} />
            <p className="text-xs font-mono tracking-widest uppercase" style={{ color: G.mid }}>Body Metrics</p>
            <div className="h-px flex-1" style={{ background: 'rgba(45,106,79,0.2)' }} />
          </div>
          <p className="text-[10px] font-mono text-center -mt-1" style={{ color: G.textMuted }}>
            Used to calculate daily calorie &amp; protein targets
          </p>

          <div className="grid grid-cols-2 gap-2">
            <div className="flex flex-col gap-1.5">
              <label className="text-[10px] font-mono uppercase tracking-wider" style={{ color: G.textMuted }}>Weight</label>
              <div className="relative">
                <input type="number" min={30} max={250} step={0.5} value={weight}
                  onChange={e => setWeight(Number(e.target.value))}
                  className="w-full rounded-xl pl-3 pr-8 py-2 font-mono text-sm focus:outline-none"
                  style={inputStyle} />
                <span className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[10px] font-mono" style={{ color: G.textMuted }}>kg</span>
              </div>
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-[10px] font-mono uppercase tracking-wider" style={{ color: G.textMuted }}>Height</label>
              <div className="relative">
                <input type="number" min={100} max={250} step={1} value={height}
                  onChange={e => setHeight(Number(e.target.value))}
                  className="w-full rounded-xl pl-3 pr-8 py-2 font-mono text-sm focus:outline-none"
                  style={inputStyle} />
                <span className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[10px] font-mono" style={{ color: G.textMuted }}>cm</span>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div className="flex flex-col gap-1.5">
              <label className="text-[10px] font-mono uppercase tracking-wider" style={{ color: G.textMuted }}>Age</label>
              <input type="number" min={10} max={100} step={1} value={age}
                onChange={e => setAge(Number(e.target.value))}
                className="w-full rounded-xl px-3 py-2 font-mono text-sm focus:outline-none"
                style={inputStyle} />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-[10px] font-mono uppercase tracking-wider" style={{ color: G.textMuted }}>Gender</label>
              <div className="grid grid-cols-2 gap-1">
                {[{ v:'male', l:'♂ Male' }, { v:'female', l:'♀ Female' }].map(g => (
                  <button key={g.v} type="button" onClick={() => setGender(g.v)}
                    className="py-2 rounded-lg text-xs font-mono font-semibold transition-all cursor-pointer"
                    style={gender === g.v ? activeMid : inactiveBtn}>
                    {g.l}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-[10px] font-mono uppercase tracking-wider" style={{ color: G.textMuted }}>Activity Level</label>
            <div className="flex flex-col gap-1">
              {ACTIVITY_OPTS.map(opt => (
                <button key={opt.value} type="button" onClick={() => setActivity(opt.value)}
                  className="flex items-center justify-between px-3 py-2 rounded-xl text-xs transition-all duration-150 cursor-pointer text-left"
                  style={activity === opt.value
                    ? { background: 'rgba(116,198,157,0.15)', border: '1px solid rgba(116,198,157,0.5)', color: G.text }
                    : inactiveBtn}>
                  <span className="font-semibold">{opt.label}</span>
                  <span className="text-[10px] opacity-60">{opt.sub}</span>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Days */}
        <div className="flex flex-col gap-2">
          <label className="text-xs font-mono tracking-wider uppercase" style={labelStyle}>Days to Plan</label>
          <div className="grid grid-cols-7 gap-1">
            {[1,2,3,4,5,6,7].map(d => (
              <button key={d} type="button" onClick={() => setDays(d)}
                className="py-2 rounded-lg text-sm font-mono font-bold transition-all cursor-pointer"
                style={days === d ? activeGreen : inactiveBtn}>
                {d}
              </button>
            ))}
          </div>
        </div>

        {/* Meals per day */}
        <div className="flex flex-col gap-2">
          <label className="text-xs font-mono tracking-wider uppercase" style={labelStyle}>Meals per Day</label>
          <div className="flex gap-2">
            {[1,2,3,4,5].map(m => (
              <button key={m} type="button" onClick={() => setMealsPerDay(m)}
                className="flex-1 py-2 rounded-lg text-sm font-mono font-bold transition-all cursor-pointer"
                style={mealsPerDay === m ? activeMid : inactiveBtn}>
                {m}
              </button>
            ))}
          </div>
        </div>

        {/* Servings */}
        <div className="flex flex-col gap-2">
          <label className="text-xs font-mono tracking-wider uppercase" style={labelStyle}>Servings per Meal</label>
          <div className="flex items-center gap-3">
            <button type="button" onClick={() => setServings(s => Math.max(1, s - 1))}
              className="w-9 h-9 rounded-xl text-xl font-bold cursor-pointer flex items-center justify-center"
              style={{ border: `1px solid ${G.border}`, color: G.primary, background: G.bgSelected }}>−</button>
            <span className="flex-1 text-center font-mono text-2xl font-bold" style={{ color: G.text }}>{servings}</span>
            <button type="button" onClick={() => setServings(s => Math.min(10, s + 1))}
              className="w-9 h-9 rounded-xl text-xl font-bold cursor-pointer flex items-center justify-center"
              style={{ border: `1px solid ${G.border}`, color: G.primary, background: G.bgSelected }}>+</button>
          </div>
        </div>

        {/* Generate */}
        <button type="submit" disabled={loading}
          className="mt-1 w-full py-4 rounded-xl font-bold text-sm tracking-widest uppercase transition-all duration-300 cursor-pointer"
          style={loading
            ? { background: 'rgba(45,106,79,0.06)', border: `1px solid rgba(45,106,79,0.15)`, color: 'rgba(45,106,79,0.35)', cursor: 'not-allowed' }
            : { background: 'linear-gradient(135deg, #2d6a4f, #40916c)',
                border: '1px solid rgba(45,106,79,0.4)', color: '#ffffff',
                boxShadow: '0 4px 20px rgba(45,106,79,0.3)' }}>
          {loading ? (
            <span className="flex items-center justify-center gap-2">
              <span className="inline-block w-4 h-4 border-2 rounded-full animate-spin"
                    style={{ borderColor: 'rgba(45,106,79,0.3)', borderTopColor: '#2d6a4f' }} />
              Generating…
            </span>
          ) : '⚡ Generate Meal Plan'}
        </button>
      </form>

      <p className="text-xs text-center font-mono mt-auto" style={{ color: G.textMuted }}>
        Gemini AI · Aldi Süd catalogue
      </p>
    </aside>
  )
}
