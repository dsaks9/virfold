"use client"

import { useState } from "react"

interface SensorProps {
  id: string
  x: number
  y: number
  color: string
  isActive: boolean
  onClick: () => void
}

const Sensor: React.FC<SensorProps> = ({ id, x, y, color, isActive, onClick }) => (
  <div
    className={`absolute w-4 h-4 rounded-full cursor-pointer transition-all duration-300 ${
      isActive ? "scale-150 ring-2 ring-white" : "scale-100"
    }`}
    style={{ left: `${x}%`, top: `${y}%`, backgroundColor: color }}
    onClick={onClick}
  >
    <span className="absolute top-5 left-1/2 transform -translate-x-1/2 text-xs font-bold text-white">{id}</span>
  </div>
)

const SensorMap: React.FC = () => {
  const [activeSensor, setActiveSensor] = useState<string | null>(null)

  const handleSensorClick = (sensorId: string) => {
    const newActiveSensor = activeSensor === sensorId ? null : sensorId
    setActiveSensor(newActiveSensor)

    // Dispatch custom event
    window.dispatchEvent(new CustomEvent("sensorClick", { detail: newActiveSensor }))
  }

  return (
    <div className="relative w-full aspect-square bg-gray-800 rounded-lg overflow-hidden">
      <svg
        viewBox="0 0 100 100"
        className="absolute inset-0 w-full h-full"
        style={{ filter: "drop-shadow(0px 0px 2px rgba(6, 182, 212, 0.5))" }}
      >
        {/* Warehouse outline */}
        <rect x="10" y="10" width="80" height="80" fill="none" stroke="rgb(6, 182, 212)" strokeWidth="0.5" />

        {/* Shelves */}
        {[20, 40, 60, 80].map((x) => (
          <line key={x} x1={x} y1="15" x2={x} y2="85" stroke="rgb(6, 182, 212)" strokeWidth="0.5" />
        ))}

        {/* Entrance */}
        <path
          d="M10,50 Q10,45 15,45 L25,45 Q30,45 30,50 L30,55 Q30,60 25,60 L15,60 Q10,60 10,55 Z"
          fill="none"
          stroke="rgb(236, 72, 153)"
          strokeWidth="0.5"
        />

        {/* Loading dock */}
        <rect x="70" y="85" width="20" height="5" fill="none" stroke="rgb(124, 58, 237)" strokeWidth="0.5" />
      </svg>

      {/* Sensors */}
      <Sensor
        id="1"
        x={25}
        y={30}
        color="rgb(6, 182, 212)"
        isActive={activeSensor === "sensor1"}
        onClick={() => handleSensorClick("sensor1")}
      />
      <Sensor
        id="2"
        x={65}
        y={70}
        color="rgb(236, 72, 153)"
        isActive={activeSensor === "sensor2"}
        onClick={() => handleSensorClick("sensor2")}
      />
      <Sensor
        id="3"
        x={85}
        y={20}
        color="rgb(124, 58, 237)"
        isActive={activeSensor === "sensor3"}
        onClick={() => handleSensorClick("sensor3")}
      />
    </div>
  )
}

export default SensorMap

