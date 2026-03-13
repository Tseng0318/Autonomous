## Setup

1. Navigate to the project directory:

```bash
cd AUTONOMOUS-ROVER--PRESET-PATH
```
2. Create a virtual environment:
```bash
python3 -m venv venv
```
3. Activate the virtual environment:
```bash
source venv/bin/activate
```
4. Install dependencies:
```bash
pip install -r requirements.txt
```
5. (Optional) Update the requirements file with installed packages:
```bash
pip freeze > requirements.txt
```

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