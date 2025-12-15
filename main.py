"""
CPU Scheduling Simulator
========================

This module implements a GUI application (Tkinter) that simulates
classic CPU scheduling algorithms commonly studied in an operating
systems course:

- First-Come, First-Served (FCFS)
- Shortest Job First (SJF, non-preemptive)
- Round Robin (with configurable time quantum)
- Priority Scheduling (non-preemptive, lower number = higher priority)

The GUI allows you to:

- Add processes dynamically (arrival time, burst time, priority)
- Select a scheduling algorithm and (for RR) the time quantum
- Visualize the resulting schedule as a Gantt chart
- Inspect per-process metrics: completion, turnaround, and waiting times,
  plus the average waiting time across all processes.

The code is intentionally written in a clear, modular, and well-documented
style so that it can be used as part of an OS course report.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import customtkinter as ctk
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class Process:
    """
    Represents a single process for CPU scheduling.

    Attributes:
        pid:        A human-readable process identifier (e.g. "P1").
        arrival_time: The time at which the process arrives in the ready queue.
        burst_time:   The total CPU time required by the process.
        priority:     Process priority (lower number = higher priority).
    """

    pid: str
    arrival_time: int
    burst_time: int
    priority: int = 0


# Type alias used by the scheduling functions.
# Each schedule entry represents one contiguous CPU execution interval.
ScheduleEntry = Dict[str, Any]  # keys: "pid", "start", "end"


# ---------------------------------------------------------------------------
# Scheduling algorithms
# ---------------------------------------------------------------------------


def fcfs_scheduling(processes: List[Process]) -> Tuple[List[ScheduleEntry], List[Dict[str, Any]]]:
    """
    First-Come, First-Served (FCFS) scheduling.

    Concept:
        - Non-preemptive.
        - Processes are ordered by arrival time.
        - The CPU is assigned to the process that arrives first.
        - If the CPU becomes idle (no ready process), time jumps forward
          to the arrival of the next process.

    Args:
        processes: List of Process objects to schedule.

    Returns:
        schedule: List of schedule entries describing the Gantt chart.
        stats:    List of per-process metrics dictionaries with keys:
                  pid, arrival_time, burst_time, priority,
                  completion_time, turnaround_time, waiting_time.
    """
    if not processes:
        return [], []

    # Sort by arrival time (and PID for a deterministic tie-break).
    procs = sorted(processes, key=lambda p: (p.arrival_time, p.pid))

    current_time = 0
    schedule: List[ScheduleEntry] = []
    completion_times: Dict[str, int] = {}

    for p in procs:
        # If no process is ready yet, the CPU is idle until this one arrives.
        if current_time < p.arrival_time:
            schedule.append({"pid": None, "start": current_time, "end": p.arrival_time})
            current_time = p.arrival_time

        # Run the process to completion.
        start = current_time
        end = current_time + p.burst_time
        schedule.append({"pid": p.pid, "start": start, "end": end})
        completion_times[p.pid] = end
        current_time = end

    stats: List[Dict[str, Any]] = []
    for p in procs:
        ct = completion_times[p.pid]
        tat = ct - p.arrival_time
        wt = tat - p.burst_time
        stats.append(
            {
                "pid": p.pid,
                "arrival_time": p.arrival_time,
                "burst_time": p.burst_time,
                "priority": p.priority,
                "completion_time": ct,
                "turnaround_time": tat,
                "waiting_time": wt,
            }
        )

    return schedule, stats


def sjf_scheduling(processes: List[Process]) -> Tuple[List[ScheduleEntry], List[Dict[str, Any]]]:
    """
    Shortest Job First (SJF) scheduling, non-preemptive.

    Concept:
        - Non-preemptive.
        - Among the processes that have arrived and are waiting, always
          choose the one with the smallest CPU burst time.
        - If no process is ready, the CPU is idle until the next arrival.

    Args:
        processes: List of Process objects to schedule.

    Returns:
        schedule: Gantt chart schedule entries.
        stats:    Per-process metrics (see fcfs_scheduling docstring).
    """
    if not processes:
        return [], []

    # Sort by arrival time for easier management of "who arrives next".
    procs = sorted(processes, key=lambda p: (p.arrival_time, p.pid))
    n = len(procs)
    completed = 0
    current_time = 0

    schedule: List[ScheduleEntry] = []
    completion_times: Dict[str, int] = {}

    ready_queue: List[Process] = []
    next_index = 0  # Index into procs for the next process that has not yet arrived

    while completed < n:
        # Move all processes that have arrived by current_time into the ready queue.
        while next_index < n and procs[next_index].arrival_time <= current_time:
            ready_queue.append(procs[next_index])
            next_index += 1

        if not ready_queue:
            # No process is ready -> CPU idle until the next process arrives.
            next_arrival = procs[next_index].arrival_time
            if current_time < next_arrival:
                schedule.append({"pid": None, "start": current_time, "end": next_arrival})
            current_time = next_arrival
            continue

        # Select the process with the smallest burst time (SJF rule).
        ready_queue.sort(key=lambda p: (p.burst_time, p.arrival_time, p.pid))
        current = ready_queue.pop(0)

        start = current_time
        end = current_time + current.burst_time
        schedule.append({"pid": current.pid, "start": start, "end": end})
        completion_times[current.pid] = end
        current_time = end
        completed += 1

    # Compute metrics.
    stats: List[Dict[str, Any]] = []
    # Iterate in PID order for a stable table display.
    for p in sorted(procs, key=lambda p: p.pid):
        ct = completion_times[p.pid]
        tat = ct - p.arrival_time
        wt = tat - p.burst_time
        stats.append(
            {
                "pid": p.pid,
                "arrival_time": p.arrival_time,
                "burst_time": p.burst_time,
                "priority": p.priority,
                "completion_time": ct,
                "turnaround_time": tat,
                "waiting_time": wt,
            }
        )

    return schedule, stats


def sjf_preemptive_scheduling(processes: List[Process]) -> Tuple[List[ScheduleEntry], List[Dict[str, Any]]]:
    """
    Shortest Remaining Time First (preemptive SJF) scheduling.

    Concept:
        - Preemptive version of SJF.
        - At every time unit, among the ready processes, choose the one
          with the smallest remaining burst time.
        - A newly arrived process with a shorter remaining time can preempt
          the currently running one at its arrival time.
        - If no process is ready, the CPU is idle until the next arrival.

    Implementation details:
        - Time is modeled in discrete units (burst and arrival times are
          integers).
        - The algorithm simulates the CPU one time unit at a time, always
          re-evaluating which process should run next.
        - The Gantt chart schedule merges consecutive time units where the
          same process runs into a single bar.
    """
    if not processes:
        return [], []

    procs = sorted(processes, key=lambda p: (p.arrival_time, p.pid))
    n = len(procs)

    remaining: Dict[str, int] = {p.pid: p.burst_time for p in procs}
    completion_times: Dict[str, int] = {}

    schedule: List[ScheduleEntry] = []
    ready_queue: List[Process] = []

    current_time = 0
    next_index = 0  # Next process that has not yet been added to the ready queue

    while len(completion_times) < n:
        # Add all processes that have arrived by current_time to the ready queue.
        while next_index < n and procs[next_index].arrival_time <= current_time:
            ready_queue.append(procs[next_index])
            next_index += 1

        if not ready_queue:
            # No ready processes -> CPU idle until the next arrival.
            if next_index < n:
                next_arrival = procs[next_index].arrival_time
                if current_time < next_arrival:
                    if schedule and schedule[-1]["pid"] is None and schedule[-1]["end"] == current_time:
                        # Extend existing idle block.
                        schedule[-1]["end"] = next_arrival
                    else:
                        schedule.append({"pid": None, "start": current_time, "end": next_arrival})
                current_time = next_arrival
                continue
            else:
                # No more processes to arrive and none ready; should not occur
                # if the loop condition is correct, but break defensively.
                break

        # Choose the process with the smallest remaining time.
        ready_queue.sort(key=lambda p: (remaining[p.pid], p.arrival_time, p.pid))
        current = ready_queue[0]
        pid = current.pid

        # Run the chosen process for one time unit.
        if schedule and schedule[-1]["pid"] == pid and schedule[-1]["end"] == current_time:
            schedule[-1]["end"] += 1
        else:
            schedule.append({"pid": pid, "start": current_time, "end": current_time + 1})

        remaining[pid] -= 1
        current_time += 1

        if remaining[pid] == 0:
            # Process has finished at current_time.
            completion_times[pid] = current_time
            # Remove it from the ready queue.
            ready_queue = [p for p in ready_queue if p.pid != pid]

    # Compute metrics.
    stats: List[Dict[str, Any]] = []
    for p in sorted(procs, key=lambda p: p.pid):
        ct = completion_times[p.pid]
        tat = ct - p.arrival_time
        wt = tat - p.burst_time
        stats.append(
            {
                "pid": p.pid,
                "arrival_time": p.arrival_time,
                "burst_time": p.burst_time,
                "priority": p.priority,
                "completion_time": ct,
                "turnaround_time": tat,
                "waiting_time": wt,
            }
        )

    return schedule, stats


def priority_scheduling(processes: List[Process]) -> Tuple[List[ScheduleEntry], List[Dict[str, Any]]]:
    """
    Priority scheduling, non-preemptive.

    Convention:
        - Lower numeric priority value means *higher* priority.
          (Priority 1 is higher than 2.)

    Concept:
        - Non-preemptive.
        - Among the ready processes, always choose the one with the
          highest priority (smallest numeric priority).
        - If no process is ready, the CPU is idle until the next arrival.

    Args:
        processes: List of Process objects to schedule.

    Returns:
        schedule: Gantt chart schedule entries.
        stats:    Per-process metrics (see fcfs_scheduling docstring).
    """
    if not processes:
        return [], []

    procs = sorted(processes, key=lambda p: (p.arrival_time, p.pid))
    n = len(procs)
    completed = 0
    current_time = 0

    schedule: List[ScheduleEntry] = []
    completion_times: Dict[str, int] = {}

    ready_queue: List[Process] = []
    next_index = 0

    while completed < n:
        # Add newly arrived processes to the ready queue.
        while next_index < n and procs[next_index].arrival_time <= current_time:
            ready_queue.append(procs[next_index])
            next_index += 1

        if not ready_queue:
            # CPU is idle.
            next_arrival = procs[next_index].arrival_time
            if current_time < next_arrival:
                schedule.append({"pid": None, "start": current_time, "end": next_arrival})
            current_time = next_arrival
            continue

        # Pick the ready process with the highest priority
        # (lowest numeric priority value).
        ready_queue.sort(key=lambda p: (p.priority, p.arrival_time, p.pid))
        current = ready_queue.pop(0)

        start = current_time
        end = current_time + current.burst_time
        schedule.append({"pid": current.pid, "start": start, "end": end})
        completion_times[current.pid] = end
        current_time = end
        completed += 1

    stats: List[Dict[str, Any]] = []
    for p in sorted(procs, key=lambda p: p.pid):
        ct = completion_times[p.pid]
        tat = ct - p.arrival_time
        wt = tat - p.burst_time
        stats.append(
            {
                "pid": p.pid,
                "arrival_time": p.arrival_time,
                "burst_time": p.burst_time,
                "priority": p.priority,
                "completion_time": ct,
                "turnaround_time": tat,
                "waiting_time": wt,
            }
        )

    return schedule, stats


def priority_preemptive_scheduling(processes: List[Process]) -> Tuple[List[ScheduleEntry], List[Dict[str, Any]]]:
    """
    Priority scheduling, preemptive.

    Convention:
        - Lower numeric priority value means *higher* priority.
          (Priority 1 is higher than 2.)

    Concept:
        - Preemptive.
        - At every time unit, among the ready processes, the one with the
          highest priority (smallest numeric value) is chosen.
        - A newly arrived process with a higher priority can preempt the
          currently running one at its arrival time.
        - If no process is ready, the CPU is idle until the next arrival.
    """
    if not processes:
        return [], []

    procs = sorted(processes, key=lambda p: (p.arrival_time, p.pid))
    n = len(procs)

    remaining: Dict[str, int] = {p.pid: p.burst_time for p in procs}
    completion_times: Dict[str, int] = {}

    schedule: List[ScheduleEntry] = []
    ready_queue: List[Process] = []

    current_time = 0
    next_index = 0

    while len(completion_times) < n:
        # Add newly arrived processes to the ready queue.
        while next_index < n and procs[next_index].arrival_time <= current_time:
            ready_queue.append(procs[next_index])
            next_index += 1

        if not ready_queue:
            # CPU idle until the next arrival.
            if next_index < n:
                next_arrival = procs[next_index].arrival_time
                if current_time < next_arrival:
                    if schedule and schedule[-1]["pid"] is None and schedule[-1]["end"] == current_time:
                        schedule[-1]["end"] = next_arrival
                    else:
                        schedule.append({"pid": None, "start": current_time, "end": next_arrival})
                current_time = next_arrival
                continue
            else:
                break

        # Choose the ready process with the highest priority.
        ready_queue.sort(key=lambda p: (p.priority, p.arrival_time, p.pid))
        current = ready_queue[0]
        pid = current.pid

        # Run for one time unit.
        if schedule and schedule[-1]["pid"] == pid and schedule[-1]["end"] == current_time:
            schedule[-1]["end"] += 1
        else:
            schedule.append({"pid": pid, "start": current_time, "end": current_time + 1})

        remaining[pid] -= 1
        current_time += 1

        if remaining[pid] == 0:
            completion_times[pid] = current_time
            ready_queue = [p for p in ready_queue if p.pid != pid]

    stats: List[Dict[str, Any]] = []
    for p in sorted(procs, key=lambda p: p.pid):
        ct = completion_times[p.pid]
        tat = ct - p.arrival_time
        wt = tat - p.burst_time
        stats.append(
            {
                "pid": p.pid,
                "arrival_time": p.arrival_time,
                "burst_time": p.burst_time,
                "priority": p.priority,
                "completion_time": ct,
                "turnaround_time": tat,
                "waiting_time": wt,
            }
        )

    return schedule, stats


def round_robin_scheduling(
    processes: List[Process], quantum: int
) -> Tuple[List[ScheduleEntry], List[Dict[str, Any]]]:
    """
    Round Robin (RR) scheduling with a given time quantum.

    Concept:
        - Preemptive.
        - Each process gets a time slice of length 'quantum'.
        - After using its slice (or if it finishes earlier), the process is
          moved to the end of the ready queue (if it is not finished).
        - New processes that arrive while the CPU is running are added
          to the ready queue as soon as they arrive.
        - When the ready queue is empty, the CPU is idle until the next
          process arrives.

    Args:
        processes: List of Process objects to schedule.
        quantum:   The time quantum (must be a positive integer).

    Returns:
        schedule: Gantt chart schedule entries.
        stats:    Per-process metrics (see fcfs_scheduling docstring).
    """
    if not processes:
        return [], []
    if quantum <= 0:
        raise ValueError("Time quantum must be a positive integer.")

    procs = sorted(processes, key=lambda p: (p.arrival_time, p.pid))
    n = len(procs)

    # Remaining burst time per process.
    remaining: Dict[str, int] = {p.pid: p.burst_time for p in procs}
    completion_times: Dict[str, int] = {}

    schedule: List[ScheduleEntry] = []
    ready_queue: List[Process] = []

    current_time = 0
    next_index = 0  # Next process that has not yet been inserted into the ready queue.

    while len(completion_times) < n:
        # If there are no ready processes, advance time to the next arrival.
        if not ready_queue and next_index < n and current_time < procs[next_index].arrival_time:
            next_arrival = procs[next_index].arrival_time
            schedule.append({"pid": None, "start": current_time, "end": next_arrival})
            current_time = next_arrival

        # Add all processes that have arrived by current_time to the ready queue.
        while next_index < n and procs[next_index].arrival_time <= current_time:
            ready_queue.append(procs[next_index])
            next_index += 1

        if not ready_queue:
            # No process is ready and we have already advanced to next arrival.
            # Loop will continue and add newly arrived processes above.
            continue

        current = ready_queue.pop(0)

        # Determine how long this process will run in this slice.
        run_time = min(quantum, remaining[current.pid])
        start = current_time
        end = current_time + run_time
        schedule.append({"pid": current.pid, "start": start, "end": end})

        # Update time and remaining burst.
        current_time = end
        remaining[current.pid] -= run_time

        # Add any processes that arrived during this time slice.
        while next_index < n and procs[next_index].arrival_time <= current_time:
            ready_queue.append(procs[next_index])
            next_index += 1

        if remaining[current.pid] > 0:
            # Not finished: put it back at the end of the queue.
            ready_queue.append(current)
        else:
            # Finished: record completion time.
            completion_times[current.pid] = current_time

    stats: List[Dict[str, Any]] = []
    for p in sorted(procs, key=lambda p: p.pid):
        ct = completion_times[p.pid]
        tat = ct - p.arrival_time
        wt = tat - p.burst_time
        stats.append(
            {
                "pid": p.pid,
                "arrival_time": p.arrival_time,
                "burst_time": p.burst_time,
                "priority": p.priority,
                "completion_time": ct,
                "turnaround_time": tat,
                "waiting_time": wt,
            }
        )

    return schedule, stats


# ---------------------------------------------------------------------------
# Simple tooltip helper for Tk / customtkinter widgets
# ---------------------------------------------------------------------------


class _ToolTip:
    """Minimal tooltip implementation for Tk / customtkinter widgets."""

    def __init__(self, widget: tk.Widget, text: str) -> None:
        self.widget = widget
        self.text = text
        self._tip_window: Optional[tk.Toplevel] = None
        widget.bind("<Enter>", self._on_enter)
        widget.bind("<Leave>", self._on_leave)

    def _on_enter(self, _event: tk.Event) -> None:
        if self._tip_window is not None:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        self._tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            tw,
            text=self.text,
            justify="left",
            background="#111827",
            foreground="#F9FAFB",
            relief="solid",
            borderwidth=1,
            font=("Segoe UI", 9),
            padx=4,
            pady=2,
        )
        label.pack(ipadx=1)

    def _on_leave(self, _event: tk.Event) -> None:
        if self._tip_window is not None:
            self._tip_window.destroy()
            self._tip_window = None


def _add_tooltip(widget: tk.Widget, text: str) -> None:
    """Attach a tooltip with the given text to a widget."""
    _ToolTip(widget, text)


# ---------------------------------------------------------------------------
# GUI Application
# ---------------------------------------------------------------------------


class CPUSchedulerApp:
    """
    customtkinter-based GUI for exploring CPU scheduling algorithms.

    High-level structure:
        - Top section: process input (arrival, burst, priority) + list of processes.
        - Middle section: algorithm selection + (for RR) quantum selection.
        - Bottom section: Gantt chart (Canvas) + metrics table (Treeview).
    """

    def __init__(self, root: Optional[ctk.CTk] = None) -> None:
        # Configure global appearance for customtkinter.
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        if root is None:
            root = ctk.CTk()
        self.root = root
        self.root.title("CPU Scheduling Simulator")
        self.root.geometry("1100x700")

        # Algorithm selection: store internal key in algorithm_var.
        self.algorithm_var = ctk.StringVar(value="FCFS")

        # Mapping from human-readable labels to internal keys.
        self._algorithm_display_to_key: Dict[str, str] = {
            "First-Come, First-Served (FCFS)": "FCFS",
            "Shortest Job First (SJF, non-preemptive)": "SJF",
            "Shortest Remaining Time First (SJF, preemptive)": "SJF_PREEMPTIVE",
            "Priority Scheduling (non-preemptive)": "PRIORITY",
            "Priority Scheduling (preemptive)": "PRIORITY_PREEMPTIVE",
            "Round Robin (RR)": "RR",
        }
        self._algorithm_label_var = ctk.StringVar(
            value="First-Come, First-Served (FCFS)"
        )

        # Appearance mode (Dark / Light) for the UI.
        self._appearance_var = ctk.StringVar(value="Dark")"
        )

        # Counter used to assign new process identifiers (P1, P2, ...).
        self._next_pid = 1

        # Currently selected PID (for cross-highlighting).
        self._selected_pid: Optional[str] = None

        # Last computed schedule and playback state for the Gantt chart.
        self._current_schedule: List[ScheduleEntry] = []
        self._playback_time: Optional[int] = None
        self._playback_running: bool = False
        self._playback_job_id: Optional[str] = None

        # Mapping from comparison table rows to algorithm keys.
        self._comparison_algorithm_for_item

        # Configure ttk-based widgets (Treeview) to match the dark theme.
        self._configure_treeview_style()

        self._build_ui()

    def _configure_treeview_style(self) -> None:
        """Apply a dark theme to ttk Treeview widgets so they match customtkinter."""
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure(
            "Treeview",
            background="#020617",
            foreground="#E5E7EB",
            fieldbackground="#020617",
            bordercolor="#1F2937",
            borderwidth=1,
            rowheight=22,
        )
        style.map(
            "Treeview",
            background=[("selected", "#1D4ED8")],
            foreground=[("selected", "#F9FAFB")],
        )
        style.configure(
            "Treeview.Heading",
            background="#0F172A",
            foreground="#E5E7EB",
            font=("Segoe UI Semibold", 9),
        )

    def _on_theme_changed(self, mode: str) -> None:
        """
        Callback when the Dark/Light segmented button is changed.

        Updates the global appearance mode and reapplies Treeview styling.
        """
        # customtkinter expects lowercase "dark"/"light".
        ctk.set_appearance_mode(mode.lower())
        # Reapply Treeview styling so headers / rows match the new theme.
        self._configure_treeview_style()

    def _show_help_window(self) -> None:
        """Open a small help window explaining the algorithms and metrics."""
        # Avoid opening multiple help windows.
        if hasattr(self, "_help_window") and self._help_window is not None:
            try:
                self._help_window.lift()
                return
            except tk.TclError:
                self._help_window = None

        help_win = self._help_window = ctk.CTkToplevel(self.root)
        help_win.title("CPU Scheduling – Theory Overview")
        help_win.geometry("700x500")

        container = ctk.CTkScrollableFrame(help_win, corner_radius=0)
        container.pack(fill="both", expand=True, padx=12, pady=12)

        title = ctk.CTkLabel(
            container,
            text="CPU Scheduling Algorithms – Overview",
            font=("Segoe UI Semibold", 18),
        )
        title.pack(anchor="w", pady=(0, 8))

        text_blocks = [
            (
                "FCFS (First-Come, First-Served)",
                "Non-preemptive. Processes are served strictly in order of arrival.\n"
                "Simple to implement but can suffer from the 'convoy effect' when a "
                "long job blocks many short ones.",
            ),
            (
                "SJF (Shortest Job First, non-preemptive)",
                "Among the ready processes, always run the one with the smallest "
                "burst time. Minimizes average waiting time in theory, but can "
                "cause starvation of long jobs.",
            ),
            (
                "SRTF (Shortest Remaining Time First, preemptive SJF)",
                "Preemptive version of SJF. At every time unit, runs the process "
                "with the smallest remaining time. New shorter jobs can preempt "
                "the current job.",
            ),
            (
                "Priority Scheduling (non-preemptive / preemptive)",
                "Each process has a priority (lower number = higher priority).\n"
                "The highest-priority job runs first. Can cause starvation of "
                "low-priority jobs if high-priority jobs keep arriving.",
            ),
            (
                "Round Robin (RR)",
                "Preemptive, time-sliced scheduling. Each process receives up to "
                "a fixed time quantum, then moves to the back of the ready queue.\n"
                "Good for time-sharing systems; behavior depends heavily on the "
                "chosen quantum.",
            ),
            (
                "Metrics",
                "Turnaround Time T = Completion - Arrival.\n"
                "Waiting Time   W = Turnaround - Burst.\n"
                "CPU Utilization = BusyTime / TotalTime.\n"
                "Throughput      = NumberOfProcesses / TotalTime.",
            ),
        ]

        for heading, body in text_blocks:
            lbl_h = ctk.CTkLabel(
                container,
                text=heading,
                font=("Segoe UI Semibold", 14),
            )
            lbl_h.pack(anchor="w", pady=(10, 2))
            lbl_b = ctk.CTkLabel(
                container,
                text=body,
                font=("Segoe UI", 11),
                justify="left",
            )
            lbl_b.pack(anchor="w")

        close_btn = ctk.CTkButton(
            container,
            text="Close",
            width=100,
            command=help_win.destroy,
        )
        close_btn.pack(anchor="e", pady=(16, 0))

    # ------------------------------------------------------------------#
    # UI construction                                                   #
    # ------------------------------------------------------------------#

    def _build_ui(self) -> None:
        """Create and lay out all GUI widgets."""
        # Wrap the entire content in a scrollable frame so the bottom sections
        # (Gantt chart and Process Metrics table) remain accessible on smaller screens.
        main_frame = ctk.CTkScrollableFrame(
            self.root,
            corner_radius=0,
            fg_color="transparent",
        )
        main_frame.pack(fill="both", expand=True, padx=16, pady=16)

        # Title area.
        header_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 10))

        title_left = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_left.pack(side="left", fill="x", expand=True)

        title_label = ctk.CTkLabel(
            title_left,
            text="CPU Scheduling Simulator",
            font=("Segoe UI Semibold", 22),
        )
        subtitle_label = ctk.CTkLabel(
            title_left,
            text="FCFS • SJF • SRTF • Priority • Round Robin",
            font=("Segoe UI", 12),
        )
        title_label.pack(anchor="w")
        subtitle_label.pack(anchor="w")

        # Right side: theme toggle and help button.
        title_right = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_right.pack(side="right")

        theme_toggle = ctk.CTkSegmentedButton(
            title_right,
            values=["Dark", "Light"],
            variable=self._appearance_var,
            width=140,
            command=self._on_theme_changed,
        )
        theme_toggle.pack(side="right", padx=(0, 8))

        help_button = ctk.CTkButton(
            title_right,
            text="Help / Theory",
            width=110,
            command=self._show_help_window,
        )
        help_button.pack(side="right", padx=(0, 8))

        # Process input, algorithm selection, and output.
        self._build_process_input_section(main_frame)
        self._build_algorithm_section(main_frame)
        self._build_output_section(main_frame)

    def _build_process_input_section(self, parent: ctk.CTkFrame) -> None:
        frame = ctk.CTkFrame(parent, corner_radius=12)
        frame.pack(fill="x", pady=(10, 10))

        header = ctk.CTkLabel(
            frame,
            text="Process Input",
            font=("Segoe UI Semibold", 13),
        )
        header.grid(row=0, column=0, columnspan=2, padx=12, pady=(10, 6), sticky="w")

        # Input row: arrival time, burst time, priority, and buttons.
        arrival_label = ctk.CTkLabel(frame, text="Arrival Time (ms)")
        arrival_label.grid(row=1, column=0, padx=12, pady=4, sticky="w")
        self.arrival_entry = ctk.CTkEntry(frame, width=80)
        self.arrival_entry.grid(row=1, column=1, padx=6, pady=4, sticky="w")

        burst_label = ctk.CTkLabel(frame, text="Burst Time (ms)")
        burst_label.grid(row=1, column=2, padx=12, pady=4, sticky="w")
        self.burst_entry = ctk.CTkEntry(frame, width=80)
        self.burst_entry.grid(row=1, column=3, padx=6, pady=4, sticky="w")

        priority_label = ctk.CTkLabel(frame, text="Priority\n(lower = higher)")
        priority_label.grid(row=1, column=4, padx=12, pady=4, sticky="w")
        self.priority_entry = ctk.CTkEntry(frame, width=80)

        # Tooltips with quick hints.
        _add_tooltip(
            priority_label,
            "Lower numeric value = higher priority.\n"
            "Example: priority 1 runs before priority 3.",
        )
        self.priority_entry.grid(row=1, column=5, padx=6, pady=4, sticky="w")

        add_button = ctk.CTkButton(
            frame,
            text="Add Process",
            command=self.add_process,
            width=110,
        )
        add_button.grid(row=1, column=6, padx=10, pady=4)

        remove_button = ctk.CTkButton(
            frame,
            text="Remove Selected",
            command=self.remove_selected_process,
            width=140,
            fg_color="#1F2937",
            hover_color="#111827",
        )
        remove_button.grid(row=1, column=7, padx=10, pady=4)

        # Treeview to display the current list of processes (styled like the metrics table).
        columns = ("pid", "arrival", "burst", "priority")
        self.process_tree = ttk.Treeview(
            frame,
            columns=columns,
            show="headings",
            height=8,  # show more input rows at once
        )
        self.process_tree.heading("pid", text="PID")
        self.process_tree.heading("arrival", text="Arrival")
        self.process_tree.heading("burst", text="Burst")
        self.process_tree.heading("priority", text="Priority")

        for col in columns:
            # Centered values and stretchable columns for consistency.
            self.process_tree.column(col, anchor="center", width=90, stretch=True)

        # Striped rows for readability (same colors as metrics table).
        self.process_tree.tag_configure("evenrow", background="#020617")
        self.process_tree.tag_configure("oddrow", background="#111827")

        self.process_tree.grid(
            row=2, column=0, columnspan=8, sticky="nsew", padx=12, pady=(8, 10)
        )

        scrollbar = ttk.Scrollbar(
            frame, orient="vertical", command=self.process_tree.yview
        )
        self.process_tree.configure(yscroll=scrollbar.set)
        scrollbar.grid(row=2, column=8, sticky="ns", pady=(8, 10))

        # When a process row is selected, highlight it across the UI.
        self.process_tree.bind("<<TreeviewSelect>>", self._on_process_tree_select)

        # Allow the tree to expand horizontally.
        for col_index in range(8):
            frame.columnconfigure(col_index, weight=1)
        frame.rowconfigure(2, weight=1)

    def _build_algorithm_section(self, parent: ctk.CTkFrame) -> None:
        frame = ctk.CTkFrame(parent, corner_radius=12)
        frame.pack(fill="x", pady=(0, 10))

        algo_label = ctk.CTkLabel(
            frame,
            text="Scheduling Algorithm",
            font=("Segoe UI Semibold", 13),
        )
        algo_label.grid(row=0, column=0, padx=12, pady=10, sticky="w")

        # Combobox for algorithm selection.
        self.algorithm_combobox = ctk.CTkComboBox(
            frame,
            values=list(self._algorithm_display_to_key.keys()),
            variable=self._algorithm_label_var,
            width=320,
            state="readonly",
            command=self._on_algorithm_combobox_change,
        )
        self.algorithm_combobox.grid(row=0, column=1, padx=8, pady=10, sticky="w")
        _add_tooltip(
            self.algorithm_combobox,
            "Choose the CPU scheduling algorithm.\n"
            "Preemptive variants: SRTF, Preemptive Priority, Round Robin.",
        )

        # Time quantum controls (only used for RR).
        quantum_label = ctk.CTkLabel(frame, text="Time Quantum")
        quantum_label.grid(row=0, column=2, padx=(20, 4), pady=10, sticky="e")

        self.quantum_entry = ctk.CTkEntry(frame, width=80)
        self.quantum_entry.insert(0, "2")
        self.quantum_entry.grid(row=0, column=3, padx=(0, 10), pady=10, sticky="w")
        _add_tooltip(
            quantum_label,
            "Round Robin only:\n"
            "Each process gets up to this many time units per turn.",
        )

        # Make sure internal variable matches initial selection and quantum state.
        self._on_algorithm_combobox_change(self._algorithm_label_var.get())

        # Simulation control buttons.
        run_button = ctk.CTkButton(
            frame,
            text="Run Simulation",
            command=self.run_simulation,
            width=140,
        )
        run_button.grid(row=0, column=4, padx=(10, 5), pady=10)

        compare_button = ctk.CTkButton(
            frame,
            text="Compare Algorithms",
            command=self.run_comparison,
            width=170,
        )
        compare_button.grid(row=0, column=5, padx=(5, 5), pady=10)

        clear_button = ctk.CTkButton(
            frame,
            text="Clear All",
            command=self.clear_all,
            width=120,
            fg_color="#1F2937",
            hover_color="#111827",
        )
        clear_button.grid(row=0, column=6, padx=(5, 10), pady=10)

        # Example scenarios dropdown for quickly loading demo datasets.
        scenario_label = ctk.CTkLabel(
            frame,
            text="Example Scenario",
            font=("Segoe UI", 11),
        )
        scenario_label.grid(row=1, column=0, padx=12, pady=(0, 6), sticky="w")

        self.scenario_var = ctk.StringVar(value="None")
        self.scenario_combobox = ctk.CTkComboBox(
            frame,
            values=[
                "None",
                "Simple FCFS demo",
                "Starvation example (Priority)",
                "Preemptive vs Non-preemptive SJF",
            ],
            variable=self.scenario_var,
            width=320,
            state="readonly",
            command=self._on_scenario_selected,
        )
        self.scenario_combobox.grid(
            row=1, column=1, columnspan=3, padx=8, pady=(0, 6), sticky="w"
        )
        _add_tooltip(
            self.scenario_combobox,
            "Load a predefined set of processes that illustrates\n"
            "a particular scheduling behavior (e.g., starvation).",
        )

        # Small container under the Run button to stack the average labels vertically.
        averages_frame = ctk.CTkFrame(frame, fg_color="transparent")
        averages_frame.grid(
            row=2,
            column=4,
            columnspan=2,
            padx=(10, 10),
            pady=(0, 10),
            sticky="ne",
        )

        self.avg_waiting_label = ctk.CTkLabel(
            averages_frame,
            text="Average Waiting Time: N/A",
            font=("Segoe UI Semibold", 16),
        )
        self.avg_waiting_label.pack(anchor="e")

        self.avg_turnaround_label = ctk.CTkLabel(
            averages_frame,
            text="Average Turnaround Time: N/A",
            font=("Segoe UI Semibold", 16),
        )
        self.avg_turnaround_label.pack(anchor="e")

        # Additional aggregate metrics for the current run.
        self.extra_metrics_label = ctk.CTkLabel(
            averages_frame,
            text=(
                "CPU Utilization: N/A  |  Throughput: N/A  |  "
                "Min Waiting: N/A  |  Max Waiting: N/A"
            ),
            font=("Segoe UI", 11),
        )
        self.extra_metrics_label.pack(anchor="e", pady=(4, 0))

        frame.columnconfigure(1, weight=1)

    def _on_algorithm_combobox_change(self, selected_label: str) -> None:
        """Update internal algorithm key when the combobox selection changes."""
        key = self._algorithm_display_to_key.get(selected_label, "FCFS")
        self.algorithm_var.set(key)

        # Enable the time quantum field only for Round Robin.
        if key == "RR":
            self.quantum_entry.configure(state="normal")
        else:
            self.quantum_entry.configure(state="disabled")

    def _build_output_section(self, parent: ctk.CTkFrame) -> None:
        frame = ctk.CTkFrame(parent, corner_radius=12)
        frame.pack(fill="both", expand=True)

        # Gantt chart section.
        gantt_frame = ctk.CTkFrame(frame, corner_radius=12)
        gantt_frame.pack(fill="x", padx=10, pady=(10, 0))

        gantt_label = ctk.CTkLabel(
            gantt_frame,
            text="Gantt Chart",
            font=("Segoe UI Semibold", 13),
        )
        gantt_label.pack(anchor="w", padx=12, pady=(10, 4))

        self.gantt_canvas = tk.Canvas(
            gantt_frame,
            height=220,
            bg="#020617",
            highlightthickness=0,
        )
        self.gantt_canvas.pack(fill="x", padx=12, pady=(0, 12))

        # Playback controls for stepping through the schedule in time.
        playback_frame = ctk.CTkFrame(gantt_frame, fg_color="transparent")
        playback_frame.pack(fill="x", padx=12, pady=(0, 10))

        step_back_btn = ctk.CTkButton(
            playback_frame,
            text="⏮ Step Back",
            width=110,
            command=self._playback_step_back,
        )
        step_back_btn.pack(side="left", padx=(0, 6))

        step_forward_btn = ctk.CTkButton(
            playback_frame,
            text="⏭ Step Forward",
            width=120,
            command=self._playback_step_forward,
        )
        step_forward_btn.pack(side="left", padx=(0, 6))

        play_btn = ctk.CTkButton(
            playback_frame,
            text="▶ Play",
            width=80,
            command=self._playback_start,
        )
        play_btn.pack(side="left", padx=(12, 6))

        pause_btn = ctk.CTkButton(
            playback_frame,
            text="⏸ Pause",
            width=90,
            command=self._playback_pause,
        )
        pause_btn.pack(side="left", padx=(0, 6))

        self.playback_time_label = ctk.CTkLabel(
            playback_frame,
            text="Time: t = -",
            font=("Segoe UI", 11),
        )
        self.playback_time_label.pack(side="right")

        # Process metrics section.
        metrics_frame = ctk.CTkFrame(frame, corner_radius=12)
        metrics_frame.pack(fill="both", expand=True, padx=10, pady=(10, 0))

        metrics_label = ctk.CTkLabel(
            metrics_frame,
            text="Process Metrics",
            font=("Segoe UI Semibold", 13),
        )
        metrics_label.pack(anchor="w", padx=12, pady=(10, 4))

        table_container = ctk.CTkFrame(metrics_frame, fg_color="transparent")
        table_container.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        result_columns = (
            "pid",
            "arrival",
            "burst",
            "priority",
            "completion",
            "turnaround",
            "waiting",
        )
        # Tall Treeview to show more rows without scrolling.
        self.results_tree = ttk.Treeview(
            table_container,
            columns=result_columns,
            show="headings",
            height=12,  # show more rows at once
        )

        headings = [
            ("pid", "PID"),
            ("arrival", "Arrival"),
            ("burst", "Burst"),
            ("priority", "Priority"),
            ("completion", "Completion"),
            ("turnaround", "Turnaround"),
            ("waiting", "Waiting"),
        ]
        for col, label in headings:
            self.results_tree.heading(col, text=label)
            # Center all values; allow columns to stretch with the window.
            self.results_tree.column(col, anchor="center", width=90, stretch=True)

        # Striped rows for readability.
        self.results_tree.tag_configure("evenrow", background="#020617")
        self.results_tree.tag_configure("oddrow", background="#111827")

        # Let the table fill the available space at the bottom of the window.
        self.results_tree.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(4, 0),
            pady=4,
        )

        metrics_scrollbar = ttk.Scrollbar(
            table_container, orient="vertical", command=self.results_tree.yview
        )
        self.results_tree.configure(yscroll=metrics_scrollbar.set)
        metrics_scrollbar.pack(side="right", fill="y", padx=(0, 4), pady=4)

        # Export controls under the metrics table.
        export_frame = ctk.CTkFrame(metrics_frame, fg_color="transparent")
        export_frame.pack(fill="x", padx=12, pady=(0, 10))

        export_csv_btn = ctk.CTkButton(
            export_frame,
            text="Export Metrics (CSV)",
            width=170,
            command=self._export_metrics_csv,
        )
        export_csv_btn.pack(side="left", padx=(0, 8))

        export_chart_btn = ctk.CTkButton(
            export_frame,
            text="Save Gantt Chart (PS)",
            width=190,
            command=self._export_gantt_chart,
        )
        export_chart_btn.pack(side="left", padx=(0, 8))

        # Algorithm comparison section.
        comparison_frame = ctk.CTkFrame(frame, corner_radius=12)
        comparison_frame.pack(fill="both", expand=True, padx=10, pady=(10, 10))

        comparison_label = ctk.CTkLabel(
            comparison_frame,
            text="Algorithm Comparison",
            font=("Segoe UI Semibold", 13),
        )
        comparison_label.pack(anchor="w", padx=12, pady=(10, 4))

        comparison_container = ctk.CTkFrame(comparison_frame, fg_color="transparent")
        comparison_container.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        comparison_columns = (
            "algorithm",
            "avg_waiting",
            "avg_turnaround",
            "cpu_util",
            "throughput",
        )
        self.comparison_tree = ttk.Treeview(
            comparison_container,
            columns=comparison_columns,
            show="headings",
            height=6,
        )

        comparison_headings = [
            ("algorithm", "Algorithm"),
            ("avg_waiting", "Avg Waiting"),
            ("avg_turnaround", "Avg Turnaround"),
            ("cpu_util", "CPU Util (%)"),
            ("throughput", "Throughput"),
        ]
        for col, label in comparison_headings:
            self.comparison_tree.heading(col, text=label)
            self.comparison_tree.column(col, anchor="center", width=120, stretch=True)

        self.comparison_tree.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(4, 0),
            pady=4,
        )

        comparison_scrollbar = ttk.Scrollbar(
            comparison_container,
            orient="vertical",
            command=self.comparison_tree.yview,
        )
        self.comparison_tree.configure(yscroll=comparison_scrollbar.set)
        comparison_scrollbar.pack(side="right", fill="y", padx=(0, 4), pady=4)

        self.comparison_tree.bind("<<TreeviewSelect>>", self._on_comparison_select)

    # ------------------------------------------------------------------#
    # Process list operations                                           #
    # ------------------------------------------------------------------#

    def add_process(self) -> None:
        """
        Add a new process using the values from the entry fields.

        Arrival time and burst time must be integers; burst time must be > 0,
        and arrival time must be >= 0. Priority is optional (defaults to 0
        if left blank).
        """
        arrival_text = self.arrival_entry.get().strip()
        burst_text = self.burst_entry.get().strip()
        priority_text = self.priority_entry.get().strip()

        try:
            arrival = int(arrival_text)
            burst = int(burst_text)
        except ValueError:
            messagebox.showerror("Invalid input", "Arrival and burst times must be integers.")
            return

        if arrival < 0 or burst <= 0:
            messagebox.showerror(
                "Invalid input",
                "Arrival time must be >= 0 and burst time must be > 0.",
            )
            return

        if priority_text:
            try:
                priority = int(priority_text)
            except ValueError:
                messagebox.showerror("Invalid input", "Priority must be an integer if specified.")
                return
        else:
            priority = 0

        pid = f"P{self._next_pid}"
        self._next_pid += 1

        # Determine row stripe (even/odd) to match the metrics table style.
        row_index = len(self.process_tree.get_children())
        tag = "evenrow" if row_index % 2 == 0 else "oddrow"

        self.process_tree.insert(
            "",
            "end",
            values=(pid, arrival, burst, priority),
            tags=(tag,),
        )

        # Clear input fields to make adding the next process easier.
        self.arrival_entry.delete(0, tk.END)
        self.burst_entry.delete(0, tk.END)
        self.priority_entry.delete(0, tk.END)

    def remove_selected_process(self) -> None:
        """Remove the selected process(es) from the process list."""
        selection = self.process_tree.selection()
        for item in selection:
            self.process_tree.delete(item)

        # Re-apply row striping after deletions.
        self._restyle_process_tree_rows()

    def clear_all(self) -> None:
        """Clear all processes, results, comparison data, and the Gantt chart."""
        for item in self.process_tree.get_children():
            self.process_tree.delete(item)

        for item in self.results_tree.get_children():
            self.results_tree.delete(item)

        # Clear comparison table if it exists.
        if hasattr(self, "comparison_tree"):
            for item in self.comparison_tree.get_children():
                self.comparison_tree.delete(item)

        self.gantt_canvas.delete("all")
        self.avg_waiting_label.configure(text="Average Waiting Time: N/A")
        self.avg_turnaround_label.configure(text="Average Turnaround Time: N/A")
        if hasattr(self, "extra_metrics_label"):
            self.extra_metrics_label.configure(
                text="CPU Utilization: N/A  |  Throughput: N/A  |  Min Waiting: N/A  |  Max Waiting: N/A"
            )

        # Reset PID counter so new processes start again at P1.
        self._next_pid = 1

        # Clear selection-related and playback state.
        self._selected_pid = None
        self._current_schedule = []
        self._playback_time = None
        self._playback_running = False
        self._playback_job_id = None
        if hasattr(self, "playback_time_label"):
            self.playback_time_label.configure(text="Time: t = -")

        # Re-apply striping (no rows, but keeps things consistent if extended later).
        self._restyle_process_tree_rows()

    # ------------------------------------------------------------------#
    # Simulation + visualization                                       #
    # ------------------------------------------------------------------#

    def _restyle_process_tree_rows(self) -> None:
        """Apply alternating row colors to the process input Treeview."""
        for index, item in enumerate(self.process_tree.get_children()):
            tag = "evenrow" if index % 2 == 0 else "oddrow"
            self.process_tree.item(item, tags=(tag,))

    # ------------------------------------------------------------------#
    # Selection handling + scenarios                                    #
    # ------------------------------------------------------------------#

    def _on_process_tree_select(self, event: tk.Event) -> None:
        """
        When a process is selected in the input table, highlight the same PID
        in the metrics table (if present) and emphasize its segments in the
        Gantt chart.
        """
        selection = self.process_tree.selection()
        if not selection:
            self._selected_pid = None
            # Clear metrics table selection.
            self.results_tree.selection_remove(*self.results_tree.selection())
            # Redraw Gantt chart without emphasis if we have a schedule.
            if self._current_schedule:
                self._draw_gantt_chart(self._current_schedule)
            return

        item_id = selection[0]
        values = self.process_tree.item(item_id, "values")
        if not values:
            return

        pid = str(values[0])
        self._selected_pid = pid

        # Highlight the corresponding row in the metrics table.
        self.results_tree.selection_remove(*self.results_tree.selection())
        for metrics_item in self.results_tree.get_children():
            m_values = self.results_tree.item(metrics_item, "values")
            if m_values and str(m_values[0]) == pid:
                self.results_tree.selection_set(metrics_item)
                self.results_tree.see(metrics_item)
                break

        # Redraw Gantt chart with emphasized segments for this PID.
        if self._current_schedule:
            self._draw_gantt_chart(self._current_schedule)

    def _on_scenario_selected(self, selected_label: str) -> None:
        """
        Load one of the predefined example scenarios into the process input
        table. This clears the current processes and results.
        """
        if selected_label == "None":
            return

        # Clear existing simulation state.
        self.clear_all()

        # Define scenarios as lists of (arrival, burst, priority).
        scenarios = {
            "Simple FCFS demo": [
                (0, 5, 2),
                (2, 3, 1),
                (4, 1, 3),
                (6, 7, 2),
            ],
            "Starvation example (Priority)": [
                # One low-priority job arrives first, many high-priority jobs arrive later.
                (0, 20, 5),  # P1, low priority, long job
                (2, 3, 1),   # P2, high priority
                (4, 4, 1),   # P3, high priority
                (6, 2, 1),   # P4, high priority
                (8, 1, 1),   # P5, high priority
            ],
            "Preemptive vs Non-preemptive SJF": [
                (0, 8, 1),
                (1, 4, 1),
                (2, 2, 1),
                (3, 1, 1),
            ],
        }

        processes = scenarios.get(selected_label)
        if not processes:
            return

        for arrival, burst, priority in processes:
            pid = f"P{self._next_pid}"
            self._next_pid += 1

            row_index = len(self.process_tree.get_children())
            tag = "evenrow" if row_index % 2 == 0 else "oddrow"

            self.process_tree.insert(
                "",
                "end",
                values=(pid, arrival, burst, priority),
                tags=(tag,),
            )

    def _get_processes_from_tree(self) -> List[Process]:
        """
        Convert the rows in the process Treeview into Process objects.

        This is the canonical source of truth for the simulator, so that
        any manual edits or row deletions are reflected correctly.
        """
        processes: List[Process] = []
        for item in self.process_tree.get_children():
            pid, arrival, burst, priority = self.process_tree.item(item, "values")
            processes.append(
                Process(
                    pid=str(pid),
                    arrival_time=int(arrival),
                    burst_time=int(burst),
                    priority=int(priority),
                )
            )
        return processes

    # ------------------------------------------------------------------#
    # Core scheduling helpers                                           #
    # ------------------------------------------------------------------#

    def _run_algorithm(
        self, algorithm: str, processes: List[Process], quantum: Optional[int] = None
    ) -> Tuple[List[ScheduleEntry], List[Dict[str, Any]]]:
        """Run a scheduling algorithm by key and return (schedule, stats)."""
        if algorithm == "FCFS":
            return fcfs_scheduling(processes)
        if algorithm == "SJF":
            return sjf_scheduling(processes)
        if algorithm == "SJF_PREEMPTIVE":
            return sjf_preemptive_scheduling(processes)
        if algorithm == "PRIORITY":
            return priority_scheduling(processes)
        if algorithm == "PRIORITY_PREEMPTIVE":
            return priority_preemptive_scheduling(processes)
        if algorithm == "RR":
            if quantum is None:
                raise ValueError("Time quantum is required for Round Robin.")
            return round_robin_scheduling(processes, quantum)
        raise ValueError(f"Unsupported algorithm key: {algorithm}")

    def _compute_aggregates(
        self,
        schedule: List[ScheduleEntry],
        stats: List[Dict[str, Any]],
    ) -> Dict[str, float]:
        """Compute aggregate metrics from a schedule and per-process stats."""
        if stats:
            total_waiting = sum(p["waiting_time"] for p in stats)
            total_turnaround = sum(p["turnaround_time"] for p in stats)
            avg_waiting = total_waiting / len(stats)
            avg_turnaround = total_turnaround / len(stats)
            min_waiting = min(p["waiting_time"] for p in stats)
            max_waiting = max(p["waiting_time"] for p in stats)
        else:
            avg_waiting = 0.0
            avg_turnaround = 0.0
            min_waiting = 0.0
            max_waiting = 0.0

        if schedule:
            total_time = max(entry["end"] for entry in schedule)
            busy_time = sum(
                entry["end"] - entry["start"]
                for entry in schedule
                if entry["pid"] is not None
            )
            cpu_utilization = (busy_time / total_time) if total_time > 0 else 0.0
            throughput = (len(stats) / total_time) if total_time > 0 else 0.0
        else:
            cpu_utilization = 0.0
            throughput = 0.0

        return {
            "avg_waiting": avg_waiting,
            "avg_turnaround": avg_turnaround,
            "min_waiting": min_waiting,
            "max_waiting": max_waiting,
            "cpu_utilization": cpu_utilization,
            "throughput": throughput,
        }

    def run_simulation(self) -> None:
        """Run the selected scheduling algorithm and update the GUI."""
        processes = self._get_processes_from_tree()
        if not processes:
            messagebox.showerror(
                "No processes",
                "Please add at least one process before running the simulation.",
            )
            return

        algorithm = self.algorithm_var.get()
        quantum: Optional[int] = None

        if algorithm == "RR":
            quantum_text = self.quantum_entry.get().strip()
            if not quantum_text:
                messagebox.showerror(
                    "Invalid quantum", "Please enter a time quantum for Round Robin."
                )
                return
            try:
                quantum = int(quantum_text)
            except ValueError:
                messagebox.showerror(
                    "Invalid quantum", "Time quantum must be a positive integer."
                )
                return

        try:
            schedule, stats = self._run_algorithm(algorithm, processes, quantum)
        except ValueError as exc:
            messagebox.showerror("Error", str(exc))
            return

        aggregates = self._compute_aggregates(schedule, stats)

        # Update the GUI with the new schedule and metrics.
        self._populate_results_table(
            stats, aggregates["avg_waiting"], aggregates["avg_turnaround"]
        )
        self._draw_gantt_chart(schedule)

        # Update the extra aggregate metrics label.
        if hasattr(self, "extra_metrics_label"):
            self.extra_metrics_label.configure(
                text=(
                    f"CPU Utilization: {aggregates['cpu_utilization'] * 100:.2f}%  |  "
                    f"Throughput: {aggregates['throughput']:.3f} proc/unit  |  "
                    f"Min Waiting: {aggregates['min_waiting']:.2f}  |  "
                    f"Max Waiting: {aggregates['max_waiting']:.2f}"
                )
            )

        # Initialize playback at time 0 and update label.
        self._playback_time = 0
        if hasattr(self, "playback_time_label"):
            self.playback_time_label.configure(text="Time: t = 0")

    def run_comparison(self) -> None:
        """Run all algorithms on the current process set and populate the comparison table."""
        processes = self._get_processes_from_tree()
        if not processes:
            messagebox.showerror(
                "No processes",
                "Please add at least one process before running the comparison.",
            )
            return

        # Determine quantum to use for RR in comparison.
        quantum: Optional[int] = None
        quantum_text = self.quantum_entry.get().strip()
        if quantum_text:
            try:
                quantum = int(quantum_text)
            except ValueError:
                messagebox.showerror(
                    "Invalid quantum",
                    "Time quantum must be a positive integer for Round Robin.",
                )
                return

        # Clear old comparison rows.
        self._comparison_algorithm_for_item.clear()
        for item in self.comparison_tree.get_children():
            self.comparison_tree.delete(item)

        # Use the mapping of labels -> keys to decide which algorithms to compare.
        for label, key in self._algorithm_display_to_key.items():
            try:
                schedule, stats = self._run_algorithm(key, processes, quantum)
            except ValueError:
                # Skip RR if quantum is invalid / missing.
                if key == "RR":
                    continue
                raise

            aggregates = self._compute_aggregates(schedule, stats)

            item_id = self.comparison_tree.insert(
                "",
                "end",
                values=(
                    label,
                    f"{aggregates['avg_waiting']:.2f}",
                    f"{aggregates['avg_turnaround']:.2f}",
                    f"{aggregates['cpu_utilization'] * 100:.2f}",
                    f"{aggregates['throughput']:.3f}",
                ),
            )
            self._comparison_algorithm_for_item[item_id] = key

    def _on_comparison_select(self, _event: tk.Event) -> None:
        """
        When a row in the comparison table is selected, rerun that algorithm
        and update the main Gantt chart and metrics table accordingly.
        """
        selection = self.comparison_tree.selection()
        if not selection:
            return

        item_id = selection[0]
        algorithm = self._comparison_algorithm_for_item.get(item_id)
        if not algorithm:
            return

        processes = self._get_processes_from_tree()
        if not processes:
            return

        quantum: Optional[int] = None
        if algorithm == "RR":
            quantum_text = self.quantum_entry.get().strip()
            if not quantum_text:
                messagebox.showerror(
                    "Invalid quantum",
                    "Please enter a time quantum for Round Robin before comparing.",
                )
                return
            try:
                quantum = int(quantum_text)
            except ValueError:
                messagebox.showerror(
                    "Invalid quantum", "Time quantum must be a positive integer."
                )
                return

        try:
            schedule, stats = self._run_algorithm(algorithm, processes, quantum)
        except ValueError as exc:
            messagebox.showerror("Error", str(exc))
            return

        aggregates = self._compute_aggregates(schedule, stats)

        # Update the GUI with the new schedule and metrics.
        self._populate_results_table(
            stats, aggregates["avg_waiting"], aggregates["avg_turnaround"]
        )
        self._draw_gantt_chart(schedule)

        if hasattr(self, "extra_metrics_label"):
            self.extra_metrics_label.configure(
                text=(
                    f"CPU Utilization: {aggregates['cpu_utilization'] * 100:.2f}%  |  "
                    f"Throughput: {aggregates['throughput']:.3f} proc/unit  |  "
                    f"Min Waiting: {aggregates['min_waiting']:.2f}  |  "
                    f"Max Waiting: {aggregates['max_waiting']:.2f}"
                )
            )

        self._playback_time = 0
        if hasattr(self, "playback_time_label"):
            self.playback_time_label.configure(text="Time: t = 0")

    def _populate_results_table(
        self,
        stats: List[Dict[str, Any]],
        avg_waiting: float,
        avg_turnaround: float,
    ) -> None:
        """Display per-process metrics and the overall average and per-process values."""
        # Clear existing rows.
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)

        # Insert new metrics rows (strictly sorted by PID for consistent display),
        # and apply alternating row colors to match the input table.
        for index, row in enumerate(sorted(stats, key=lambda r: r["pid"])):
            tag = "evenrow" if index % 2 == 0 else "oddrow"
            self.results_tree.insert(
                "",
                "end",
                values=(
                    row["pid"],
                    row["arrival_time"],
                    row["burst_time"],
                    row["priority"],
                    row["completion_time"],
                    row["turnaround_time"],
                    row["waiting_time"],
                ),
                tags=(tag,),
            )

        self.avg_waiting_label.configure(
            text=f"Average Waiting Time: {avg_waiting:.2f}"
        )
        self.avg_turnaround_label.configure(
            text=f"Average Turnaround Time: {avg_turnaround:.2f}"
        )

    def _draw_gantt_chart(self, schedule: List[ScheduleEntry]) -> None:
        """
        Draw the Gantt chart on the Canvas.

        Each schedule entry is drawn as a rectangle whose width is
        proportional to its duration. Different processes are shown in
        different colors; idle time (no process running) is shown in gray.

        The currently selected PID (if any) is emphasized with a thicker
        border and slightly brighter rectangle.
        """
        # Remember the last schedule so selection changes can trigger a redraw.
        self._current_schedule = list(schedule)

        self.gantt_canvas.delete("all")

        if not schedule:
            self.gantt_canvas.create_text(
                10,
                10,
                anchor="nw",
                text="No schedule to display.",
                fill="#E5E7EB",
                font=("Segoe UI", 10),
            )
            return

        # Determine total time span to scale the chart horizontally.
        total_time = max(entry["end"] for entry in schedule)
        if total_time <= 0:
            return

        canvas_width = int(self.gantt_canvas.winfo_width())
        if canvas_width <= 1:
            # If the canvas has not been fully laid out yet, fall back to a default width.
            canvas_width = 800

        canvas_height = int(self.gantt_canvas.winfo_height())
        if canvas_height <= 1:
            canvas_height = 180

        left_margin = 20
        right_margin = 20
        top_margin = 30
        bar_height = 50

        usable_width = max(1, canvas_width - left_margin - right_margin)
        time_scale = usable_width / float(total_time)

        bar_top = top_margin
        bar_bottom = bar_top + bar_height

        # Color palette for processes (bright accents on dark background).
        color_palette = [
            "#22C55E",  # emerald
            "#3B82F6",  # blue
            "#EAB308",  # amber
            "#EC4899",  # pink
            "#F97316",  # orange
            "#8B5CF6",  # violet
            "#06B6D4",  # cyan
            "#FACC15",  # yellow
            "#EF4444",  # red
            "#14B8A6",  # teal
        ]
        pid_to_color: Dict[str, str] = {}
        next_color_index = 0

        label_font = ("Segoe UI", 9)
        tick_font = ("Segoe UI", 8)

        # Draw each scheduled segment.
        for entry in schedule:
            start = entry["start"]
            end = entry["end"]
            if end <= start:
                continue  # zero-length segment, nothing to draw

            x1 = left_margin + start * time_scale
            x2 = left_margin + end * time_scale

            pid = entry["pid"]
            if pid is None:
                # Idle time.
                fill_color = "#4B5563"
                label = "Idle"
            else:
                if pid not in pid_to_color:
                    pid_to_color[pid] = color_palette[next_color_index % len(color_palette)]
                    next_color_index += 1
                fill_color = pid_to_color[pid]
                label = pid

            # Rectangle representing the CPU execution interval.
            self.gantt_canvas.create_rectangle(
                x1,
                bar_top,
                x2,
                bar_bottom,
                fill=fill_color,
                outline="#111827",
            )

            # Text label in the middle of the rectangle.
            self.gantt_canvas.create_text(
                (x1 + x2) / 2,
                (bar_top + bar_bottom) / 2,
                text=label,
                font=label_font,
                fill="#F9FAFB",
            )

            # Time tick at the start of the segment.
            self.gantt_canvas.create_line(
                x1, bar_bottom, x1, bar_bottom + 5, fill="#4B5563"
            )
            self.gantt_canvas.create_text(
                x1,
                bar_bottom + 7,
                text=str(start),
                anchor="n",
                font=tick_font,
                fill="#D1D5DB",
            )

        # Time tick at the final end time.
        final_x = left_margin + total_time * time_scale
        self.gantt_canvas.create_line(
            final_x, bar_bottom, final_x, bar_bottom + 5, fill="#4B5563"
        )
        self.gantt_canvas.create_text(
            final_x,
            bar_bottom + 7,
            text=str(total_time),
            anchor="n",
            font=tick_font,
            fill="#D1D5DB",
        )

    # ------------------------------------------------------------------#
    # Mainloop                                                          #
    # ------------------------------------------------------------------#

    def run(self) -> None:
        """Start the Tkinter main event loop."""
        self.root.mainloop()


def main() -> None:
    """Entry point when running this module as a script."""
    app = CPUSchedulerApp()
    app.run()


if __name__ == "__main__":
    main()
