import { useEffect, useState, type FormEvent } from 'react'
import { AlertTriangle, ArrowRight, Bot, Check, CheckCheck, Clock3, KeyRound, MessageCircle, Plus, Send, Settings2, ShieldCheck, Sparkles, WandSparkles } from 'lucide-react'
import { request, type AIProviderStatus, type Event, type Task } from '../lib/api'

type ToastKind = 'success' | 'error' | 'info'
type ToastFn = (title: string, message?: string, kind?: ToastKind) => void
type SuggestedTask = { title: string; category: string; weeks_before: number; priority: string; description: string }
type AgentResponse = { reply: string; suggestions: string[]; suggested_tasks: SuggestedTask[]; follow_up_questions: string[]; guardrail_notes: string[]; generated_by: 'gemini' | 'groq' }
type ChatMessage = { role: 'user' | 'assistant'; content: string; provider?: 'gemini' | 'groq' }

export default function PlanningAssistantPanel({ event, tasks, onTaskAdded, toast, onOpenSettings }: { event: Event | null; tasks: Task[]; onTaskAdded: () => void; toast: ToastFn; onOpenSettings: () => void }) {
  // No seeded assistant greeting, prewritten advice, or template suggestions are shown.
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [latest, setLatest] = useState<AgentResponse | null>(null)
  const [adding, setAdding] = useState(false)
  const [aiStatus, setAIStatus] = useState<AIProviderStatus | null>(null)
  const [checkingAI, setCheckingAI] = useState(true)
  const [lastError, setLastError] = useState('')
  const quickPrompts = ['Help me stay within budget', 'Build a realistic timeline', 'Suggest ideas for my event', 'What am I forgetting?']

  useEffect(() => {
    let active = true
    request<AIProviderStatus>('/api/ai/settings')
      .then(status => { if (active) setAIStatus(status) })
      .catch(error => { if (active) setLastError(error instanceof Error ? error.message : 'Could not check AI provider setup.') })
      .finally(() => { if (active) setCheckingAI(false) })
    return () => { active = false }
  }, [])

  const ask = async (raw: string) => {
    const question = raw.trim()
    if (!question || loading) return
    if (!aiStatus?.ai_enabled) {
      setLastError('Add a Gemini API key in Settings before asking the planning agent.')
      return
    }
    const prior = messages.slice(-8)
    // Hide the previous response card while this request runs so a failure can never look like a fresh answer.
    setLatest(null)
    setMessages(current => [...current, { role: 'user', content: question }].slice(-16))
    setInput('')
    setLoading(true)
    setLastError('')
    try {
      const result = await request<AgentResponse>('/api/ai/assistant', {
        method: 'POST',
        body: JSON.stringify({
          message: question,
          event_type: event?.event_type || 'Wedding',
          event_title: event?.title || 'My celebration',
          event_date: event?.event_date || null,
          budget: event?.budget ?? 0,
          guest_count: event?.guest_count || 80,
          theme: event?.theme || 'Thoughtful celebration',
          location: event?.location || 'India',
          notes: event?.notes || '',
          existing_tasks: tasks.slice(0, 30).map(t => t.title),
          conversation: prior,
        }),
      })
      setLatest(result)
      setMessages(current => [...current, { role: 'assistant', content: result.reply, provider: result.generated_by }].slice(-16))
      setAIStatus(current => current ? { ...current, ai_enabled: true } : current)
    } catch (err) {
      const text = err instanceof Error ? err.message : 'The AI provider could not complete this request.'
      setLastError(text)
      toast('The AI planning request failed', text, 'error')
      // Do not append canned text or fallback suggestions to the conversation.
      try { setAIStatus(await request<AIProviderStatus>('/api/ai/settings')) } catch { /* keep the previous status */ }
    } finally { setLoading(false) }
  }

  const submit = (e: FormEvent) => { e.preventDefault(); void ask(input) }
  const addSuggestedTasks = async () => {
    if (!event || !latest?.suggested_tasks.length) return
    setAdding(true)
    let added = 0
    try {
      for (const item of latest.suggested_tasks) {
        if (tasks.some(t => t.title.trim().toLowerCase() === item.title.trim().toLowerCase())) continue
        let due_date: string | null = null
        if (event.event_date) {
          const date = new Date(`${event.event_date}T00:00:00`)
          date.setDate(date.getDate() - Math.max(0, Math.min(104, item.weeks_before)) * 7)
          due_date = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
        }
        await request('/api/tasks', { method: 'POST', body: JSON.stringify({ event_id: event.id, title: item.title, category: item.category || 'Planning', due_date, priority: item.priority, status: 'To do', description: item.description }) })
        added++
      }
      toast('AI tasks saved', `${added} AI-generated task${added === 1 ? '' : 's'} added. Existing tasks were left alone.`)
      setLatest(current => current ? { ...current, suggested_tasks: [] } : current)
      onTaskAdded()
    } catch (err) {
      toast('Some tasks may not have been saved', err instanceof Error ? err.message : 'Please refresh the task board and check it.', 'error')
      onTaskAdded()
    } finally { setAdding(false) }
  }

  const providerLabel = latest?.generated_by === 'groq' ? 'Groq fallback used' : latest?.generated_by === 'gemini' ? 'Generated by Gemini' : aiStatus?.ai_enabled ? (aiStatus.groq_configured ? 'Gemini · Groq fallback ready' : 'Gemini connected') : 'API key required'

  return <section className="panel planning-agent-panel">
    <div className="planning-agent-header"><div className="agent-avatar"><Bot size={22}/><span className={aiStatus?.ai_enabled ? '' : 'agent-dot-off'}/></div><div className="planning-agent-title"><div className="eyebrow"><Sparkles size={12}/> YOUR GENAI PLANNING PARTNER</div><h3>Let's plan it together.</h3><p>Ask about your event, budget, timeline, vendors, guests, or creative direction. Every answer comes from a configured AI provider.</p></div><div className={`agent-status ${aiStatus?.ai_enabled ? '' : 'agent-status-off'}`}><span/> {checkingAI ? 'Checking keys…' : providerLabel}</div></div>
    <div className="planning-agent-body">
      <div className="agent-chat-column">
        <div className="agent-chat-log" aria-live="polite" aria-label="AI planning assistant conversation">
          {messages.map((message, index) => <div key={`${index}-${message.role}`} className={`agent-message agent-message-${message.role}`}><div className="agent-message-avatar">{message.role === 'assistant' ? <Sparkles size={14}/> : 'Y'}</div><div className="agent-message-content"><small>{message.role === 'assistant' ? (message.provider === 'groq' ? 'EVERAFTER · GROQ' : 'EVERAFTER · GEMINI') : 'YOU'}</small><p>{message.content}</p></div></div>)}
          {loading && <div className="agent-message agent-message-assistant"><div className="agent-message-avatar"><Sparkles size={14}/></div><div className="agent-thinking"><span/><span/><span/> <small>{aiStatus?.groq_configured ? 'Asking Gemini… Groq is ready if needed' : 'Asking Gemini…'}</small></div></div>}
          {!messages.length && aiStatus?.ai_enabled && !checkingAI && <div className="agent-no-message"><div className="agent-empty-icon"><MessageCircle size={20}/></div><b>Your planning conversation starts here.</b><p>Ask a specific question. The AI will use your current event, known budget, guest count, and existing tasks as context.</p></div>}
          {checkingAI && <div className="agent-no-message"><div className="agent-empty-icon"><Sparkles size={20}/></div><b>Checking your AI setup…</b><p>EverAfter is checking whether your account has a provider key saved.</p></div>}
          {!checkingAI && !aiStatus?.ai_enabled && <div className="agent-no-message agent-key-required"><div className="agent-empty-icon"><KeyRound size={20}/></div><b>Connect Gemini to begin</b><p>AI-generated suggestions stay hidden until you add your Gemini API key. No hardcoded suggestion library will be shown as AI.</p><button className="primary-button" onClick={onOpenSettings}><Settings2 size={15}/> Open AI settings <ArrowRight size={14}/></button></div>}
        </div>
        {aiStatus?.ai_enabled && <div className="agent-quick-prompts"><small>ASK THE AGENT</small>{quickPrompts.map(prompt => <button key={prompt} onClick={() => void ask(prompt)} disabled={loading}><WandSparkles size={12}/>{prompt}</button>)}</div>}
        {lastError && <div className="agent-error-state"><AlertTriangle size={14}/><span>{lastError}</span>{!aiStatus?.ai_enabled && <button onClick={onOpenSettings}>Set up key</button>}</div>}
        <form className={`agent-composer ${!aiStatus?.ai_enabled ? 'agent-composer-locked' : ''}`} onSubmit={submit}><textarea value={input} onChange={e => setInput(e.target.value)} rows={2} maxLength={2000} placeholder={aiStatus?.ai_enabled ? 'Ask the AI anything about this event…' : 'Add a Gemini API key in Settings to start…'} aria-label="Message your AI planning assistant" disabled={!aiStatus?.ai_enabled || checkingAI || loading}/><button disabled={!aiStatus?.ai_enabled || checkingAI || loading || !input.trim()} aria-label="Send message">{loading ? <span className="button-spinner"/> : <Send size={17}/>}</button><small>{input.length}/2000</small></form>
        <div className="agent-privacy-note"><AlertTriangle size={13}/><span>AI drafts only: EverAfter does not book vendors, verify live availability, contact people, or spend money. Generated content is checked before display.</span></div>
      </div>
      <aside className="agent-recommendations"><div className="agent-recommendations-heading"><div><div className="eyebrow">AI-GENERATED OUTPUT</div><h4>From chat to checklist</h4></div><div className="agent-sparkle-orb"><Sparkles size={17}/></div></div>
        {!latest && <div className="agent-suggestion-empty"><div className="agent-empty-icon">{aiStatus?.ai_enabled ? <MessageCircle size={20}/> : <KeyRound size={20}/>}</div><b>{aiStatus?.ai_enabled ? 'Your AI recommendations will appear here.' : 'AI recommendations are locked.'}</b><p>{aiStatus?.ai_enabled ? 'Ask a question to generate personalized ideas and optional tasks. Nothing gets saved until you approve it.' : 'Configure Gemini in Settings. Groq can be added as an optional fallback for provider errors or quota limits.'}</p>{!aiStatus?.ai_enabled && <button className="soft-button" onClick={onOpenSettings}><Settings2 size={14}/> Configure AI</button>}</div>}
        {latest && <>
          {latest.suggestions.length > 0 && <div className="agent-suggestion-list">{latest.suggestions.map((suggestion, i) => <div className="agent-suggestion" key={`${suggestion}-${i}`}><span>{String(i + 1).padStart(2, '0')}</span><p>{suggestion}</p></div>)}</div>}
          {latest.suggested_tasks.length > 0 && <><div className="agent-suggested-tasks-heading"><b><CheckCheck size={14}/> AI suggested tasks</b><small>{latest.suggested_tasks.length} drafts</small></div><div className="agent-task-suggestions">{latest.suggested_tasks.map((task,i)=><div className="agent-task-suggestion" key={`${task.title}-${i}`}><div><b>{task.title}</b><small><Clock3 size={11}/>{task.weeks_before===0?'Event week':`${task.weeks_before} weeks before`} · {task.priority}</small></div><span>{task.category}</span></div>)}</div><button className="primary-button agent-add-tasks" onClick={addSuggestedTasks} disabled={adding || !event}>{adding ? <span className="button-spinner"/> : <Plus size={15}/>} Add AI tasks to my board <ArrowRight size={14}/></button></>}
          {latest.follow_up_questions.length > 0 && <div className="agent-followups"><b>Follow-up questions from AI</b>{latest.follow_up_questions.map(q=><button key={q} onClick={()=>void ask(q)} disabled={loading}>{q}<ArrowRight size={12}/></button>)}</div>}
          {latest.guardrail_notes.length > 0 && <div className="agent-guardrails"><ShieldCheckIcon/><span>{latest.guardrail_notes.join(' ')}</span></div>}
          <div className="agent-provider-receipt"><Check size={12}/> Response generated by {latest.generated_by === 'gemini' ? 'Gemini' : 'Groq fallback'} and validated before display.</div>
        </>}
      </aside>
    </div>
    <div className="agent-footer"><span><Check size={13}/> You decide what gets saved</span><span>Context: {event?.event_type || 'Event'} · {event?.guest_count || 80} guests · {event?.theme || 'Your style'}</span></div>
  </section>
}

function ShieldCheckIcon() { return <span className="agent-guardrail-icon"><AlertTriangle size={13}/></span> }
