import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const app = readFileSync(new URL('../src/App.jsx', import.meta.url), 'utf8')
const client = readFileSync(new URL('../src/api/client.ts', import.meta.url), 'utf8')
const chat = readFileSync(new URL('../src/components/Chat.jsx', import.meta.url), 'utf8')

test('authenticated shell has top-right sign out and clears browser state', () => {
  assert.match(app, /<header/)
  assert.match(app, /Sign out/)
  assert.match(app, /authAPI\.logout/)
  assert.match(app, /sessionStorage\.clear/)
  assert.match(app, /localStorage\.removeItem\('access_token'\)/)
})

test('role-aware routes include chat, tickets, agent, analytics, and admin guards', () => {
  for (const route of ['/chat', '/tickets', '/agent', '/analytics', '/admin']) {
    assert.match(app, new RegExp(route.replace('/', '\\/')))
  }
  assert.match(app, /roles=\{\['agent', 'admin'\]\}/)
  assert.match(app, /roles=\{\['admin'\]\}/)
})

test('frontend API exposes chat, auth, ticket, admin, channel, and KB contracts', () => {
  for (const token of ['logout', 'refresh', 'timeline', 'comment', 'channelsAPI', 'knowledgeAPI', 'adminAPI']) {
    assert.match(client, new RegExp(token))
  }
})

test('chat flow persists conversation and wires attachments, voice, escalation, and feedback', () => {
  for (const token of ['conversation_id', 'analyzeImage', 'transcribe', 'ticketsAPI.create', 'submitQuickFeedback']) {
    assert.match(chat, new RegExp(token))
  }
})
