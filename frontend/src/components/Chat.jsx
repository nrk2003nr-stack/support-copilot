import { useState, useRef, useEffect } from 'react'
import { chatAPI, ticketsAPI } from '../api/client'
import { Send, Paperclip, AlertCircle, ThumbsUp, ThumbsDown, User, Mic } from 'lucide-react'
import toast from 'react-hot-toast'

export default function Chat() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [sessionId, setSessionId] = useState(() => localStorage.getItem('session_id'))
  const [convId, setConvId] = useState(() => {
    const value = localStorage.getItem('conversation_id')
    return value ? Number(value) : null
  })
  const [ticketId, setTicketId] = useState(null)
  const [imageFile, setImageFile] = useState(null)
  const [escalationWarning, setEscalationWarning] = useState(false)
  const bottomRef = useRef(null)
  const fileInputRef = useRef(null)
  const audioInputRef = useRef(null)

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  const sendMessage = async () => {
    if (!input.trim() && !imageFile) return
    const userMsg = { role: 'user', content: input, image: imageFile?.name }
    setMessages(prev => [...prev, userMsg])
    setLoading(true)
    setInput('')

    try {
      let data
      if (imageFile) {
        const res = await chatAPI.analyzeImage(imageFile, input)
        data = { reply: res.data.answer, session_id: sessionId || 'img', conversation_id: convId || 0, sentiment: {}, escalation_recommended: false, sources: [] }
        setImageFile(null)
      } else {
        const res = await chatAPI.send(input, sessionId, convId)
        data = res.data
        setSessionId(data.session_id)
        setConvId(data.conversation_id)
        setTicketId(data.ticket_id || null)
        localStorage.setItem('session_id', data.session_id)
        localStorage.setItem('conversation_id', String(data.conversation_id))
        if (data.escalation_recommended) setEscalationWarning(true)
      }
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.reply,
        sources: data.sources,
        sentiment: data.sentiment
      }])
    } catch (err) {
      toast.error('Failed to send message')
    } finally {
      setLoading(false)
    }
  }

  const handleEscalate = async () => {
    try {
      const res = await ticketsAPI.create({
        title: 'Customer escalation from chat',
        description: messages.map(m => `${m.role}: ${m.content}`).join('\n'),
        priority: 'urgent',
        conversation_id: convId,
        language: 'en',
      })
      setTicketId(res.data.id)
      toast.success('Ticket created. A human agent will contact you shortly.')
      setEscalationWarning(false)
    } catch {
      toast.error('Failed to escalate.')
    }
  }

  const handleAudio = async (file) => {
    if (!file) return
    setLoading(true)
    try {
      const res = await chatAPI.transcribe(file)
      if (res.data.text) {
        setInput(res.data.text)
        toast.success('Audio transcribed')
      } else {
        toast(res.data.message || 'Voice transcription is disabled locally')
      }
    } catch {
      toast.error('Audio transcription failed')
    } finally {
      setLoading(false)
    }
  }

  const submitQuickFeedback = async (thumbsUp) => {
    if (!ticketId) {
      toast('Feedback is available after a ticket is created.')
      return
    }
    try {
      await ticketsAPI.submitFeedback(ticketId, { rating: thumbsUp ? 5 : 2, thumbs_up: thumbsUp, comment: 'Chat quick feedback' })
      toast.success('Feedback saved')
    } catch {
      toast.error('Could not save feedback')
    }
  }

  return (
    <div className="flex flex-col h-screen max-w-3xl mx-auto bg-white shadow-xl rounded-xl overflow-hidden">
      {/* Header */}
      <div className="bg-indigo-600 text-white px-6 py-4 flex items-center gap-3">
        <div className="w-9 h-9 rounded-full bg-white/20 flex items-center justify-center">
          <User size={18} />
        </div>
        <div>
          <p className="font-semibold">Support Copilot</p>
          <p className="text-xs text-indigo-200">AI-powered · Always here to help</p>
        </div>
      </div>

      {/* Escalation Banner */}
      {escalationWarning && (
        <div className="bg-amber-50 border-b border-amber-200 px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2 text-amber-700 text-sm">
            <AlertCircle size={16} />
            <span>It seems you may need additional help. Would you like to speak with an agent?</span>
            {ticketId && <span className="font-medium">Ticket #{ticketId}</span>}
          </div>
          <button onClick={handleEscalate} className="text-xs bg-amber-600 text-white px-3 py-1.5 rounded-lg hover:bg-amber-700 transition">
            Connect Agent
          </button>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4">
        {messages.length === 0 && (
          <div className="text-center text-gray-400 mt-16">
            <p className="text-lg font-medium">How can I help you today?</p>
            <p className="text-sm mt-1">Ask anything or upload a screenshot</p>
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[75%] rounded-2xl px-4 py-3 text-sm shadow-sm ${
              msg.role === 'user'
                ? 'bg-indigo-600 text-white rounded-br-sm'
                : 'bg-gray-100 text-gray-800 rounded-bl-sm'
            }`}>
              {msg.image && <p className="text-xs opacity-70 mb-1">📎 {msg.image}</p>}
              <p className="leading-relaxed whitespace-pre-wrap">{msg.content}</p>
              {msg.sources?.length > 0 && (
                <p className="text-xs mt-2 opacity-60">Sources: {msg.sources.join(', ')}</p>
              )}
              {msg.role === 'assistant' && (
                <div className="flex gap-2 mt-2">
                  <button onClick={() => submitQuickFeedback(true)} title="Helpful" className="text-gray-400 hover:text-green-500">
                    <ThumbsUp size={14} />
                  </button>
                  <button onClick={() => submitQuickFeedback(false)} title="Not helpful" className="text-gray-400 hover:text-red-500">
                    <ThumbsDown size={14} />
                  </button>
                </div>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 rounded-2xl px-4 py-3 rounded-bl-sm">
              <div className="flex gap-1">
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay:'0ms'}}/>
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay:'150ms'}}/>
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay:'300ms'}}/>
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Image preview */}
      {imageFile && (
        <div className="px-4 pb-2 flex items-center gap-2 text-sm text-gray-600">
          <Paperclip size={14} />
          <span>{imageFile.name}</span>
          <button onClick={() => setImageFile(null)} className="text-red-500 text-xs ml-1">remove</button>
        </div>
      )}

      {/* Input bar */}
      <div className="border-t border-gray-100 px-4 py-3 flex items-center gap-2">
        <button
          onClick={() => fileInputRef.current?.click()}
          className="p-2 text-gray-400 hover:text-indigo-600 transition"
          title="Upload screenshot"
        >
          <Paperclip size={18} />
        </button>
        <button
          onClick={() => audioInputRef.current?.click()}
          className="p-2 text-gray-400 hover:text-indigo-600 transition"
          title="Voice input"
        >
          <Mic size={18} />
        </button>
        <input ref={audioInputRef} type="file" accept="audio/*" className="hidden"
          onChange={e => handleAudio(e.target.files[0])} />
        <input ref={fileInputRef} type="file" accept="image/*" className="hidden"
          onChange={e => setImageFile(e.target.files[0])} />
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && !e.shiftKey && sendMessage()}
          placeholder="Type your message..."
          className="flex-1 border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300"
        />
        <button
          onClick={sendMessage}
          disabled={loading}
          className="p-2 text-indigo-600 hover:bg-indigo-50 rounded-lg transition disabled:opacity-50"
        >
          <Send size={18} />
        </button>
      </div>
    </div>
  )
}
