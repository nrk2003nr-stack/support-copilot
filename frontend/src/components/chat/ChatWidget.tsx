import { useState, useRef, useEffect } from "react";
import { useMutation } from "@tanstack/react-query";
import { chatAPI, ticketsAPI } from "../../api/client";
import {
  Send, ThumbsUp, ThumbsDown, AlertTriangle, Loader2, Bot, User
} from "lucide-react";

interface Message {
  id?: string;
  role: "user" | "bot" | "agent";
  content: string;
  created_at?: string;
  feedback?: number;
  language?: string;
}

interface ChatWidgetProps {
  ticketId: string;
  initialMessages?: Message[];
  onHandoff?: () => void;
}

export default function ChatWidget({ ticketId, initialMessages = [], onHandoff }: ChatWidgetProps) {
  const [messages, setMessages] = useState<Message[]>(initialMessages);
  const [input, setInput] = useState("");
  const [isHandedOff, setIsHandedOff] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMutation = useMutation({
    mutationFn: ({ ticket_id, message }: { ticket_id: string; message: string }) =>
      chatAPI.send(ticket_id, message),
    onSuccess: (res) => {
      const data = res.data;
      setMessages((prev) => [
        ...prev,
        {
          id: data.message_id,
          role: "bot",
          content: data.bot_message,
          language: data.detected_language,
        },
      ]);
      if (data.should_handoff) {
        setIsHandedOff(true);
        onHandoff?.();
      }
    },
  });

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || sendMutation.isPending) return;
    const msg = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: msg }]);
    sendMutation.mutate({ ticket_id: ticketId, message: msg });
  };

  const handleFeedback = async (messageId: string, rating: number) => {
    await ticketsAPI.messageFeedback(ticketId, messageId, { rating });
    setMessages((prev) =>
      prev.map((m) => (m.id === messageId ? { ...m, feedback: rating } : m))
    );
  };

  return (
    <div className="flex flex-col h-full bg-white rounded-xl border border-gray-200">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-100 flex items-center gap-2">
        <div className="w-7 h-7 bg-blue-600 rounded-full flex items-center justify-center">
          <Bot size={14} className="text-white" />
        </div>
        <span className="text-sm font-medium text-gray-800">Support Assistant</span>
        {isHandedOff && (
          <span className="ml-auto flex items-center gap-1 text-xs text-amber-600 bg-amber-50 px-2 py-1 rounded-full">
            <AlertTriangle size={11} />
            Connecting to agent...
          </span>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.length === 0 && (
          <div className="text-center text-gray-400 text-sm pt-8">
            How can I help you today?
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`flex gap-2 ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            {msg.role !== "user" && (
              <div className="w-7 h-7 rounded-full bg-gray-100 flex items-center justify-center flex-shrink-0 mt-0.5">
                {msg.role === "agent" ? <User size={13} className="text-gray-600" /> : <Bot size={13} className="text-blue-600" />}
              </div>
            )}
            <div className="max-w-[75%]">
              <div
                className={`px-3 py-2 rounded-xl text-sm leading-relaxed ${
                  msg.role === "user"
                    ? "bg-blue-600 text-white rounded-tr-sm"
                    : "bg-gray-100 text-gray-800 rounded-tl-sm"
                }`}
              >
                {msg.content}
              </div>
              {/* Thumbs feedback for bot messages */}
              {msg.role === "bot" && msg.id && (
                <div className="flex gap-1 mt-1">
                  <button
                    onClick={() => handleFeedback(msg.id!, 1)}
                    className={`p-1 rounded hover:bg-gray-100 ${msg.feedback === 1 ? "text-green-600" : "text-gray-400"}`}
                  >
                    <ThumbsUp size={12} />
                  </button>
                  <button
                    onClick={() => handleFeedback(msg.id!, -1)}
                    className={`p-1 rounded hover:bg-gray-100 ${msg.feedback === -1 ? "text-red-500" : "text-gray-400"}`}
                  >
                    <ThumbsDown size={12} />
                  </button>
                </div>
              )}
            </div>
          </div>
        ))}

        {sendMutation.isPending && (
          <div className="flex gap-2">
            <div className="w-7 h-7 rounded-full bg-gray-100 flex items-center justify-center">
              <Bot size={13} className="text-blue-600" />
            </div>
            <div className="bg-gray-100 rounded-xl rounded-tl-sm px-3 py-2">
              <Loader2 size={14} className="text-gray-400 animate-spin" />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSend} className="p-3 border-t border-gray-100 flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={isHandedOff ? "Agent will respond shortly..." : "Type your message..."}
          disabled={isHandedOff || sendMutation.isPending}
          className="flex-1 px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-50 disabled:text-gray-400"
        />
        <button
          type="submit"
          disabled={!input.trim() || sendMutation.isPending || isHandedOff}
          className="p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
        >
          <Send size={16} />
        </button>
      </form>
    </div>
  );
}