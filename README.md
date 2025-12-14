# CPU Scheduling Simulator

A desktop application for visualizing and comparing classic CPU scheduling algorithms.  
Built with **Python**, **Tkinter/customtkinter**, and a modern dark UI.

---

## Features

### Implemented Scheduling Algorithms

Both non-preemptive and preemptive algorithms are supported:

- **First-Come, First-Served (FCFS)** – non-preemptive  
- **Shortest Job First (SJF)** – non-preemptive  
- **Shortest Remaining Time First (SRTF)** – preemptive SJF  
- **Priority Scheduling** – non-preemptive (lower numeric value = higher priority)  
- **Priority Scheduling (Preemptive)**  
- **Round Robin (RR)** – preemptive, with configurable time quantum  

For every run, the simulator computes for each process:

- Completion Time  
- Turnaround Time  
- Waiting Time  

And aggregates:

- **Average Waiting Time**
- **Average Turnaround Time**
- **CPU Utilization**
- **Throughput (processes per unit time)**
- **Minimum / Maximum Waiting Time**

---

## GUI Overview

The main window is divided into three sections:

### 1. Process Input

- Add processes with:
  - **Arrival Time (ms)**
  - **Burst Time (ms)**
  - **Priority** (lower = higher priority)
- Processes are listed in a **dark-themed table** (`PID, Arrival, Burst, Priority`) with:
  - Striped rows
  - Centered values
  - Scrollbar for long lists
- **Remove Selected** deletes the highlighted process row.
- PIDs are auto-assigned as `P1`, `P2`, `P3`, ...

### 2. Algorithm Selection & Controls

- **Scheduling Algorithm** dropdown:
  - Choose any of the implemented algorithms.
- **Time Quantum** input:
  - Only enabled when **Round Robin (RR)** is selected.
- **Run Simulation** button:
  - Executes the selected algorithm on the current process set.
  - Updates the Gantt chart, metrics table, and aggregate metrics.
- **Clear All** button:
  - Clears processes, metrics, chart, and resets counters/state.

#### Example Scenarios

A dedicated **“Example Scenario”** dropdown provides ready-made datasets:

- **Simple FCFS demo** – basic example to illustrate FCFS behavior.
- **Starvation example (Priority)** – shows starvation in non-preemptive priority scheduling.
- **Preemptive vs Non-preemptive SJF** – good for comparing SJF and SRTF.

Selecting a scenario:

- Clears the current data,
- Auto-fills the Process Input table with a predefined set of processes.

#### Aggregate Metrics Display

Under the Run/ Clear buttons, the simulator displays:

- **Average Waiting Time**
- **Average Turnaround Time**
- **CPU Utilization** (busy time / total time)
- **Throughput** (number of processes / total time)
- **Minimum & Maximum Waiting Time**

These metrics update after each simulation.

### 3. Gantt Chart & Process Metrics

#### Gantt Chart

- Visualizes the schedule on a dark background:
  - Each process is a colored bar segment.
  - Idle CPU intervals are shown in grey.
- Time ticks and labels along the bottom show the exact timing.

**Cross-highlighting:**

- Clicking a process row in the **Process Input** table:
  - Selects the corresponding row in the **Process Metrics** table.
  - Highlights that process’s segments in the Gantt chart with a **thicker golden outline**.
- This makes it easy to follow one process from input → schedule → metrics.

#### Process Metrics Table

- A second dark-themed `ttk.Treeview` showing, per process:

  `PID, Arrival, Burst, Priority, Completion, Turnaround, Waiting`

- Rows are **sorted by PID** for stable, predictable ordering.
- Striped rows and centered text match the Process Input table.

---

## Installation

1. **Clone the repository** (or download the project folder):

```bash
git clone <your-repo-url>.git
cd Scheduler-Project
```

2. **Create a virtual environment** (recommended):

```bash
python -m venv .venv
# Windows
.\.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
```

3. **Install dependencies:**

```bash
pip install -r requirements.txt
```

This will install:

- `customtkinter` (the modern Tkinter UI library)

*Note:* `tkinter` itself is included with standard Python installations on Windows/macOS for CPython; you don’t install it via `pip`.

---

## Running the Simulator

From the project directory:

```bash
python main.py
```

The **CPU Scheduling Simulator** window should open.

---

## Building a Standalone Executable (Optional)

You can package the simulator as a standalone `.exe` using **PyInstaller**.

1. Install PyInstaller (in your virtual environment or globally):

```bash
pip install pyinstaller
```

2. Build the executable:

```bash
pyinstaller --onefile main.py
```

For a GUI-only executable without console window and with a custom name/icon:

```bash
pyinstaller --onefile --noconsole --name "CPU_Scheduler" --icon=icon.ico main.py
```

This will create an executable in the `dist/` folder.

---

## How Metrics Are Computed

For each process \( i \):

- **Completion Time** \( C_i \): time when the process finishes.
- **Turnaround Time** \( T_i = C_i - A_i \)  
  where \( A_i \) is the arrival time.
- **Waiting Time** \( W_i = T_i - B_i \)  
  where \( B_i \) is the burst time.

Aggregate metrics:

- **Average Waiting Time**  
  \[
  \text{AvgWait} = \frac{1}{n} \sum_i W_i
  \]
- **Average Turnaround Time**  
  \[
  \text{AvgTurn} = \frac{1}{n} \sum_i T_i
  \]
- **CPU Utilization**  
  \[
  \text{CPU Util} = \frac{\text{Total Busy Time}}{\text{Total Time}}
  \]
- **Throughput**  
  \[
  \text{Throughput} = \frac{n}{\text{Total Time}}
  \]

These formulas are standard in operating systems textbooks and match what the simulator uses internally.

---

## Project Structure

- `main.py`  
  The full GUI application and scheduling logic.
- `README.md`  
  This documentation.
- `requirements.txt`  
  Python dependencies.
- `tests/`  
  Folder for unit tests (currently simple placeholders, can be extended).

---

## Possible Extensions

Ideas if you want to extend the project further:

- **Algorithm comparison view**: run all algorithms on the same scenario and show a summary table.
- **Step-by-step playback**: animate the schedule one time unit at a time for SRTF and preemptive priority.
- **Scenario export/import**: save process sets to JSON/CSV and reload them later.
- **Light/dark theme toggle**: allow switching appearance modes dynamically.

---

## License

You can add your own license here (e.g., MIT, GPL, or a custom school license).
