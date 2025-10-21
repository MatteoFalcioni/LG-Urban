/**
 * ChatSidebar: Combined chat interface for the left sidebar.
 * Contains ThreadSelector, MessageList and MessageInput in a vertical layout.
 */

import { ThreadSelector } from './ThreadSelector';
import { MessageList } from './MessageList';
import { MessageInput } from './MessageInput';

interface ChatSidebarProps {
  onCollapse: () => void;
}

export function ChatSidebar({ onCollapse }: ChatSidebarProps) {
  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Thread selector - fixed at top */}
      <div className="flex-shrink-0">
        <ThreadSelector onCollapse={onCollapse} />
      </div>
      
      {/* Messages area - scrollable */}
      <div className="flex-1 overflow-hidden">
        <MessageList />
      </div>
      
      {/* Input area - fixed at bottom */}
      <div className="flex-shrink-0">
        <MessageInput />
      </div>
    </div>
  );
}

