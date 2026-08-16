'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Sparkles, Loader2, RefreshCw } from 'lucide-react';
import { assistantChat } from '@/lib/api';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

const CATEGORIZED_QUESTIONS = [
  {
    category: 'SYSTEM',
    questions: [
      'What is ContextIQ?',
      'Why was it built?',
      'Explain the architecture',
      'Explain the complete pipeline',
      'How does compression work?',
      'How does caching work?',
      'What happens to tokens?',
    ],
  },
  {
    category: 'DOCUMENTS',
    questions: [
      'How do I upload a document?',
      'What file types are supported?',
      'How does versioning work?',
      'How do I delete a document?',
    ],
  },
  {
    category: 'QUERYING',
    questions: [
      'How do I query a document?',
      'How does CSV retrieval work?',
      'Why is structured retrieval used?',
    ],
  },
  {
    category: 'ANALYTICS',
    questions: [
      'Where do I see system health?',
      'What does grounding score mean?',
      'What is compression ratio?',
      'Where can I see latency and token savings?',
    ],
  },
  {
    category: 'SECURITY',
    questions: [
      'What are the guardrails?',
      'What is grounding?',
      'How does the system handle prompt injection?',
    ],
  },
];

export function SystemAssistantView() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content:
        'Hello! I am the **ContextIQ System Assistant** — your AI guide to the system architecture, 8-phase RAG pipeline, analytics, and dashboard navigation.\n\nHow can I help you today? Choose a suggested question below or type your prompt!',
    },
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState<string>('SYSTEM');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const handleSendMessage = async (userPrompt?: string) => {
    const promptToSend = userPrompt || input.trim();
    if (!promptToSend || isLoading) return;

    const newMessages: Message[] = [...messages, { role: 'user', content: promptToSend }];
    setMessages(newMessages);
    if (!userPrompt) setInput('');
    setIsLoading(true);

    try {
      const res = await assistantChat(newMessages);
      setMessages((prev) => [...prev, { role: 'assistant', content: res.content }]);
    } catch (err: unknown) {
      const errMsg = err instanceof Error ? err.message : 'Failed to get assistant response.';
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `⚠️ Assistant Error: ${errMsg}`,
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleClearHistory = () => {
    setMessages([
      {
        role: 'assistant',
        content:
          'Chat history reset. Ask me anything about ContextIQ system architecture, pipeline, or UI navigation!',
      },
    ]);
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Header Banner */}
      <div
        className="p-5 rounded-2xl border flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4"
        style={{
          backgroundColor: 'var(--surface)',
          borderColor: 'var(--border)',
        }}
      >
        <div className="flex items-center gap-3">
          <div
            className="h-10 w-10 rounded-xl flex items-center justify-center shrink-0"
            style={{
              backgroundColor: 'color-mix(in srgb, var(--primary) 12%, transparent)',
              color: 'var(--primary)',
              border: '1px solid color-mix(in srgb, var(--primary) 25%, transparent)',
            }}
          >
            <Bot className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-base font-brand font-bold text-[color:var(--foreground)]">
              ContextIQ System Assistant
            </h2>
            <p className="text-xs font-sans-plex text-[color:var(--muted)]">
              AI guide for ContextIQ architecture, 8-phase pipeline, analytics & UI navigation.
            </p>
          </div>
        </div>

        <button
          onClick={handleClearHistory}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-mono-plex transition-all shrink-0"
          style={{
            backgroundColor: 'var(--surface-elevated)',
            border: '1px solid var(--border)',
            color: 'var(--muted)',
          }}
        >
          <RefreshCw className="h-3.5 w-3.5" />
          Reset Chat
        </button>
      </div>

      {/* Suggested Questions Panel */}
      <div
        className="p-4 rounded-2xl border space-y-3"
        style={{
          backgroundColor: 'var(--surface)',
          borderColor: 'var(--border)',
        }}
      >
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4" style={{ color: 'var(--primary)' }} />
          <span className="text-xs font-mono-plex font-semibold uppercase tracking-wider text-[color:var(--muted-foreground)]">
            Suggested Topics
          </span>
        </div>

        {/* Category Tabs */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1">
          {CATEGORIZED_QUESTIONS.map(({ category }) => {
            const isActive = selectedCategory === category;
            return (
              <button
                key={category}
                onClick={() => setSelectedCategory(category)}
                className="px-2.5 py-1 rounded-lg text-xs font-mono-plex font-medium transition-all shrink-0"
                style={
                  isActive
                    ? {
                        backgroundColor: 'var(--primary)',
                        color: 'var(--primary-foreground, #fff)',
                      }
                    : {
                        backgroundColor: 'var(--surface-elevated)',
                        color: 'var(--muted)',
                        border: '1px solid var(--border-subtle)',
                      }
                }
              >
                {category}
              </button>
            );
          })}
        </div>

        {/* Question Pills */}
        <div className="flex flex-wrap gap-2 pt-1">
          {CATEGORIZED_QUESTIONS.find((c) => c.category === selectedCategory)?.questions.map((q) => (
            <button
              key={q}
              onClick={() => handleSendMessage(q)}
              disabled={isLoading}
              className="text-xs font-sans-plex px-3 py-1.5 rounded-xl border transition-all text-left hover:scale-[1.01] active:scale-[0.99]"
              style={{
                backgroundColor: 'var(--surface-elevated)',
                borderColor: 'var(--border-subtle)',
                color: 'var(--foreground)',
              }}
            >
              {q}
            </button>
          ))}
        </div>
      </div>

      {/* Chat Messages Container */}
      <div
        className="rounded-2xl border p-4 sm:p-6 min-h-[380px] max-h-[550px] flex flex-col justify-between"
        style={{
          backgroundColor: 'var(--surface)',
          borderColor: 'var(--border)',
        }}
      >
        <div className="space-y-4 overflow-y-auto pr-1 flex-1">
          {messages.map((msg, idx) => {
            const isUser = msg.role === 'user';
            return (
              <div
                key={idx}
                className={`flex gap-3 text-xs sm:text-sm font-sans-plex animate-fade-in ${
                  isUser ? 'justify-end' : 'justify-start'
                }`}
              >
                {!isUser && (
                  <div
                    className="h-7 w-7 rounded-lg flex items-center justify-center shrink-0 mt-0.5"
                    style={{
                      backgroundColor: 'color-mix(in srgb, var(--primary) 15%, transparent)',
                      color: 'var(--primary)',
                    }}
                  >
                    <Bot className="h-4 w-4" />
                  </div>
                )}

                <div
                  className={`p-3.5 rounded-2xl max-w-[85%] sm:max-w-[75%] space-y-1 ${
                    isUser ? 'rounded-tr-none' : 'rounded-tl-none'
                  }`}
                  style={
                    isUser
                      ? {
                          backgroundColor: 'var(--primary)',
                          color: '#ffffff',
                        }
                      : {
                          backgroundColor: 'var(--surface-elevated)',
                          border: '1px solid var(--border-subtle)',
                          color: 'var(--foreground)',
                        }
                  }
                >
                  <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                </div>

                {isUser && (
                  <div
                    className="h-7 w-7 rounded-lg flex items-center justify-center shrink-0 mt-0.5"
                    style={{
                      backgroundColor: 'var(--surface-muted)',
                      color: 'var(--muted)',
                    }}
                  >
                    <User className="h-4 w-4" />
                  </div>
                )}
              </div>
            );
          })}

          {isLoading && (
            <div className="flex items-center gap-3 text-xs font-sans-plex text-[color:var(--muted)] animate-pulse">
              <div
                className="h-7 w-7 rounded-lg flex items-center justify-center"
                style={{
                  backgroundColor: 'color-mix(in srgb, var(--primary) 15%, transparent)',
                  color: 'var(--primary)',
                }}
              >
                <Bot className="h-4 w-4" />
              </div>
              <div className="flex items-center gap-2 px-3 py-2 rounded-2xl bg-[color:var(--surface-elevated)] border border-[color:var(--border-subtle)]">
                <Loader2 className="h-3.5 w-3.5 animate-spin text-[color:var(--primary)]" />
                <span>Thinking...</span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar */}
        <div className="pt-4 mt-4 border-t border-[color:var(--border-subtle)]">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSendMessage();
            }}
            className="flex items-center gap-2"
          >
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about ContextIQ pipeline, architecture, or navigation..."
              disabled={isLoading}
              className="flex-1 text-xs sm:text-sm font-sans-plex px-4 py-2.5 rounded-xl border outline-none transition-all"
              style={{
                backgroundColor: 'var(--surface-elevated)',
                borderColor: 'var(--border)',
                color: 'var(--foreground)',
              }}
            />
            <button
              type="submit"
              disabled={!input.trim() || isLoading}
              className="h-10 px-4 rounded-xl flex items-center justify-center font-sans-plex text-xs font-semibold gap-1.5 transition-all disabled:opacity-50"
              style={{
                backgroundColor: 'var(--primary)',
                color: '#ffffff',
              }}
            >
              <span>Send</span>
              <Send className="h-3.5 w-3.5" />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
