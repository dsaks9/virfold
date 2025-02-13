"use client"

import { useEffect, useState } from "react"
import Chart from "chart.js/auto"

interface SensorData {
  time: string
  temperature: number
  humidity: number
}

interface SensorDataMap {
  [key: string]: SensorData[]
}

const sensorColors = {
  sensor1: "rgb(6, 182, 212)",
  sensor2: "rgb(236, 72, 153)",
  sensor3: "rgb(124, 58, 237)",
}

const charts: { [key: string]: Chart } = {}

const API_URL = process.env.NEXT_PUBLIC_TS_API_URL

async function fetchSensorData(): Promise<SensorDataMap> {
  if (!API_URL) {
    throw new Error('API URL is not configured')
  }

  try {
    console.log('Fetching sensor data from:', `${API_URL}/sensors/data?interval=5%20minutes`)
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 10000) // 10 second timeout

    const response = await fetch(`${API_URL}/sensors/data?interval=5%20minutes`, {
      headers: {
        'Accept': 'application/json',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache'
      },
      signal: controller.signal,
      mode: 'cors',
    })
    
    clearTimeout(timeoutId)
    
    if (!response.ok) {
      const errorText = await response.text()
      console.error('API Error:', errorText)
      throw new Error(`Failed to fetch sensor data: ${response.statusText}. ${errorText}`)
    }
    
    const data = await response.json()
    console.log('Received sensor data:', data)
    
    if (!data || Object.keys(data).length === 0) {
      throw new Error('No sensor data returned from API')
    }
    
    return data
  } catch (error) {
    if (error instanceof Error) {
      if (error.name === 'AbortError') {
        throw new Error('Request timed out after 10 seconds')
      }
      console.error('Error fetching sensor data:', error)
      throw error
    }
    throw new Error('An unknown error occurred')
  }
}

