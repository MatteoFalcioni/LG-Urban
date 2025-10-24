# UI Refactor Plan: Data-Centered Urban Analytics Interface

## Overview
Transform the interface from a classic chatbot to a data-centered urban analytics tool with chat on the left, artifacts in center, and enhanced configuration with API key management.

---

## 1. Layout Restructure: Chat to Left Sidebar ✅ COMPLETED

**Goal**: Move the entire chat interface (MessageList + MessageInput) to where ThreadSidebar currently is, making it collapsible.

### Implementation
- ✅ Created `ChatSidebar.tsx` - Combined chat interface component
- ✅ Updated `App.tsx` - Swapped sidebar content from ThreadSidebar to ChatSidebar
- ✅ Maintained collapsible/resizable functionality
- ✅ Center area prepared for artifact display

---

## 2. Context Indicator in Message Input ✅ COMPLETED

**Goal**: Move the context circle from the header into the MessageInput bubble (bottom-right corner).

### Implementation
- ✅ Updated `MessageInput.tsx` - Added context indicator in bottom-right corner of textarea
- ✅ Positioned absolutely inside input bubble with proper spacing
- ✅ Removed context indicator from App header
- ✅ Simplified header design

---

## 3. Center Artifact Display ✅ COMPLETED

**Goal**: Show artifacts (maps, charts, data tables) in the center of the screen instead of inline with messages.

### Implementation
- ✅ Created `ArtifactDisplay.tsx` - Dedicated artifact visualization component
- ✅ Updated `MessageList.tsx` - Stripped artifact rendering, text-only messages
- ✅ Updated `App.tsx` - Routed artifacts to center display
- ✅ Implemented empty states with helpful urban data prompts

---

## 4. Thread Selection UI ✅ COMPLETED

**Selected Option**: **Option B - Top Bar with Thread Selector**

### Implementation
- ✅ Created `ThreadSelector.tsx` - Top bar component
- ✅ Thread dropdown with current thread title display
- ✅ Integrated theme toggle and new thread button
- ✅ Smooth dropdown panel with thread list
- ✅ Modern styling with hover effects

---

## 5. API Key Management ✅ COMPLETED

**Goal**: Allow users to input their OpenAI and Anthropic API keys, stored securely on backend per user.

### Backend Implementation
- ✅ Added `UserAPIKeys` table in `backend/db/models.py`
- ✅ Created encryption utilities in `backend/utils/encryption.py` using Fernet
- ✅ Added API endpoints: GET/POST `/api/users/{user_id}/api-keys`
- ✅ Created database migration for UserAPIKeys table
- ✅ Integrated user API keys into LLM invocation in `backend/graph/graph.py`
- ✅ Fixed: API keys wrapped in `SecretStr` for LangChain compatibility

### Frontend Implementation
- ✅ Enhanced `ConfigPanel.tsx` with API Keys section
- ✅ Added password inputs with show/hide toggle
- ✅ Integrated with backend API for key storage/retrieval
- ✅ Updated `chatStore.ts` with API keys state management
- ✅ Added `getUserApiKeys()` and `saveUserApiKeys()` in `api.ts`

### Security Features
- ✅ Keys encrypted at rest using Fernet symmetric encryption
- ✅ Keys masked in UI (e.g., "sk-...abc123")
- ✅ Secure transmission and storage
- ✅ Per-user key isolation

---

## 6. LLM Integration with User API Keys ✅ COMPLETED

**Goal**: Use user-provided API keys when available, fallback to environment variables.

### Implementation
- ✅ Modified `make_graph()` to accept `user_api_keys` parameter
- ✅ Implemented key priority logic:
  - **First**: Use user-provided keys if available
  - **Fallback**: Use environment variables
- ✅ Updated both `/threads/{thread_id}/state` and `/threads/{thread_id}/messages` endpoints
- ✅ Created `get_user_api_keys_for_llm()` helper function
- ✅ Fixed: Wrapped API keys in `SecretStr` for LangChain

---

## 7. Modern Styling & Polish ✅ COMPLETED

**Goal**: Update aesthetics to match modern chat interfaces (Claude, ChatGPT, Cursor style).

### Implementation
- ✅ Enhanced `index.css` with modern color palette and CSS variables
- ✅ Added shadows, gradients, and smooth transitions
- ✅ Updated chat bubbles with rounded corners and better contrast
- ✅ Enhanced input area with modern styling
- ✅ Improved button hover states and interactions
- ✅ Better typography and spacing throughout
- ✅ Gradient backgrounds for avatars
- ✅ Modern card-based design language

---

## Final Status: ✅ ALL PHASES COMPLETED

### What Was Accomplished:

1. **Data-Centered Layout** - Chat moved to left sidebar, artifacts take center stage
2. **Modern Thread Management** - Clean dropdown interface with theme controls
3. **Secure API Key Storage** - Encrypted backend storage with user-friendly frontend
4. **LLM Integration** - User keys automatically used when available
5. **Enhanced Visual Design** - Modern styling with gradients, shadows, and smooth animations
6. **Improved User Experience** - Better spacing, typography, and interaction feedback

### Key Benefits:

- **Urban Data Focus**: Visualizations are now the primary interface element
- **Cost Control**: Users can use their own API keys
- **Security**: Encrypted key storage with proper LangChain integration
- **Flexibility**: Graceful fallback to system keys
- **Modern UX**: Contemporary design matching latest chat interfaces

---

## Technical Implementation Details

### Frontend Components Created/Modified:
- `ChatSidebar.tsx` (new)
- `ThreadSelector.tsx` (new)
- `ArtifactDisplay.tsx` (new)
- `App.tsx` (modified)
- `MessageInput.tsx` (modified)
- `MessageList.tsx` (modified)
- `ConfigPanel.tsx` (modified)
- `chatStore.ts` (modified)
- `api.ts` (modified)
- `index.css` (enhanced)

### Backend Components Created/Modified:
- `models.py` - Added `UserAPIKeys` table
- `api.py` - Added key management endpoints and helper functions
- `graph.py` - Integrated user API keys into LLM initialization
- `encryption.py` (new) - Encryption utilities
- Database migration for `UserAPIKeys`

### Security Measures:
- Fernet symmetric encryption for API keys
- `SecretStr` wrapping for LangChain compatibility
- Masked key display in UI
- Per-user key isolation
- Secure transmission

---

## Future Enhancements (Optional)

- Support for additional LLM providers
- Key rotation and expiration features
- Usage tracking per user API key
- Multiple artifact view modes (grid/list/fullscreen)
- Thread organization features (folders, tags)
- Export capabilities for visualizations

---

**Status**: Ready for production deployment ✅
