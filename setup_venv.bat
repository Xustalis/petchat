@echo off
echo Creating virtual environment...
python -m venv venv

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Installing dependencies...
pip install --upgrade pip
pip install -r requirements.txt

echo.
echo Virtual environment setup complete!
echo.
echo To activate the virtual environment, run:
echo   venv\Scripts\activate.bat
echo.
echo To deactivate, run:
echo   deactivate
pause

