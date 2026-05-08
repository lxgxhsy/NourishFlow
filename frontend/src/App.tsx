import { ChatView } from "@/components/ChatView"

export default function App() {
  return (
    <div className="h-screen flex flex-col">
      <header className="border-b px-4 py-3">
        <h1 className="text-lg font-semibold">NourishFlow</h1>
      </header>
      <main className="flex-1 overflow-hidden">
        <ChatView />
      </main>
    </div>
  )
}
