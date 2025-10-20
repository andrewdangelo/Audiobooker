// TODO: Implement Dashboard page
// This page shows overview statistics and recent activity

export default function Dashboard() {
  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-8">Dashboard</h1>
      
      <div className="grid md:grid-cols-3 gap-6 mb-8">
        <div className="p-6 border rounded-lg">
          <h3 className="text-sm text-muted-foreground mb-2">Total Audiobooks</h3>
          <p className="text-3xl font-bold">0</p>
        </div>
        <div className="p-6 border rounded-lg">
          <h3 className="text-sm text-muted-foreground mb-2">Processing</h3>
          <p className="text-3xl font-bold">0</p>
        </div>
        <div className="p-6 border rounded-lg">
          <h3 className="text-sm text-muted-foreground mb-2">Total Duration</h3>
          <p className="text-3xl font-bold">0h</p>
        </div>
      </div>

      <div className="border rounded-lg p-6">
        <h2 className="text-xl font-semibold mb-4">Recent Activity</h2>
        <p className="text-muted-foreground">No recent activity</p>
      </div>
    </div>
  )
}
