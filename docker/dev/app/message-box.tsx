"use client"

import React, { useState, useEffect, FormEvent, ChangeEvent } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { ScrollArea } from "@/components/ui/scroll-area"

interface Message {
  id: number
  text: string
  sender: "user" | "bot"
}

interface ChatResponse {
  session_id: string
  response: string
}

export default function MessageBox() {
  const [messages, setMessages] = useState<Message[]>([
    { id: 1, text: "Welcome to the Sensor Dashboard! How can I assist you today?", sender: "bot" }
  ])
  const [input, setInput] = useState("")
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  // Load session ID from localStorage on mount
  useEffect(() => {
    const savedSessionId = localStorage.getItem('chatSessionId')
    if (savedSessionId) {
      setSessionId(savedSessionId)
    }
  }, [])

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    if (input.trim() && !isLoading) {
      setIsLoading(true)
      
      // Add user message immediately
      const userMessage: Message = {
        id: messages.length + 1,
        text: input.trim(),
        sender: "user"
      }
      setMessages((prev: Message[]) => [...prev, userMessage])
      setInput("")

      try {
        // Send message to API
        const response = await fetch(`${process.env.NEXT_PUBLIC_DATA_ANALYST_API_URL}/data-analyst/chat`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            message: userMessage.text,
            session_id: sessionId
          })
        })

        if (!response.ok) {
          throw new Error('Failed to get response from API')
        }

        const data: ChatResponse = await response.json()
        
        // Save session ID if it's new
        if (!sessionId) {
          setSessionId(data.session_id)
          localStorage.setItem('chatSessionId', data.session_id)
        }

        // Add bot response
        setMessages((prev: Message[]) => [...prev, {
          id: prev.length + 1,
          text: data.response,
          sender: "bot"
        }])
      } catch (error) {
        console.error('Error sending message:', error)
        // Add error message
        setMessages((prev: Message[]) => [...prev, {
          id: prev.length + 1,
          text: "Sorry, I encountered an error processing your request. Please try again.",
          sender: "bot"
        }])
      } finally {
        setIsLoading(false)
      }
    }
  }

  return (
    <div className="flex flex-col h-full">
      <ScrollArea className="flex-grow mb-4">
        {messages.map((message: Message) => (
          <div
            key={message.id}
            className={`mb-2 p-2 rounded-lg ${
              message.sender === "user" ? "bg-blue-500 text-white ml-auto" : "bg-gray-700 text-cyan-400"
            } max-w-[80%]`}
          >
            {message.text}
          </div>
        ))}
        {isLoading && (
          <div className="mb-2 p-2 rounded-lg bg-gray-700 text-cyan-400 max-w-[80%]">
            Thinking...
          </div>
        )}
      </ScrollArea>
      <form onSubmit={handleSubmit} className="flex gap-2">
        <Input
          type="text"
          placeholder="Type your query here..."
          value={input}
          onChange={(e: ChangeEvent<HTMLInputElement>) => setInput(e.target.value)}
          disabled={isLoading}
          className="flex-grow bg-gray-800 text-white border-gray-700 focus:border-cyan-400"
        />
        <Button 
          type="submit" 
          disabled={isLoading}
          className={`${
            isLoading 
              ? 'bg-gray-600 cursor-not-allowed' 
              : 'bg-cyan-500 hover:bg-cyan-600'
          } text-white`}
        >
          Send
        </Button>
      </form>
    </div>
  )
}

