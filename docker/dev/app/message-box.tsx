"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { ScrollArea } from "@/components/ui/scroll-area"

// Hardcoded message history
const initialMessages = [
  { id: 1, text: "Welcome to the Sensor Dashboard! How can I assist you today?", sender: "bot" },
  { id: 2, text: "What's the current temperature in the warehouse?", sender: "user" },
  { id: 3, text: "The current average temperature across all sensors is 24.5°C.", sender: "bot" },
  { id: 4, text: "Are there any unusual humidity readings?", sender: "user" },
  {
    id: 5,
    text: "Sensor 2 is reporting slightly elevated humidity levels. Current reading is 68%, which is 10% above the average.",
    sender: "bot",
  },
]

export default function MessageBox() {
  const [messages, setMessages] = useState(initialMessages)
  const [input, setInput] = useState("")

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (input.trim()) {
      // Add user message
      setMessages((prev) => [...prev, { id: prev.length + 1, text: input, sender: "user" }])
      setInput("")

      // TODO: Implement API call here
      // For now, we'll just add a dummy response
      setTimeout(() => {
        setMessages((prev) => [
          ...prev,
          {
            id: prev.length + 1,
            text: "I've received your message. Once connected to an AI, I'll provide a relevant response.",
            sender: "bot",
          },
        ])
      }, 500)
    }
  }

  return (
    <div className="flex flex-col h-full">
      <ScrollArea className="flex-grow mb-4">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`mb-2 p-2 rounded-lg ${
              message.sender === "user" ? "bg-blue-500 text-white ml-auto" : "bg-gray-700 text-cyan-400"
            } max-w-[80%]`}
          >
            {message.text}
          </div>
        ))}
      </ScrollArea>
      <form onSubmit={handleSubmit} className="flex gap-2">
        <Input
          type="text"
          placeholder="Type your query here..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          className="flex-grow bg-gray-800 text-white border-gray-700 focus:border-cyan-400"
        />
        <Button type="submit" className="bg-cyan-500 text-white hover:bg-cyan-600">
          Send
        </Button>
      </form>
    </div>
  )
}

