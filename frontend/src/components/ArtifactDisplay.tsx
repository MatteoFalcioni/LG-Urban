/**
 * ArtifactDisplay: Center area for displaying urban data artifacts.
 * Shows maps, charts, data tables, and other visualizations.
 */

import { useEffect, useRef } from 'react';
import { useChatStore } from '@/store/chatStore';
import { ArtifactGrid } from './ArtifactCard';

export function ArtifactDisplay() {
  const currentThreadId = useChatStore((state) => state.currentThreadId);
  const messages = useChatStore((state) => state.messages);
  const artifactBubbles = useChatStore((state) => state.artifactBubbles);
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  // Get all artifacts from current thread
  const getCurrentThreadArtifacts = () => {
    if (!currentThreadId) return [];

    // Get artifacts from messages
    const messageArtifacts = messages
      .filter(msg => msg.thread_id === currentThreadId && msg.artifacts)
      .flatMap(msg => msg.artifacts || []);

    // Get artifacts from streaming bubbles
    const streamingArtifacts = artifactBubbles
      .filter(bubble => bubble.threadId === currentThreadId)
      .flatMap(bubble => bubble.artifacts);

    // Combine and deduplicate by artifact ID
    const allArtifacts = [...messageArtifacts, ...streamingArtifacts];
    const uniqueArtifacts = allArtifacts.filter((artifact, index, self) => 
      index === self.findIndex(a => a.id === artifact.id)
    );

    return uniqueArtifacts;
  };

  const artifacts = getCurrentThreadArtifacts();

  // Auto-scroll to bottom when artifacts change
  useEffect(() => {
    if (scrollContainerRef.current && artifacts.length > 0) {
      scrollContainerRef.current.scrollTo({
        top: scrollContainerRef.current.scrollHeight,
        behavior: 'smooth'
      });
    }
  }, [artifacts]);

  if (!currentThreadId) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500 dark:text-slate-400">
        <div className="text-center">
          <h2 className="text-xl font-semibold mb-2">Urban Data Analytics</h2>
          <p>Select a thread or create a new one to start analyzing urban data</p>
        </div>
      </div>
    );
  }

  if (artifacts.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500 dark:text-slate-400">
        <div className="text-center">
          <h2 className="text-xl font-semibold mb-2">Urban Data Analytics</h2>
          <p>Send a message to generate visualizations and data insights</p>
          <div className="mt-4 text-sm text-gray-400 dark:text-slate-500">
            <p>Try asking about:</p>
            <ul className="mt-2 space-y-1">
              <li>• Population density in specific areas</li>
              <li>• Traffic patterns and congestion</li>
              <li>• Environmental data and air quality</li>
              <li>• Urban planning metrics</li>
            </ul>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div ref={scrollContainerRef} className="h-full overflow-auto">
      <div className="p-6">
        <div className="mb-4">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-slate-100">
            Data Visualizations
          </h2>
          <p className="text-sm text-gray-600 dark:text-slate-400">
            {artifacts.length} visualization{artifacts.length !== 1 ? 's' : ''} generated
          </p>
        </div>
        
        <ArtifactGrid artifacts={artifacts} />
      </div>
    </div>
  );
}





