/**
 * FeedbackWidget.jsx
 * CSAT feedback form for customers after ticket resolution
 */

import { useState } from 'react'
import { ticketsAPI } from '../api/client'
import { Star, Send } from 'lucide-react'
import toast from 'react-hot-toast'

export default function FeedbackWidget({ ticketId, onSubmitted }) {
  const [rating, setRating] = useState(0)
  const [comment, setComment] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const submit = async () => {
    if (rating === 0) {
      toast.error('Please select a rating')
      return
    }
    setSubmitting(true)
    try {
      await ticketsAPI.submitFeedback(ticketId, { rating, thumbs_up: rating >= 4, comment })
      toast.success('Thank you for your feedback!')
      onSubmitted?.()
    } catch (err) {
      toast.error('Failed to submit feedback')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="bg-indigo-50 rounded-lg p-4 border border-indigo-100">
      <p className="text-sm font-medium text-gray-700 mb-3">How satisfied are you with this resolution?</p>
      <div className="flex gap-2 mb-3">
        {[1, 2, 3, 4, 5].map(i => (
          <button
            key={i}
            onClick={() => setRating(i)}
            className="transition"
          >
            <Star
              size={20}
              className={i <= rating ? 'fill-amber-400 text-amber-400' : 'text-gray-300'}
            />
          </button>
        ))}
      </div>
      <textarea
        value={comment}
        onChange={e => setComment(e.target.value)}
        placeholder="Optional comment..."
        className="w-full text-sm border border-gray-200 rounded px-2 py-1.5 mb-2 focus:outline-none focus:ring-2 focus:ring-indigo-300"
        rows={2}
      />
      <button
        onClick={submit}
        disabled={submitting}
        className="w-full bg-indigo-600 text-white text-sm py-1.5 rounded hover:bg-indigo-700 transition flex items-center justify-center gap-2"
      >
        <Send size={14} />
        Submit Feedback
      </button>
    </div>
  )
}
