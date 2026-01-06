import subprocess

# Paths
venv_python = r"c:\Users\Moesa\Documents\Audiobooker\backend\venv\Scripts\python.exe"
backend_path = r"c:\Users\Moesa\Documents\Audiobooker\backend\main.py"
frontend_path = r"c:\Users\Moesa\Documents\Audiobooker\frontend"

# & "C:\Program Files\PostgreSQL\17\bin\psql.exe" --version
# & "C:\Program Files\PostgreSQL\17\bin\psql.exe" -U postgres -h localhost
# & "C:\Program Files\PostgreSQL\17\bin\psql.exe" -U audiobooker -h localhost -d audiobooker_db
# delete logs folder in git bash with find . -type d -name "logs" -not -path "./venv/*" -exec rm -rf {} +

def run_app():
    # Run backend
    # subprocess.Popen([venv_python, backend_path])

    # Run frontend (npm run dev)
    subprocess.Popen(["npm", "run", "dev"], cwd=frontend_path, shell=True)


if __name__ == "__main__":
    run_app()