export function initializeCharts(sensorData: SensorDataMap, activeSensor: string | null) {
  console.log('Initializing charts with data:', sensorData)
  if (!sensorData || Object.keys(sensorData).length === 0) {
    console.log('No sensor data available')
    return
  }

  // Temperature Chart
  const ctx1 = document.getElementById("chart1") as HTMLCanvasElement
  if (!ctx1) {
    console.log('Temperature chart canvas not found')
    return
  }

  if (charts.temperatureChart) charts.temperatureChart.destroy()
  charts.temperatureChart = new Chart(ctx1, {
    type: "line",
    data: {
      labels: Object.values(sensorData)[0]?.map(d => d.time) || [],
      datasets: Object.entries(sensorData)
        .filter(([key]) => !activeSensor || key === activeSensor)
        .map(([key, data]) => ({
          label: `${key} Temperature`,
          data: data.map((d) => d.temperature),
          borderColor: sensorColors[key as keyof typeof sensorColors],
          backgroundColor: `${sensorColors[key as keyof typeof sensorColors]}20`,
          tension: 0.4,
          fill: true,
        })),
    },
    options: {
      responsive: true,
      scales: {
        x: {
          grid: { color: "rgba(6, 182, 212, 0.1)" },
          ticks: { color: "rgb(6, 182, 212)" },
        },
        y: {
          grid: { color: "rgba(6, 182, 212, 0.1)" },
          ticks: { color: "rgb(6, 182, 212)" },
          title: {
            display: true,
            text: "Temperature (°C)",
            color: "rgb(6, 182, 212)",
          },
        },
      },
      plugins: {
        title: {
          display: true,
          text: "Temperature Over Time",
          color: "rgb(6, 182, 212)",
          font: { size: 16 },
        },
        legend: {
          labels: { color: "rgb(6, 182, 212)" },
        },
      },
    },
  })

  // Humidity Chart
  const ctx2 = document.getElementById("chart2") as HTMLCanvasElement
  if (!ctx2) return

  if (charts.humidityChart) charts.humidityChart.destroy()
  charts.humidityChart = new Chart(ctx2, {
    type: "line",
    data: {
      labels: Object.values(sensorData)[0]?.map(d => d.time) || [],
      datasets: Object.entries(sensorData)
        .filter(([key]) => !activeSensor || key === activeSensor)
        .map(([key, data]) => ({
          label: `${key} Humidity`,
          data: data.map((d) => d.humidity),
          borderColor: sensorColors[key as keyof typeof sensorColors],
          backgroundColor: `${sensorColors[key as keyof typeof sensorColors]}20`,
          tension: 0.4,
          fill: true,
        })),
    },
    options: {
      responsive: true,
      scales: {
        x: {
          grid: { color: "rgba(236, 72, 153, 0.1)" },
          ticks: { color: "rgb(236, 72, 153)" },
        },
        y: {
          grid: { color: "rgba(236, 72, 153, 0.1)" },
          ticks: { color: "rgb(236, 72, 153)" },
          title: {
            display: true,
            text: "Humidity (%)",
            color: "rgb(236, 72, 153)",
          },
        },
      },
      plugins: {
        title: {
          display: true,
          text: "Humidity Over Time",
          color: "rgb(236, 72, 153)",
          font: { size: 16 },
        },
        legend: {
          labels: { color: "rgb(236, 72, 153)" },
        },
      },
    },
  })

  // Bar Chart - Average Values
  const ctxBar = document.getElementById("barChart") as HTMLCanvasElement
  if (!ctxBar) return

  if (charts.barChart) charts.barChart.destroy()
  charts.barChart = new Chart(ctxBar, {
    type: "bar",
    data: {
      labels: Object.keys(sensorData).filter(key => !activeSensor || key === activeSensor),
      datasets: [
        {
          label: "Average Temperature (°C)",
          data: Object.entries(sensorData)
            .filter(([key]) => !activeSensor || key === activeSensor)
            .map(([_, data]) => 
              data.reduce((acc, curr) => acc + curr.temperature, 0) / data.length
            ),
          backgroundColor: "rgba(6, 182, 212, 0.5)",
          borderColor: "rgb(6, 182, 212)",
          borderWidth: 1,
        },
        {
          label: "Average Humidity (%)",
          data: Object.entries(sensorData)
            .filter(([key]) => !activeSensor || key === activeSensor)
            .map(([_, data]) => 
              data.reduce((acc, curr) => acc + curr.humidity, 0) / data.length
            ),
          backgroundColor: "rgba(236, 72, 153, 0.5)",
          borderColor: "rgb(236, 72, 153)",
          borderWidth: 1,
        },
      ],
    },
    options: {
      responsive: true,
      scales: {
        x: {
          grid: { color: "rgba(6, 182, 212, 0.1)" },
          ticks: { color: "rgb(6, 182, 212)" },
        },
        y: {
          grid: { color: "rgba(6, 182, 212, 0.1)" },
          ticks: { color: "rgb(6, 182, 212)" },
        },
      },
      plugins: {
        title: {
          display: true,
          text: "Average Sensor Readings",
          color: "rgb(6, 182, 212)",
          font: { size: 16 },
        },
        legend: {
          labels: { color: "rgb(6, 182, 212)" },
        },
      },
    },
  })
}

export default function DashboardCharts() {
  const [activeSensor, setActiveSensor] = useState<string | null>(null)
  const [sensorData, setSensorData] = useState<SensorDataMap>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true)
        setError(null)
        const data = await fetchSensorData()
        if (Object.keys(data).length === 0) {
          setError('No sensor data available')
        }
        setSensorData(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch sensor data')
      } finally {
        setLoading(false)
      }
    }

    // Fetch initial data
    fetchData()

    // Set up polling every minute
    const interval = setInterval(fetchData, 60000)

    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    const handleSensorClick = (event: CustomEvent) => {
      setActiveSensor(event.detail)
    }

    window.addEventListener("sensorClick" as any, handleSensorClick)

    return () => {
      window.removeEventListener("sensorClick" as any, handleSensorClick)
    }
  }, [])

  useEffect(() => {
    if (Object.keys(sensorData).length > 0) {
      initializeCharts(sensorData, activeSensor)
    }
  }, [sensorData, activeSensor])

  if (loading) {
    return <div className="text-cyan-400">Loading sensor data...</div>
  }

  if (error) {
    return <div className="text-red-400">Error: {error}</div>
  }

  if (Object.keys(sensorData).length === 0) {
    return <div className="text-yellow-400">No sensor data available</div>
  }

  return null
}

