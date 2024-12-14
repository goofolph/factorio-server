IF not exist "venv" (
    py -m venv "venv"
)

call ".\venv\Scripts\activate.bat"
pip install -U -r requirements.txt
