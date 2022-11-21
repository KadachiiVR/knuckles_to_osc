call venv/Scripts/activate.bat
cd src
python setup.py build -b ../build --build-exe ../build/Knuckles_to_OSC
cd ..