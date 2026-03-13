## Setup

1. Navigate to the project directory:

```bash
cd AUTONOMOUS-ROVER--PRESET-PATH
```
2. Install system dependencies:
```bash
pip install -r sys-requirements.txt
```
3. Create a virtual environment:
```bash
python3 -m venv venv
```
4. Activate the virtual environment:
```bash
source venv/bin/activate
```
5. Install virtual enviroment dependencies:
```bash
pip install -r venv-requirements.txt
```
6. (Optional) Update the requirements file with installed packages:
```bash
pip freeze > requirements.txt
```

---

## How to Run 
1. Considerations:
- Make sure both pi and devices interfacing with the website are both on the same wi-fi connection 

2. Activate the virtual environment:
```bash
source venv/bin/activate
```
3. Run app file:
```bash
python -m app.app
```
4. ctrl+c to terminate program

---

## System Structure

### `app/`
Contains:
- Servo control logic  
- Website frontend  
- Website backend  

### `base/`
Contains:
- Autonomous rover movement  
- LiDAR Logic  
- AI model logic  