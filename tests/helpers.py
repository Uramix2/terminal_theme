"""Terminate an isolated tmux server and wait for its shells to finish writing."""
from pathlib import Path
import subprocess
import time


def stop_tmux(command):
    result = subprocess.run(command+['list-panes','-a','-F','#{pane_pid}'],capture_output=True,text=True)
    pids = [int(row) for row in result.stdout.splitlines() if row.isdigit()]
    subprocess.run(command+['kill-server'],capture_output=True)
    deadline = time.monotonic()+5
    while pids:
        alive = []
        for pid in pids:
            try:
                # Zombies have completed their file writes; their parent reaps them later.
                state = (Path('/proc')/str(pid)/'stat').read_text().rsplit(')',1)[1].split()[0]
                if state != 'Z': alive.append(pid)
            except FileNotFoundError:
                pass
        if not alive: return
        if time.monotonic() >= deadline:
            raise RuntimeError(f'Test tmux shells did not exit: {alive}')
        pids = alive
        time.sleep(0.02)
