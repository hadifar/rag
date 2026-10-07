// The chat feature's public API: import it from '@/features/chat', never a file inside.
// Only the lazily loaded ChatPage and SharedChatPage may import it: it pulls in the
// markdown renderer.
export { Composer } from './components/Composer';
export { MessageList } from './components/MessageList';
export { WelcomePlaceholder } from './components/WelcomePlaceholder';
export { useChat } from './hooks/useChat';
export { SharedChatView } from './components/SharedChatView';
export { useSharedChat } from './hooks/useSharedChat';
