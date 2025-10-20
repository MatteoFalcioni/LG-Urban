/**
 * ChatSidebar: Combined chat interface for the left sidebar.
 * Contains ThreadSelector, MessageList and MessageInput in a vertical layout.
 */

import { ThreadSelector } from './ThreadSelector';
import { MessageList } from './MessageList';
import { MessageInput } from './MessageInput';

export function ChatSidebar() {
  return (
    <div className="flex flex-col h-full">
      {/* Thread selector - fixed at top */}
      <ThreadSelector />
      
      {/* Messages area - scrollable */}
      <div className="flex-1 overflow-hidden">
        <MessageList />
      </div>
      
      {/* Input area - fixed at bottom */}
      <MessageInput />
    </div>
  );
}

