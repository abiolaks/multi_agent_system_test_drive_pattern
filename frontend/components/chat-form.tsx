"use client";

import { useState } from "react";

interface ChatFormProps {
  onSubmit: (question: string) => void;
  disabled: boolean;
}

export function ChatForm({ onSubmit, disabled }: ChatFormProps) {
  const [question, setQuestion] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = question.trim();
    if (!trimmed || disabled) return;
    onSubmit(trimmed);
    setQuestion("");
  };

  return (
    <form className="chat-form" onSubmit={handleSubmit}>
      <input
        className="chat-input"
        type="text"
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        placeholder="Ask about your Fabric workspace data…"
        disabled={disabled}
        aria-label="Question"
      />
      <button type="submit" className="action-button" disabled={disabled || !question.trim()}>
        Ask
      </button>
    </form>
  );
}
