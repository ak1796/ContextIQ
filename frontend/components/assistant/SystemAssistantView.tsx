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
      'What models does this use and why?',
      'What is the budget controller and how do I set it?',
    ],
  },
  {
    category: 'DOCUMENTS',
    questions: [
      'How do I upload a document?',
      'What file types are supported?',
      'How does versioning work?',
      'How do I delete a document?',
      'What happens if I upload the same document twice?',
      'How are uploaded files chunked and indexed?',
    ],
  },
  {
    category: 'QUERYING',
    questions: [
      'How do I query a document?',
      'How does CSV retrieval work?',
      'Why is structured retrieval used?',
      "What's the difference between structured lookup and semantic search?",
      'Why did my query get an empty answer?',
      'How do k and top_n parameters affect retrieval?',
    ],
  },
  {
    category: 'ANALYTICS',
    questions: [
      'Where do I see system health?',
      'What does grounding score mean?',
      'What is compression ratio?',
      'Where can I see latency and token savings?',
      'What metrics does the Observability dashboard track?',
      'How is total latency calculated across pipeline stages?',
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

function renderInlineText(text: string): React.ReactNode[] {
  const pattern = /(`[^`]+`|\*\*[^*]+\*\*|__[^_]+__|\*[^*]+\*|_[^_]+_)/g;
  const parts = text.split(pattern);

  return parts.map((part, i) => {
    if (!part) return null;
    if (part.startsWith('`') && part.endsWith('`') && part.length > 2) {
      return (
        <code
          key={i}
          className="px-1.5 py-0.5 rounded text-[0.85em] font-mono font-medium bg-[color:var(--surface-muted)] text-[color:var(--primary)] border border-[color:var(--border-subtle)]"
        >
          {part.slice(1, -1)}
        </code>
      );
    }
    if (
      (part.startsWith('**') && part.endsWith('**') && part.length > 4) ||
      (part.startsWith('__') && part.endsWith('__') && part.length > 4)
    ) {
      return (
        <strong key={i} className="font-semibold text-[color:var(--foreground)]">
          {renderInlineText(part.slice(2, -2))}
        </strong>
      );
    }
    if (
      (part.startsWith('*') && part.endsWith('*') && part.length > 2) ||
      (part.startsWith('_') && part.endsWith('_') && part.length > 2)
    ) {
      return (
        <em key={i} className="italic">
          {renderInlineText(part.slice(1, -1))}
        </em>
      );
    }
    return part;
  });
}

function FormattedMessage({ content }: { content: string }) {
  if (!content) return null;

  const lines = content.split('\n');
  const elements: React.ReactNode[] = [];

  let i = 0;
  while (i < lines.length) {
    const trimmed = lines[i].trim();

    if (!trimmed) {
      i++;
      continue;
    }

    if (trimmed.startsWith('# ')) {
      elements.push(
        <h1 key={`h1-${i}`} className="text-base font-bold font-brand text-[color:var(--foreground)] mt-4 mb-2">
          {renderInlineText(trimmed.slice(2))}
        </h1>
      );
      i++;
      continue;
    }

    if (trimmed.startsWith('## ')) {
      elements.push(
        <h2 key={`h2-${i}`} className="text-sm font-bold font-brand text-[color:var(--foreground)] mt-3.5 mb-1.5">
          {renderInlineText(trimmed.slice(3))}
        </h2>
      );
      i++;
      continue;
    }

    if (trimmed.startsWith('### ')) {
      elements.push(
        <h3 key={`h3-${i}`} className="text-xs font-bold font-brand uppercase tracking-wider text-[color:var(--primary)] mt-3 mb-1.5">
          {renderInlineText(trimmed.slice(4))}
        </h3>
      );
      i++;
      continue;
    }

    const bulletMatch = trimmed.match(/^[-*•]\s+(.+)/);
    if (bulletMatch) {
      const items: string[] = [];
      const startIdx = i;
      while (i < lines.length) {
        const lineTrimmed = lines[i].trim();
        const itemMatch = lineTrimmed.match(/^[-*•]\s+(.+)/);
        if (itemMatch) {
          items.push(itemMatch[1]);
          i++;
        } else {
          break;
        }
      }
      elements.push(
        <ul key={`ul-${startIdx}`} className="my-3 space-y-2 list-disc pl-5 text-[color:var(--foreground)]">
          {items.map((item, idx) => (
            <li key={idx} className="leading-relaxed">
              {renderInlineText(item)}
            </li>
          ))}
        </ul>
      );
      continue;
    }

    const numberMatch = trimmed.match(/^(\d+)[\.\)]\s+(.+)/);
    if (numberMatch) {
      const items: string[] = [];
      const startIdx = i;
      while (i < lines.length) {
        const lineTrimmed = lines[i].trim();
        const itemMatch = lineTrimmed.match(/^(\d+)[\.\)]\s+(.+)/);
        if (itemMatch) {
          items.push(itemMatch[2]);
          i++;
        } else {
          break;
        }
      }
      elements.push(
        <ol key={`ol-${startIdx}`} className="my-3 space-y-2 list-decimal pl-5 text-[color:var(--foreground)]">
          {items.map((item, idx) => (
            <li key={idx} className="leading-relaxed">
              {renderInlineText(item)}
            </li>
          ))}
        </ol>
      );
      continue;
    }

    const isUppercaseHeading = /^[A-Z0-9\s_\-\(\)&]{4,50}:$/.test(trimmed);
    if (isUppercaseHeading) {
      elements.push(
        <div key={`head-${i}`} className="text-xs font-bold font-brand uppercase tracking-wider text-[color:var(--primary)] mt-4 mb-2">
          {trimmed}
        </div>
      );
      i++;
      continue;
    }

    elements.push(
      <p key={`p-${i}`} className="leading-relaxed my-2">
        {renderInlineText(trimmed)}
      </p>
    );
    i++;
  }

  return <div className="space-y-3 text-xs sm:text-sm font-sans-plex">{elements}</div>;
}

export function SystemAssistantView() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content:
        'Hello! I am the ContextIQ System Assistant - your AI guide to the system architecture, ContextIQ processing pipeline, analytics, and dashboard navigation.\n\nHow can I help you today? Choose a suggested question below or type your prompt!',
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
              AI guide for ContextIQ architecture, ContextIQ pipeline, analytics & UI navigation.
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
                  <FormattedMessage content={msg.content} />
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
