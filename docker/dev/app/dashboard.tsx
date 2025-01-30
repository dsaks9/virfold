import { Card } from "@/components/ui/card"
import SensorMap from "./sensor-map"
import MessageBox from "./message-box"
import DashboardCharts from "./dashboard-charts"

export default function Dashboard() {
  return (
    <>
      <DashboardCharts />
      <div className="min-h-screen bg-gray-950 p-6 text-cyan-400">
        <div className="grid gap-6">
          {/* Main Charts Section */}
          <div className="grid gap-6 lg:grid-cols-2">
            <Card className="p-4 bg-gray-900/50 border-gray-800">
              <canvas
                id="chart1"
                className="w-full aspect-[2/1]"
                style={{
                  background: "linear-gradient(to bottom, rgba(6, 182, 212, 0.1), transparent)",
                }}
              />
            </Card>
            <Card className="p-4 bg-gray-900/50 border-gray-800">
              <canvas
                id="chart2"
                className="w-full aspect-[2/1]"
                style={{
                  background: "linear-gradient(to bottom, rgba(236, 72, 153, 0.1), transparent)",
                }}
              />
            </Card>
          </div>

          {/* Average Values Chart */}
          <Card className="p-4 bg-gray-900/50 border-gray-800">
            <canvas
              id="barChart"
              className="w-full aspect-[3/1]"
              style={{
                background: "linear-gradient(to bottom, rgba(6, 182, 212, 0.05), transparent)",
              }}
            />
          </Card>

          {/* Bottom Section */}
          <div className="grid gap-6 lg:grid-cols-2">
            {/* Sensor Map */}
            <Card className="p-4 bg-gray-900/50 border-gray-800">
              <SensorMap />
            </Card>

            {/* Message Box */}
            <Card className="p-4 bg-gray-900/50 border-gray-800">
              <MessageBox />
            </Card>
          </div>
        </div>
      </div>
    </>
  )
}

