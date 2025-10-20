// TODO: Implement Upload page
// This page handles PDF file uploads

import FileUpload from '../components/upload/FileUpload'

export default function Upload() {
  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-8">Upload PDF</h1>
      
      <div className="max-w-2xl mx-auto">
        <FileUpload />
        
        <div className="mt-8 p-4 bg-muted rounded-lg">
          <h3 className="font-semibold mb-2">Supported Files</h3>
          <ul className="text-sm text-muted-foreground list-disc list-inside">
            <li>PDF documents (.pdf)</li>
            <li>Maximum file size: 50MB</li>
            <li>Text-based PDFs recommended</li>
          </ul>
        </div>
      </div>
    </div>
  )
}
