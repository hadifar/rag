import { useParams } from 'react-router-dom';
import { Composer, MessageList, WelcomePlaceholder, useChat } from '@/features/chat';
import { useOpenKbSource } from '@/features/knowledge-base';
import { SKILL_ACCEPT, useSkillUpload } from '@/features/skills';

export function ChatPage() {
  const { conversationId } = useParams();
  const { bubbles, isWaiting, showWelcome, sendMessage, attachments, retryBubbleId, retry } =
    useChat(conversationId);
  const openSource = useOpenKbSource();
  const skillUpload = useSkillUpload();

  return (
    <div className="flex h-full flex-col">
      {showWelcome ? (
        <WelcomePlaceholder />
      ) : (
        <MessageList
          bubbles={bubbles}
          isWaiting={isWaiting}
          conversationId={conversationId}
          onOpenSource={openSource}
          retryBubbleId={retryBubbleId}
          onRetry={retry}
        />
      )}
      <Composer
        onSend={sendMessage}
        attachments={attachments}
        skills={{
          accept: SKILL_ACCEPT,
          onUpload: skillUpload.upload,
          uploading: skillUpload.uploading,
          notice: skillUpload.notice,
        }}
      />
    </div>
  );
}
