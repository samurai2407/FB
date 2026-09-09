const G = {
  primary: '#2d6a4f', mid: '#40916c', light: '#74c69d',
  text: '#1b2e1b', textMuted: '#6b8f6b',
}

const STAGES = [
  { id: 1, label: 'Filtering Aldi catalog',  detail: 'Applying diet preferences & budget constraints' },
  { id: 2, label: 'Building AI prompt',       detail: 'Structuring ingredient list & meal requirements' },
  { id: 3, label: 'Calling Gemini',           detail: 'Waiting for AI-generated meal plan response' },
  { id: 4, label: 'Verifying budget math',    detail: 'Cross-checking all costs against your budget' },
]

export default function LoadingState({ stage = 0 }) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center gap-10 py-16 px-4">

      {/* Animated orb */}
      <div className="relative flex items-center justify-center w-40 h-40">
        <div className="absolute inset-0 rounded-full animate-ping-slow"
             style={{ border: '1px solid rgba(45,106,79,0.18)' }} />
        <div className="absolute inset-3 rounded-full animate-ping-slow"
             style={{ border: '1px solid rgba(64,145,108,0.22)', animationDelay: '0.35s' }} />
        <div className="absolute inset-6 rounded-full animate-ping-slow"
             style={{ border: '1px solid rgba(116,198,157,0.18)', animationDelay: '0.7s' }} />
        {/* Core */}
        <div className="absolute inset-8 rounded-full"
             style={{ background: 'linear-gradient(135deg,rgba(45,106,79,0.2),rgba(64,145,108,0.12))',
                      border: '1px solid rgba(45,106,79,0.4)',
                      boxShadow: '0 0 24px rgba(45,106,79,0.25)' }} />
        {/* Scan */}
        <div className="absolute inset-8 rounded-full overflow-hidden">
          <div className="w-full h-1/2 animate-scan"
               style={{ background: 'linear-gradient(to bottom, rgba(45,106,79,0.3), transparent)' }} />
        </div>
        <span className="relative text-4xl">🤖</span>
      </div>

      {/* Title */}
      <div className="text-center">
        <h2 className="text-2xl font-bold mb-2" style={{ color: G.text }}>
          AI is crafting your <span className="gradient-text">meal plan</span>
        </h2>
        <p className="text-sm font-mono" style={{ color: G.textMuted }}>This usually takes 10–25 seconds</p>
      </div>

      {/* Stage cards */}
      <div className="w-full max-w-md flex flex-col gap-3">
        {STAGES.map(s => {
          const isDone   = stage > s.id
          const isActive = stage === s.id

          return (
            <div key={s.id}
              className="glass rounded-xl px-4 py-3 flex items-center gap-4 transition-all duration-500"
              style={isActive  ? { borderColor: 'rgba(45,106,79,0.45)', boxShadow: '0 0 14px rgba(45,106,79,0.15)' }
                   : !isDone   ? { opacity: 0.35 } : {}}>

              <div className="w-7 h-7 rounded-full flex items-center justify-center shrink-0 text-sm font-bold font-mono"
                   style={isDone
                     ? { background: 'rgba(45,106,79,0.12)', border: '1px solid rgba(45,106,79,0.45)', color: G.primary }
                     : isActive
                     ? { background: 'rgba(64,145,108,0.12)', border: '1px solid rgba(64,145,108,0.5)', color: G.mid }
                     : { background: 'rgba(255,255,255,0.3)', border: '1px solid rgba(45,106,79,0.15)', color: G.textMuted }}>
                {isDone ? '✓' : s.id}
              </div>

              <div className="flex flex-col min-w-0">
                <span className="text-sm font-semibold truncate"
                      style={{ color: isDone ? G.primary : isActive ? G.text : G.textMuted }}>
                  {s.label}
                </span>
                {isActive && (
                  <span className="text-xs font-mono truncate" style={{ color: G.textMuted }}>{s.detail}</span>
                )}
              </div>

              {isActive && (
                <div className="ml-auto shrink-0 w-4 h-4 border-2 rounded-full animate-spin"
                     style={{ borderColor: 'rgba(45,106,79,0.2)', borderTopColor: G.primary }} />
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
