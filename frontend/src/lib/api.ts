export const API = import.meta.env.VITE_API_URL || 'https://evenafter-planner.vercel.app/api'
export type User = { id: number; name: string; email: string }
export type AIProviderStatus = { gemini_configured: boolean; gemini_masked: string | null; groq_configured: boolean; groq_masked: string | null; ai_enabled: boolean; primary_provider: 'gemini' | 'none'; fallback_provider: 'groq' | 'none' }
export type Event = { id: number; owner_id: number; title: string; event_type: string; event_date: string | null; venue: string; location: string; guest_count: number; budget: number; theme: string; notes?: string }
export type Task = { id: number; event_id: number; title: string; category: string; due_date: string | null; priority: string; status: 'To do' | 'In progress' | 'Done'; description: string; sort_order?: number }
export type Vendor = { id: number; event_id: number; name: string; category: string; quote: number; status: string; rating: number; contact: string; notes: string }
export type Guest = { id: number; event_id: number; name: string; email: string; group_name: string; rsvp: string; plus_one: boolean; dietary: string }
export type Expense = { id: number; event_id: number; category: string; planned: number; spent: number; color: string }
export type DashboardData = { event: Event; tasks: {total:number;completed:number;upcoming:number}; guests:{total:number;confirmed:number;pending:number}; vendors:{total:number;booked:number}; budget:{limit:number;planned:number;spent:number;remaining:number;percent_spent:number}; expenses: Expense[]; next_tasks: Task[] }

let authToken = localStorage.getItem('everafter-token') || ''
export function setToken(token: string) { authToken = token; if (token) localStorage.setItem('everafter-token', token); else localStorage.removeItem('everafter-token') }
export function getToken() { return authToken }
export async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers || {})
  if (!(options.body instanceof FormData)) headers.set('Content-Type', 'application/json')
  if (authToken) headers.set('Authorization', `Bearer ${authToken}`)
  const response = await fetch(`${API}${path}`, { ...options, headers })
  if (response.status === 204) return undefined as T
  const body = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(body.detail || `Request failed (${response.status})`)
  return body as T
}
export function money(value: number) { return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(value || 0) }
export function prettyDate(value?: string | null) { if (!value) return 'Date to be decided'; return new Date(`${value}T00:00:00`).toLocaleDateString('en-IN', { day:'numeric', month:'short', year:'numeric' }) }
export function relativeDate(value?: string | null) {
  if (!value) return 'No due date'
  const diff = Math.ceil((new Date(`${value}T00:00:00`).getTime() - new Date(new Date().toDateString()).getTime()) / 86400000)
  if (diff < 0) return `${Math.abs(diff)}d overdue`
  if (diff === 0) return 'Due today'
  if (diff === 1) return 'Tomorrow'
  if (diff <= 7) return `In ${diff} days`
  return prettyDate(value)
}
