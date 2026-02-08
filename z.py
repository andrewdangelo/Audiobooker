from http.server import HTTPServer, BaseHTTPRequestHandler
import webbrowser
import threading

PORT = 7823

HTML = """
<!DOCTYPE html>
<html>
<head>
<title>Excel Viewer</title>
<script src="https://cdn.jsdelivr.net/npm/xlsx@0.18.5/dist/xlsx.full.min.js"></script>
<style>
body { font-family: Arial; padding: 40px; }
.drop {
  border: 3px dashed #999;
  padding: 40px;
  text-align: center;
  cursor: pointer;
}
.drop.drag { background: #eef; border-color: #007bff; }
table {
  border-collapse: collapse;
  margin-top: 20px;
}
th, td {
  border: 1px solid #ccc;
  padding: 6px 10px;
}
th { background: #eee; }
</style>
</head>
<body>

<h2>Drag & Drop Excel File</h2>
<div class="drop" id="drop">Drop Excel here or click</div>
<input type="file" id="file" hidden accept=".xlsx,.xls">

<div id="output"></div>

<script>
const drop = document.getElementById("drop");
const fileInput = document.getElementById("file");
const output = document.getElementById("output");

drop.onclick = () => fileInput.click();

drop.ondragover = e => { e.preventDefault(); drop.classList.add("drag"); };
drop.ondragleave = () => drop.classList.remove("drag");

drop.ondrop = e => {
  e.preventDefault();
  drop.classList.remove("drag");
  handleFile(e.dataTransfer.files[0]);
};

fileInput.onchange = () => handleFile(fileInput.files[0]);

function handleFile(file) {
  const reader = new FileReader();
  reader.onload = e => {
    const data = new Uint8Array(e.target.result);
    const workbook = XLSX.read(data, { type: "array" });

    const sheet = workbook.Sheets[workbook.SheetNames[0]];
    const rows = XLSX.utils.sheet_to_json(sheet, { header: 1 });

    renderTable(rows);
  };
  reader.readAsArrayBuffer(file);
}

function renderTable(rows) {
  let html = "<table>";
  rows.forEach((row, i) => {
    html += "<tr>";
    row.forEach(cell => {
      html += i === 0 ? `<th>${cell ?? ""}</th>` : `<td>${cell ?? ""}</td>`;
    });
    html += "</tr>";
  });
  html += "</table>";
  output.innerHTML = html;
}
</script>

</body>
</html>
"""

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(HTML.encode())

def open_browser():
    webbrowser.open(f"http://localhost:{PORT}")

if __name__ == "__main__":
    threading.Timer(1, open_browser).start()
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
