import ChatInterface from '@/components/ChatInterface'

export default function ChatPage() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="container mx-auto max-w-4xl h-screen">
        <ChatInterface className="h-full" />
      </div>
    </div>
  )
}