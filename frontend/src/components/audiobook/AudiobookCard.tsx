// TODO: Implement AudiobookCard component
// This component displays a single audiobook card

import { Card, CardHeader, CardTitle, CardContent } from '../ui/card'

interface AudiobookCardProps {
  title: string
  duration?: string
  createdAt: string
}

export default function AudiobookCard({ title, duration, createdAt }: AudiobookCardProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground">
          {duration && <span>Duration: {duration}</span>}
          <span className="block">Created: {createdAt}</span>
        </p>
      </CardContent>
    </Card>
  )
}
