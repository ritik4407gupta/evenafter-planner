import { useEffect, useState, type FormEvent } from 'react'
import { CheckCircle2, Circle, Download, Gauge, KeyRound, LogOut, Moon, Palette, Shield, ShieldCheck, Sun, Eye, EyeOff, Trash2, ExternalLink, Sparkles, AlertTriangle, LoaderCircle } from 'lucide-react'
import { request, type User, type AIProviderStatus } from '../lib/api'

export type ThemeMode = 'light' | 'dark'
type Props = {
  user: User
  theme: ThemeMode
  onThemeChange: (next: ThemeMode, button: HTMLButtonElement) => void
  reducedMotion: boolean
  setReducedMotion: (value: boolean) => void
  remindersEnabled: boolean
  setRemindersEnabled: (value: boolean) => void
  onExport: () => void
  onLogout: () => void
}
function initials(name: string) { return name.split(/\s+/).slice(0, 2).map(s => s[0]).join('').toUpperCase() }

export default function SettingsPage({ user, theme, onThemeChange, reducedMotion, setReducedMotion, remindersEnabled, setRemindersEnabled, onExport, onLogout }: Props) {
  const [aiStatus, setAIStatus] = useState<AIProviderStatus | null>(null)
  const [geminiKey, setGeminiKey] = useState('')
  const [groqKey, setGroqKey] = useState('')
  const [showGeminiKey, setShowGeminiKey] = useState(false)
  const [showGroqKey, setShowGroqKey] = useState(false)
  const [aiLoading, setAILoading] = useState(true)
  const [aiSaving, setAISaving] = useState(false)
  const [aiError, setAIError] = useState('')
  const [aiSuccess, setAISuccess] = useState('')

  const refreshAIStatus = async () => {
    setAILoading(true)
    try {
      setAIStatus(await request<AIProviderStatus>('/api/ai/settings'))
      setAIError('')
    } catch (error) {
      setAIError(error instanceof Error ? error.message : 'Could not load AI settings.')
    } finally { setAILoading(false) }
  }
  useEffect(() => { void refreshAIStatus() }, [])

  const saveAIKeys = async (event: FormEvent) => {
    event.preventDefault()
    setAIError('')
    setAISuccess('')
    if (!aiStatus?.gemini_configured && !geminiKey.trim()) {
      setAIError('Gemini API key is required to enable AI suggestions.')
      return
    }
    if (geminiKey.trim() && geminiKey.trim().length < 10) {
      setAIError('Please check the Gemini API key and try again.')
      return
    }
    if (groqKey.trim() && groqKey.trim().length < 10) {
      setAIError('Please check the Groq API key and try again.')
      return
    }
    setAISaving(true)
    try {
      const result = await request<AIProviderStatus>('/api/ai/settings', {
        method: 'PUT',
        body: JSON.stringify({ ...(geminiKey.trim() ? { gemini_api_key: geminiKey.trim() } : {}), ...(groqKey.trim() ? { groq_api_key: groqKey.trim() } : {}) }),
      })
      setAIStatus(result)
      setGeminiKey('')
      setGroqKey('')
      setAISuccess(result.ai_enabled ? (result.groq_configured ? 'Gemini is ready. Groq is saved as the automatic fallback.' : 'Gemini is ready. AI-generated suggestions are enabled.') : 'Save a Gemini API key to enable AI suggestions.')
    } catch (error) {
      setAIError(error instanceof Error ? error.message : 'Could not save AI provider settings.')
    } finally { setAISaving(false) }
  }

  const clearKey = async (provider: 'gemini' | 'groq') => {
    const providerName = provider === 'gemini' ? 'Gemini' : 'Groq'
    if (!window.confirm(`Remove the saved ${providerName} API key?`)) return
    setAISaving(true); setAIError(''); setAISuccess('')
    try {
      const result = await request<AIProviderStatus>('/api/ai/settings', { method: 'PUT', body: JSON.stringify(provider === 'gemini' ? { clear_gemini: true } : { clear_groq: true }) })
      setAIStatus(result)
      setAISuccess(provider === 'gemini' ? 'Gemini key removed. AI suggestions are now disabled until a new Gemini key is added.' : 'Groq fallback key removed.')
    } catch (error) {
      setAIError(error instanceof Error ? error.message : `Could not remove ${providerName} key.`)
    } finally { setAISaving(false) }
  }

  const themes = [
    { key: 'light' as const, label: 'Light mode', desc: 'Warm ivory, blush and soft sage', icon: Sun },
    { key: 'dark' as const, label: 'Dark mode', desc: 'Deep plum, dusk and muted rose', icon: Moon },
  ]
  return <div className="standard-page settings-page">
    <div className="page-header"><div><div className="eyebrow">YOUR SPACE, YOUR RULES</div><h1>A little space to make<br/><em>things feel just right.</em></h1><p>Tune the way EverAfter looks and feels. Your theme and preferences stay saved on this device.</p></div></div>
    <div className="settings-layout">
      <section className="panel settings-profile-card">
        <div className="settings-profile-art"><div className="settings-profile-flower">✿</div><div className="settings-avatar">{initials(user.name)}</div></div>
        <div className="settings-profile-copy"><div className="eyebrow">YOUR ACCOUNT</div><h3>{user.name}</h3><p>{user.email}</p><span className="settings-private-pill"><ShieldCheck size={13}/> Private workspace</span></div>
        <div className="settings-account-note"><Shield size={16}/><span>Your events, budgets, tasks, vendors, and guest lists are linked to this account in the database. Sign in with these credentials to pick up where you left off.</span></div>
      </section>
      <section className="panel settings-panel">
        <div className="settings-section-title"><div className="settings-section-icon theme-setting-icon"><Palette size={18}/></div><div><h3>Appearance</h3><p>A soft place to plan, in light or dark.</p></div></div>
        <div className="theme-choice-grid">{themes.map(choice => { const Icon = choice.icon; return <button key={choice.key} className={`theme-choice theme-choice-${choice.key} ${theme === choice.key ? 'selected' : ''}`} onClick={e => onThemeChange(choice.key, e.currentTarget)} aria-pressed={theme === choice.key}><span className="theme-choice-preview"><span/><span/><span/></span><span className="theme-choice-text"><b><Icon size={15}/>{choice.label}</b><small>{choice.desc}</small></span><span className="theme-choice-check">{theme === choice.key ? <CheckCircle2 size={17}/> : <Circle size={17}/>}</span></button> })}</div>
        <p className="settings-muted-note">The theme transition starts from the button you press and spills across the screen. Your choice is remembered on this device.</p>
      </section>

      <section className="panel settings-panel settings-ai-panel">
        <div className="settings-section-title"><div className="settings-section-icon ai-setting-icon"><Sparkles size={18}/></div><div><h3>GenAI provider keys</h3><p>Connect a real language model to generate every suggestion.</p></div><span className={`ai-ready-pill ${aiStatus?.ai_enabled ? 'is-ready' : 'is-locked'}`}>{aiLoading ? <LoaderCircle size={12} className="spin-icon"/> : aiStatus?.ai_enabled ? <CheckCircle2 size={12}/> : <KeyRound size={12}/>} {aiLoading ? 'Checking' : aiStatus?.ai_enabled ? 'AI enabled' : 'Key required'}</span></div>
        <div className="ai-provider-explainer"><ShieldCheck size={16}/><span><b>No canned AI suggestions.</b> EverAfter only displays generated plans after a provider responds and the response passes validation. If no provider can answer, the app shows an error instead of template content.</span></div>
        <form className="ai-key-form" onSubmit={saveAIKeys}>
          <div className="ai-provider-label-row"><label className="field-label" htmlFor="gemini-api-key">Gemini API key <span className="required-chip">Required</span></label>{aiStatus?.gemini_configured && <span className="key-configured"><CheckCircle2 size={12}/> Saved securely · {aiStatus.gemini_masked}</span>}</div>
          <div className="secret-input-wrap"><KeyRound size={15}/><input id="gemini-api-key" type={showGeminiKey ? 'text' : 'password'} autoComplete="new-password" value={geminiKey} onChange={e => setGeminiKey(e.target.value)} placeholder={aiStatus?.gemini_configured ? 'Enter a new key to replace the saved key' : 'Paste your Gemini API key'} required={!aiStatus?.gemini_configured} minLength={10} maxLength={500} spellCheck={false}/><button type="button" className="secret-reveal" onClick={() => setShowGeminiKey(v => !v)} aria-label={showGeminiKey ? 'Hide Gemini API key' : 'Show Gemini API key'}>{showGeminiKey ? <EyeOff size={15}/> : <Eye size={15}/>}</button></div>
          <div className="ai-key-help">Get a key from <a href="https://aistudio.google.com/app/apikey" target="_blank" rel="noreferrer">Google AI Studio <ExternalLink size={11}/></a>. Gemini is the primary provider and must be configured to enable AI.</div>

          <div className="ai-provider-label-row ai-groq-label"><label className="field-label" htmlFor="groq-api-key">Groq API key <span className="optional-chip">Optional fallback</span></label>{aiStatus?.groq_configured && <span className="key-configured"><CheckCircle2 size={12}/> Saved securely · {aiStatus.groq_masked}</span>}</div>
          <div className="secret-input-wrap"><KeyRound size={15}/><input id="groq-api-key" type={showGroqKey ? 'text' : 'password'} autoComplete="new-password" value={groqKey} onChange={e => setGroqKey(e.target.value)} placeholder={aiStatus?.groq_configured ? 'Enter a new key to replace the saved key' : 'Add a Groq key for automatic fallback'} maxLength={500} spellCheck={false}/><button type="button" className="secret-reveal" onClick={() => setShowGroqKey(v => !v)} aria-label={showGroqKey ? 'Hide Groq API key' : 'Show Groq API key'}>{showGroqKey ? <EyeOff size={15}/> : <Eye size={15}/>}</button></div>
          <div className="ai-key-help">When Gemini hits a quota/rate limit or fails, EverAfter tries Groq automatically if this key is saved. Get one from <a href="https://console.groq.com/keys" target="_blank" rel="noreferrer">Groq Console <ExternalLink size={11}/></a>.</div>
          {aiError && <div className="ai-settings-feedback is-error"><AlertTriangle size={14}/>{aiError}</div>}
          {aiSuccess && <div className="ai-settings-feedback is-success"><CheckCircle2 size={14}/>{aiSuccess}</div>}
          <div className="ai-key-form-actions"><button type="submit" className="primary-button" disabled={aiSaving || aiLoading}>{aiSaving ? <span className="button-spinner"/> : <ShieldCheck size={15}/>} Save provider keys</button><span><Shield size={12}/> Keys are encrypted at rest and never shown in full again.</span></div>
        </form>
        {(aiStatus?.gemini_configured || aiStatus?.groq_configured) && <div className="ai-key-remove-actions">{aiStatus.gemini_configured && <button type="button" className="soft-button" disabled={aiSaving} onClick={() => void clearKey('gemini')}><Trash2 size={13}/> Remove Gemini key</button>}{aiStatus.groq_configured && <button type="button" className="soft-button" disabled={aiSaving} onClick={() => void clearKey('groq')}><Trash2 size={13}/> Remove Groq key</button>}</div>}
        <div className="ai-provider-flow"><span className={aiStatus?.gemini_configured ? 'provider-live' : ''}>1 · Gemini primary</span><span className="provider-arrow">→</span><span className={aiStatus?.gemini_configured && aiStatus.groq_configured ? 'provider-live' : ''}>2 · Groq fallback</span></div>
      </section>

      <section className="panel settings-panel">
        <div className="settings-section-title"><div className="settings-section-icon sage-setting-icon"><Gauge size={18}/></div><div><h3>Planning preferences</h3><p>Small choices that make the workspace more comfortable.</p></div></div>
        <div className="setting-row"><div><b>Reduce motion</b><small>Reduce interface animation when you prefer a calmer experience.</small></div><button type="button" role="switch" aria-checked={reducedMotion} className={`setting-switch ${reducedMotion ? 'enabled' : ''}`} onClick={() => setReducedMotion(!reducedMotion)}><span/></button></div>
        <div className="setting-row"><div><b>Reminder indicators</b><small>Show reminder status in the navigation bar.</small></div><button type="button" role="switch" aria-checked={remindersEnabled} className={`setting-switch ${remindersEnabled ? 'enabled' : ''}`} onClick={() => setRemindersEnabled(!remindersEnabled)}><span/></button></div>
      </section>
      <section className="panel settings-panel">
        <div className="settings-section-title"><div className="settings-section-icon lavender-setting-icon"><Download size={18}/></div><div><h3>Your data</h3><p>Take your planning details with you.</p></div></div>
        <div className="settings-data-actions"><div><b>Export the current event</b><small>Download a PDF snapshot with event details, tasks, budget, vendors and guest list.</small></div><button className="primary-button compact" onClick={onExport}><Download size={15}/> Download PDF</button></div>
        <div className="settings-data-actions"><div><b>Sign out</b><small>Your saved data remains in your account. This only clears the session from this browser.</small></div><button className="soft-button" onClick={onLogout}><LogOut size={15}/> Sign out</button></div>
      </section>
    </div>
    <div className="settings-footer-note"><ShieldCheck size={15}/><span>For production deployment, configure a strong server secret, a separate AI key encryption secret, HTTPS, rate limits, and account recovery before inviting real users.</span></div>
  </div>
}
