/**
 * ArtifactDisplay: Center area for displaying urban data artifacts.
 * Shows maps, charts, data tables, and other visualizations.
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import { ArrowDown } from 'lucide-react';
import { useChatStore } from '@/store/chatStore';
import { ArtifactGrid } from './ArtifactCard';

export function ArtifactDisplay() {
  const currentThreadId = useChatStore((state) => state.currentThreadId);
  const messages = useChatStore((state) => state.messages);
  const artifactBubbles = useChatStore((state) => state.artifactBubbles);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const [showScrollButton, setShowScrollButton] = useState(false);

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

  // Check if user is near bottom (to show/hide scroll button)
  const handleScroll = useCallback(() => {
    if (!scrollContainerRef.current) return;
    
    const { scrollTop, scrollHeight, clientHeight } = scrollContainerRef.current;
    const distanceFromBottom = scrollHeight - scrollTop - clientHeight;
    
    // Show button if more than 100px from bottom
    setShowScrollButton(distanceFromBottom > 100);
  }, []);

  // Scroll to bottom function
  const scrollToBottom = useCallback(() => {
    if (!scrollContainerRef.current) return;
    scrollContainerRef.current.scrollTo({
      top: scrollContainerRef.current.scrollHeight,
      behavior: 'smooth'
    });
  }, []);

  // Auto-scroll when new artifacts arrive
  useEffect(() => {
    if (scrollContainerRef.current && artifacts.length > 0) {
      scrollContainerRef.current.scrollTo({
        top: scrollContainerRef.current.scrollHeight,
        behavior: 'smooth'
      });
    }
  }, [artifacts.length]); // Only when number of artifacts changes

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
    <div className="relative h-full w-full">
      <div 
        ref={scrollContainerRef} 
        onScroll={handleScroll}
        className="h-full w-full overflow-auto"
      >
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

      {/* Scroll to bottom button */}
      {showScrollButton && (
        <button
          onClick={scrollToBottom}
          className="absolute bottom-6 right-6 p-3 bg-white/90 dark:bg-slate-800/90 backdrop-blur-sm border border-gray-200/50 dark:border-slate-700/50 rounded-full shadow-lg hover:shadow-xl hover:bg-white dark:hover:bg-slate-800 transition-all duration-300 ease-out flex items-center justify-center group hover:scale-110 active:scale-95 z-10"
          title="Scroll to bottom"
        >
          <ArrowDown size={18} className="text-gray-600 dark:text-slate-300 group-hover:text-gray-800 dark:group-hover:text-slate-100 transition-colors duration-200" />
        </button>
      )}
    </div>
  );
}





