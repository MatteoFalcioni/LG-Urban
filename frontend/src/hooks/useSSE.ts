/**
 * useSSE: hook for Server-Sent Events (SSE) streaming from POST /messages endpoint.
 * Handles EventSource connection, token streaming, tool events, and completion.
 */

import { useCallback, useRef, useState } from 'react';
import type { SSEEvent } from '@/types/api';

import type { Artifact } from '@/types/api';

interface UseSSEOptions {
  onToken?: (content: string) => void;
  onThinking?: (content: string) => void;
  onToolStart?: (name: string, input: any) => void;
  onToolEnd?: (name: string, output: any, artifacts?: Artifact[]) => void;
  onTitleUpdated?: (title: string) => void;
  onContextUpdate?: (tokensUsed: number, maxTokens: number) => void;
  onSummarizing?: (status: 'start' | 'done') => void;
  onDone?: (messageId: string | null) => void;
  onError?: (error: string) => void;
}

export function useSSE(options: UseSSEOptions) {
  const [isStreaming, setIsStreaming] = useState(false);
  const abortControllerRef = useRef<AbortController | null>(null);

  /**
   * Send a message and stream the assistant response via SSE.
   * 
   * @param threadId - Target thread ID
   * @param messageId - Client-generated UUID for idempotency
   * @param content - Message content (should have {text: string})
   */
  const sendMessage = useCallback(
    async (threadId: string, messageId: string, content: Record<string, any>) => {
      // Abort any existing stream
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }

      // Create new AbortController for this request
      const abortController = new AbortController();
      abortControllerRef.current = abortController;

      setIsStreaming(true);

      try {
        // POST message with fetch to initiate SSE stream
        const res = await fetch(`/api/threads/${threadId}/messages`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            message_id: messageId,
            content,
            role: 'user',
          }),
          signal: abortController.signal, // Add abort signal
        });

        if (!res.ok) {
          const errorText = await res.text();
          throw new Error(`Failed to send message: ${res.status} ${errorText}`);
        }

        // Read SSE stream from response body
        const reader = res.body?.getReader();
        const decoder = new TextDecoder();

        if (!reader) {
          throw new Error('No response body');
        }

        // Process SSE stream
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value, { stream: true });
          const lines = chunk.split('\n');

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6); // Remove 'data: ' prefix
              try {
                const event: SSEEvent = JSON.parse(data);

                // Dispatch to handlers based on event type
                if (event.type === 'token') {
                  options.onToken?.(event.content);
                } else if (event.type === 'thinking') {
                  options.onThinking?.(event.content);
                } else if (event.type === 'tool_start') {
                  options.onToolStart?.(event.name, event.input);
                } else if (event.type === 'tool_end') {
                  options.onToolEnd?.(event.name, event.output, event.artifacts);
                } else if (event.type === 'title_updated') {
                  options.onTitleUpdated?.(event.title);
                } else if (event.type === 'context_update') {
                  options.onContextUpdate?.(event.tokens_used, event.max_tokens);
                } else if (event.type === 'summarizing') {
                  options.onSummarizing?.(event.status);
                } else if (event.type === 'done') {
                  options.onDone?.(event.message_id);
                  setIsStreaming(false);
                } else if (event.type === 'error') {
                  options.onError?.(event.error);
                  setIsStreaming(false);
                }
              } catch (parseErr) {
                console.warn('Failed to parse SSE event:', data, parseErr);
              }
            }
          }
        }
      } catch (err) {
        // Don't treat abort as an error
        if (err instanceof Error && err.name === 'AbortError') {
          console.log('Stream aborted by user');
        } else {
          options.onError?.(err instanceof Error ? err.message : 'Stream failed');
        }
        setIsStreaming(false);
      } finally {
        // Clean up abort controller reference
        if (abortControllerRef.current === abortController) {
          abortControllerRef.current = null;
        }
      }
    },
    [options]
  );

  return { sendMessage, isStreaming };
}

