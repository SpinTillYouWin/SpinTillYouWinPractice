import gradio as gr
import pandas as pd
import json
from itertools import combinations
import random
from roulette_data import (
    EVEN_MONEY, DOZENS, COLUMNS, STREETS, CORNERS, SIX_LINES, SPLITS,
    NEIGHBORS_EUROPEAN, LEFT_OF_ZERO_EUROPEAN, RIGHT_OF_ZERO_EUROPEAN
)
def update_scores_batch(spins):
    """Update scores for a batch of spins and return actions for undo."""
    action_log = []
    for spin in spins:
        spin_value = int(spin)
        action = {"spin": spin_value, "increments": {}}

        # Update even money scores
        for name, numbers in EVEN_MONEY.items():
            if spin_value in numbers:
                state.even_money_scores[name] += 1
                action["increments"].setdefault("even_money_scores", {})[name] = 1

        # Update dozens scores
        for name, numbers in DOZENS.items():
            if spin_value in numbers:
                state.dozen_scores[name] += 1
                action["increments"].setdefault("dozen_scores", {})[name] = 1

        # Update columns scores
        for name, numbers in COLUMNS.items():
            if spin_value in numbers:
                state.column_scores[name] += 1
                action["increments"].setdefault("column_scores", {})[name] = 1

        # Update streets scores
        for name, numbers in STREETS.items():
            if spin_value in numbers:
                state.street_scores[name] += 1
                action["increments"].setdefault("street_scores", {})[name] = 1

        # Update corners scores
        for name, numbers in CORNERS.items():
            if spin_value in numbers:
                state.corner_scores[name] += 1
                action["increments"].setdefault("corner_scores", {})[name] = 1

        # Update six lines scores
        for name, numbers in SIX_LINES.items():
            if spin_value in numbers:
                state.six_line_scores[name] += 1
                action["increments"].setdefault("six_line_scores", {})[name] = 1

        # Update splits scores
        for name, numbers in SPLITS.items():
            if spin_value in numbers:
                state.split_scores[name] += 1
                action["increments"].setdefault("split_scores", {})[name] = 1

        # Update straight-up scores
        state.scores[spin_value] += 1
        action["increments"].setdefault("scores", {})[spin_value] = 1

        # Update side scores
        if str(spin_value) in [str(x) for x in current_left_of_zero]:
            state.side_scores["Left Side of Zero"] += 1
            action["increments"].setdefault("side_scores", {})["Left Side of Zero"] = 1
        if str(spin_value) in [str(x) for x in current_right_of_zero]:
            state.side_scores["Right Side of Zero"] += 1
            action["increments"].setdefault("side_scores", {})["Right Side of Zero"] = 1

        action_log.append(action)
    return action_log

    
def validate_roulette_data():
    """Validate that all required constants from roulette_data.py are present and correctly formatted."""
    required_dicts = {
        "EVEN_MONEY": EVEN_MONEY,
        "DOZENS": DOZENS,
        "COLUMNS": COLUMNS,
        "STREETS": STREETS,
        "CORNERS": CORNERS,
        "SIX_LINES": SIX_LINES,
        "SPLITS": SPLITS
    }
    required_neighbors = {
        "NEIGHBORS_EUROPEAN": NEIGHBORS_EUROPEAN,
        "LEFT_OF_ZERO_EUROPEAN": LEFT_OF_ZERO_EUROPEAN,
        "RIGHT_OF_ZERO_EUROPEAN": RIGHT_OF_ZERO_EUROPEAN
    }

    errors = []

    # Check betting category dictionaries
    for name, data in required_dicts.items():
        if not isinstance(data, dict):
            errors.append(f"{name} must be a dictionary.")
            continue
        for key, value in data.items():
            if not isinstance(key, str) or not isinstance(value, (list, set, tuple)) or not all(isinstance(n, int) for n in value):
                errors.append(f"{name}['{key}'] must map to a list/set/tuple of integers.")

    # Check neighbor data
    for name, data in required_neighbors.items():
        if name == "NEIGHBORS_EUROPEAN":
            if not isinstance(data, dict):
                errors.append(f"{name} must be a dictionary.")
                continue
            for key, value in data.items():
                if not isinstance(key, int) or not isinstance(value, tuple) or len(value) != 2 or not all(isinstance(n, (int, type(None))) for n in value):
                    errors.append(f"{name}['{key}'] must map to a tuple of two integers or None.")
        else:
            if not isinstance(data, (list, set, tuple)) or not all(isinstance(n, int) for n in data):
                errors.append(f"{name} must be a list/set/tuple of integers.")

    return errors if errors else None

class RouletteState:
    def __init__(self):
        self.scores = {n: 0 for n in range(37)}
        self.even_money_scores = {name: 0 for name in EVEN_MONEY.keys()}
        self.dozen_scores = {name: 0 for name in DOZENS.keys()}
        self.column_scores = {name: 0 for name in COLUMNS.keys()}
        self.street_scores = {name: 0 for name in STREETS.keys()}
        self.corner_scores = {name: 0 for name in CORNERS.keys()}
        self.six_line_scores = {name: 0 for name in SIX_LINES.keys()}
        self.split_scores = {name: 0 for name in SPLITS.keys()}
        self.side_scores = {"Left Side of Zero": 0, "Right Side of Zero": 0}
        self.selected_numbers = set()
        self.last_spins = []
        self.spin_history = []  # Tracks each spin's effects for undoing

        # Casino data storage
        self.casino_data = {
            "spins_count": 100,  # Default number of spins
            "hot_numbers": {},   # {number: percentage, e.g., 5: 10.0}
            "cold_numbers": {},  # {number: percentage, e.g., 0: 0.0}
            "even_odd": {"Even": 0.0, "Odd": 0.0},
            "red_black": {"Red": 0.0, "Black": 0.0},
            "low_high": {"Low": 0.0, "High": 0.0},
            "dozens": {"1st Dozen": 0.0, "2nd Dozen": 0.0, "3rd Dozen": 0.0},
            "columns": {"1st Column": 0.0, "2nd Column": 0.0, "3rd Column": 0.0}
        }
        self.use_casino_winners = False  # Toggle to highlight casino winners

        # New betting progression fields
        self.bankroll = 1000
        self.initial_bankroll = 1000  # For profit/loss tracking
        self.base_unit = 10
        self.stop_loss = -500  # Relative to initial_bankroll
        self.stop_win = 200    # Relative to initial_bankroll
        self.bet_type = "Even Money"
        self.progression = "Martingale"
        self.current_bet = self.base_unit
        self.next_bet = self.base_unit
        self.progression_state = None  # e.g., Fibonacci index or Labouchere list
        self.is_stopped = False
        self.message = f"Start with base bet of {self.base_unit} on {self.bet_type} ({self.progression})"
        self.status = "Active"
        self.status_color = "white"  # Default color for active status

    def reset(self):
        self.scores = {n: 0 for n in range(37)}
        self.even_money_scores = {name: 0 for name in EVEN_MONEY.keys()}
        self.dozen_scores = {name: 0 for name in DOZENS.keys()}
        self.column_scores = {name: 0 for name in COLUMNS.keys()}
        self.street_scores = {name: 0 for name in STREETS.keys()}
        self.corner_scores = {name: 0 for name in CORNERS.keys()}
        self.six_line_scores = {name: 0 for name in SIX_LINES.keys()}
        self.split_scores = {name: 0 for name in SPLITS.keys()}
        self.side_scores = {"Left Side of Zero": 0, "Right Side of Zero": 0}
        self.selected_numbers = set(int(s) for s in self.last_spins if s.isdigit())
        self.last_spins = []
        self.spin_history = []

        # Reset betting progression (optional: only if you want full reset to affect progression)
        # self.reset_progression()

    def reset_progression(self):
        self.current_bet = self.base_unit
        self.next_bet = self.base_unit
        self.progression_state = None
        self.is_stopped = False
        self.message = f"Progression reset. Start with base bet of {self.base_unit} on {self.bet_type} ({self.progression})"
        self.status = "Active"
        return self.bankroll, self.current_bet, self.next_bet, self.message, self.status

    def update_bankroll(self, won):
        payout = {"Even Money": 1, "Dozens": 2, "Columns": 2, "Straight Bets": 35}[self.bet_type]
        if won:
            self.bankroll += self.current_bet * payout
        else:
            self.bankroll -= self.current_bet
        profit = self.bankroll - self.initial_bankroll
        if profit <= self.stop_loss:
            self.is_stopped = True
            self.status = f"Stopped: Hit Stop Loss of {self.stop_loss}"
            self.status_color = "red"  # Red for stop loss
        elif profit >= self.stop_win:
            self.is_stopped = True
            self.status = f"Stopped: Hit Stop Win of {self.stop_win}"
            self.status_color = "green"  # Green for stop win
        else:
            self.status_color = "white"  # Neutral when active

    def update_progression(self, won):
        if self.is_stopped:
            return self.bankroll, self.current_bet, self.next_bet, self.message, self.status, self.status_color
        self.update_bankroll(won)
        if self.bankroll < self.current_bet:
            self.is_stopped = True
            self.status = "Stopped: Insufficient bankroll"
            self.status_color = "red"  # Red for insufficient bankroll
            self.message = "Cannot continue: Bankroll too low."
            return self.bankroll, self.current_bet, self.next_bet, self.message, self.status, self.status_color
    
        if self.progression == "Martingale":
            self.current_bet = self.next_bet
            self.next_bet = self.base_unit if won else self.current_bet * 2
            self.message = f"{'Win' if won else 'Loss'}! Next bet: {self.next_bet}"
        elif self.progression == "Fibonacci":
            fib = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55]
            if self.progression_state is None:
                self.progression_state = 0
            self.current_bet = self.next_bet
            if won:
                self.progression_state = max(0, self.progression_state - 2)
                self.next_bet = fib[self.progression_state] * self.base_unit
                self.message = f"Win! Move back to {self.next_bet}"
            else:
                self.progression_state = min(len(fib) - 1, self.progression_state + 1)
                self.next_bet = fib[self.progression_state] * self.base_unit
                self.message = f"Loss! Next Fibonacci bet: {self.next_bet}"
        elif self.progression == "Triple Martingale":
            self.current_bet = self.next_bet
            self.next_bet = self.base_unit if won else self.current_bet * 3
            self.message = f"{'Win' if won else 'Loss'}! Next bet: {self.next_bet}"
        elif self.progression == "Oscar’s Grind":
            self.current_bet = self.next_bet
            profit = self.bankroll - self.initial_bankroll
            if won and profit > 0:
                self.next_bet = self.base_unit
                self.message = f"Win! Profit achieved, reset to {self.next_bet}"
            elif won:
                self.next_bet = self.current_bet + self.base_unit
                self.message = f"Win! Increase to {self.next_bet}"
            else:
                self.next_bet = self.current_bet
                self.message = f"Loss! Keep bet at {self.next_bet}"
        elif self.progression == "Labouchere":
            if self.progression_state is None:
                self.progression_state = [1, 2, 3, 4]  # Default, updated by UI
            self.current_bet = self.next_bet
            if won and len(self.progression_state) > 1:
                self.progression_state.pop(0)
                self.progression_state.pop(-1)
                self.next_bet = (self.progression_state[0] + self.progression_state[-1]) * self.base_unit if len(self.progression_state) > 1 else self.progression_state[0] * self.base_unit if self.progression_state else self.base_unit
                self.message = f"Win! Next bet: {self.next_bet} (Sequence: {self.progression_state})"
            elif won:
                self.next_bet = self.base_unit
                self.message = f"Win! Sequence complete, reset to {self.next_bet}"
            else:
                self.progression_state.append(self.current_bet // self.base_unit)
                self.next_bet = (self.progression_state[0] + self.progression_state[-1]) * self.base_unit
                self.message = f"Loss! Next bet: {self.next_bet} (Sequence: {self.progression_state})"
        elif self.progression == "Ladder":
            self.current_bet = self.next_bet
            self.next_bet = self.base_unit if won else self.current_bet + self.base_unit
            self.message = f"{'Win' if won else 'Loss'}! Next bet: {self.next_bet}"
        elif self.progression == "D’Alembert":
            self.current_bet = self.next_bet
            self.next_bet = max(self.base_unit, self.current_bet - self.base_unit) if won else self.current_bet + self.base_unit
            self.message = f"{'Win' if won else 'Loss'}! Next bet: {self.next_bet}"
        elif self.progression == "Double After a Win":
            self.current_bet = self.next_bet
            self.next_bet = self.current_bet * 2 if won else self.base_unit
            self.message = f"{'Win' if won else 'Loss'}! Next bet: {self.next_bet}"
        elif self.progression == "+1 Win / -1 Loss":
            self.current_bet = self.next_bet
            self.next_bet = self.current_bet + self.base_unit if won else max(self.base_unit, self.current_bet - self.base_unit)
            self.message = f"{'Win' if won else 'Loss'}! Next bet: {self.next_bet}"
        elif self.progression == "+2 Win / -1 Loss":
            self.current_bet = self.next_bet
            self.next_bet = self.current_bet + (2 * self.base_unit) if won else max(self.base_unit, self.current_bet - self.base_unit)
            self.message = f"{'Win' if won else 'Loss'}! Next bet: {self.next_bet}"
    
        return self.bankroll, self.current_bet, self.next_bet, self.message, self.status, self.status_color

# Create an instance of RouletteState (unchanged)
state = RouletteState()

# Validate roulette data at startup
data_errors = validate_roulette_data()
if data_errors:
    raise RuntimeError("Roulette data validation failed:\n" + "\n".join(data_errors))

current_table_type = "European"
current_neighbors = NEIGHBORS_EUROPEAN
current_left_of_zero = LEFT_OF_ZERO_EUROPEAN
current_right_of_zero = RIGHT_OF_ZERO_EUROPEAN

# Global scores dictionaries
scores = {n: 0 for n in range(37)}
even_money_scores = {name: 0 for name in EVEN_MONEY.keys()}
dozen_scores = {name: 0 for name in DOZENS.keys()}
column_scores = {name: 0 for name in COLUMNS.keys()}
street_scores = {name: 0 for name in STREETS.keys()}
corner_scores = {name: 0 for name in CORNERS.keys()}
six_line_scores = {name: 0 for name in SIX_LINES.keys()}
split_scores = {name: 0 for name in SPLITS.keys()}
side_scores = {"Left Side of Zero": 0, "Right Side of Zero": 0}
selected_numbers = set()

last_spins = []

colors = {
    "0": "green",
    "1": "red", "3": "red", "5": "red", "7": "red", "9": "red", "12": "red",
    "14": "red", "16": "red", "18": "red", "19": "red", "21": "red", "23": "red",
    "25": "red", "27": "red", "30": "red", "32": "red", "34": "red", "36": "red",
    "2": "black", "4": "black", "6": "black", "8": "black", "10": "black", "11": "black",
    "13": "black", "15": "black", "17": "black", "20": "black", "22": "black", "24": "black",
    "26": "black", "28": "black", "29": "black", "31": "black", "33": "black", "35": "black"
}


def format_spins_as_html(spins, num_to_show):
    if not spins:
        return "<h4>Last Spins</h4><p>No spins yet.</p>"
    
    # Split the spins string into a list and reverse to get the most recent first
    spin_list = spins.split(", ") if spins else []
    spin_list = spin_list[-int(num_to_show):] if spin_list else []  # Take the last N spins
    
    if not spin_list:
        return "<h4>Last Spins</h4><p>No spins yet.</p>"
    
    # Define colors for each number (matching the European Roulette Table)
    colors = {
        "0": "green",
        "1": "red", "3": "red", "5": "red", "7": "red", "9": "red", "12": "red", "14": "red", "16": "red", "18": "red",
        "19": "red", "21": "red", "23": "red", "25": "red", "27": "red", "30": "red", "32": "red", "34": "red", "36": "red",
        "2": "black", "4": "black", "6": "black", "8": "black", "10": "black", "11": "black", "13": "black", "15": "black", "17": "black",
        "20": "black", "22": "black", "24": "black", "26": "black", "28": "black", "29": "black", "31": "black", "33": "black", "35": "black"
    }
    
    # Format each spin as a colored span
    html_spins = []
    for spin in spin_list:
        color = colors.get(spin.strip(), "black")  # Default to black if not found
        html_spins.append(f'<span style="background-color: {color}; color: white; padding: 2px 5px; margin: 2px; border-radius: 3px; display: inline-block;">{spin}</span>')
    
    # Wrap the spins in a div with flexbox to enable wrapping, and add a title
    return f'<h4 style="margin-bottom: 5px;">Last Spins</h4><div style="display: flex; flex-wrap: wrap; gap: 5px;">{"".join(html_spins)}</div>'

# Line 1 (start of updated function)
def add_spin(number, current_spins, num_to_show):
    print(f"add_spin: number='{number}', current_spins='{current_spins}'")
    spins = current_spins.split(", ") if current_spins else []
    if spins == [""]:
        spins = []

    # Split input on commas and process each number
    numbers = [n.strip() for n in number.split(",") if n.strip()]
    if not numbers:
        gr.Warning("No valid input provided. Please enter numbers between 0 and 36.")
        return current_spins, current_spins, "<h4>Last Spins</h4><p>Error: No valid numbers provided.</p>", update_spin_counter(), "<h4>Wheel Section Balance</h4><p>No spins yet to compare left and right sides.</p>"

    errors = []
    valid_spins = []
    for num_str in numbers:
        try:
            num = int(num_str)
            if not (0 <= num <= 36):
                errors.append(f"'{num_str}' is out of range (0-36)")
                continue
            valid_spins.append(num_str)
        except ValueError:
            errors.append(f"'{num_str}' is not a number")
            continue

    if not valid_spins:
        error_msg = "Some inputs failed:\n- " + "\n- ".join(errors)
        gr.Warning(error_msg)
        print(f"add_spin: Errors encountered - {error_msg}")
        return current_spins, current_spins, f"<h4>Last Spins</h4><p>{error_msg}</p>", update_spin_counter(), "<h4>Wheel Section Balance</h4><p>No spins yet to compare left and right sides.</p>"

    # Debug: Log side scores before update
    print(f"add_spin: Before update - side_scores = {state.side_scores}")

    # Batch update scores
    action_log = update_scores_batch(valid_spins)

    # Update state with new spins
    new_spins = spins.copy()
    state.selected_numbers.clear()  # Clear before rebuilding
    for num_str in valid_spins:
        num = int(num_str)
        new_spins.append(str(num))
        state.selected_numbers.add(num)
        state.last_spins.append(str(num))
        state.spin_history.append(action_log.pop(0))
        # Limit spin history to 100 spins
        if len(state.spin_history) > 100:
            state.spin_history.pop(0)
    state.selected_numbers = set(int(s) for s in state.last_spins if s.isdigit())  # Sync with last_spins

    new_spins_str = ", ".join(new_spins)
    if errors:
        error_msg = "Some inputs failed:\n- " + "\n- ".join(errors)
        gr.Warning(error_msg)
        print(f"add_spin: Errors encountered - {error_msg}")
        return new_spins_str, new_spins_str, f"<h4>Last Spins</h4><p>{error_msg}</p>", update_spin_counter(), "<h4>Wheel Section Balance</h4><p>Some inputs failed.</p>"

    # Debug: Log side scores after update
    print(f"add_spin: After update - side_scores = {state.side_scores}, valid_spins = {valid_spins}")

    print(f"add_spin: new_spins='{new_spins_str}'")
    return new_spins_str, new_spins_str, format_spins_as_html(new_spins_str, num_to_show), update_spin_counter(), create_wheel_balance_bar()

    print(f"add_spin: new_spins='{new_spins_str}'")
    return new_spins_str, new_spins_str, format_spins_as_html(new_spins_str, num_to_show), update_spin_counter(), create_wheel_balance_bar()

    # Batch update scores
    action_log = update_scores_batch(valid_spins)

    # Update state with new spins
    new_spins = spins.copy()
    state.selected_numbers.clear()  # Clear before rebuilding
    for num_str in valid_spins:
        num = int(num_str)
        new_spins.append(str(num))
        state.selected_numbers.add(num)
        state.last_spins.append(str(num))
        state.spin_history.append(action_log.pop(0))
        # Limit spin history to 100 spins
        if len(state.spin_history) > 100:
            state.spin_history.pop(0)
    state.selected_numbers = set(int(s) for s in state.last_spins if s.isdigit())  # Sync with last_spins

    new_spins_str = ", ".join(new_spins)
    if errors:
        error_msg = "Some inputs failed:\n- " + "\n- ".join(errors)
        gr.Warning(error_msg)
        print(f"add_spin: Errors encountered - {error_msg}")
        return new_spins_str, new_spins_str, f"<h4>Last Spins</h4><p>{error_msg}</p>", update_spin_counter()

    print(f"add_spin: new_spins='{new_spins_str}'")
    return new_spins_str, new_spins_str, format_spins_as_html(new_spins_str, num_to_show), update_spin_counter()
    
# Function to clear spins
def clear_spins():
    state.selected_numbers.clear()
    state.last_spins = []
    return "", "", "Spins cleared successfully!", "", update_spin_counter()

# Function to save the session
def save_session():
    session_data = {
        "spins": state.last_spins,
        "spin_history": state.spin_history,  # Include spin history
        "scores": state.scores,
        "even_money_scores": state.even_money_scores,
        "dozen_scores": state.dozen_scores,
        "column_scores": state.column_scores,
        "street_scores": state.street_scores,
        "corner_scores": state.corner_scores,
        "six_line_scores": state.six_line_scores,
        "split_scores": state.split_scores,
        "side_scores": state.side_scores,
        "casino_data": state.casino_data,
        "use_casino_winners": state.use_casino_winners
    }
    with open("session.json", "w") as f:
        json.dump(session_data, f)
    return "session.json"

# Function to load the session
def load_session(file, strategy_name, neighbours_count, strong_numbers_count, *checkbox_args):
    try:
        if file is None:
            return ("", "", "Please upload a session file to load.", "", "", "", "", "", "", "", "", "", "", "", create_dynamic_table(strategy_name, neighbours_count, strong_numbers_count), "")

        with open(file.name, "r") as f:
            session_data = json.load(f)

        # Load state data
        state.last_spins = session_data.get("spins", [])
        state.spin_history = session_data.get("spin_history", [])
        state.scores = session_data.get("scores", {n: 0 for n in range(37)})
        state.even_money_scores = session_data.get("even_money_scores", {name: 0 for name in EVEN_MONEY.keys()})
        state.dozen_scores = session_data.get("dozen_scores", {name: 0 for name in DOZENS.keys()})
        state.column_scores = session_data.get("column_scores", {name: 0 for name in COLUMNS.keys()})
        state.street_scores = session_data.get("street_scores", {name: 0 for name in STREETS.keys()})
        state.corner_scores = session_data.get("corner_scores", {name: 0 for name in CORNERS.keys()})
        state.six_line_scores = session_data.get("six_line_scores", {name: 0 for name in SIX_LINES.keys()})
        state.split_scores = session_data.get("split_scores", {name: 0 for name in SPLITS.keys()})
        state.side_scores = session_data.get("side_scores", {"Left Side of Zero": 0, "Right Side of Zero": 0})
        state.casino_data = session_data.get("casino_data", {
            "spins_count": 100,
            "hot_numbers": {},
            "cold_numbers": {},
            "even_odd": {"Even": 0.0, "Odd": 0.0},
            "red_black": {"Red": 0.0, "Black": 0.0},
            "low_high": {"Low": 0.0, "High": 0.0},
            "dozens": {"1st Dozen": 0.0, "2nd Dozen": 0.0, "3rd Dozen": 0.0},
            "columns": {"1st Column": 0.0, "2nd Column": 0.0, "3rd Column": 0.0}
        })
        state.use_casino_winners = session_data.get("use_casino_winners", False)

        new_spins = ", ".join(state.last_spins)
        spin_analysis_output = f"Session loaded successfully with {len(state.last_spins)} spins."
        
        # Compute UI outputs
        even_money_output = "Even Money Bets:\n" + "\n".join(f"{name}: {score}" for name, score in state.even_money_scores.items())
        dozens_output = "Dozens:\n" + "\n".join(f"{name}: {score}" for name, score in state.dozen_scores.items())
        columns_output = "Columns:\n" + "\n".join(f"{name}: {score}" for name, score in state.column_scores.items())
        streets_output = "Streets:\n" + "\n".join(f"{name}: {score}" for name, score in state.street_scores.items() if score > 0)
        corners_output = "Corners:\n" + "\n".join(f"{name}: {score}" for name, score in state.corner_scores.items() if score > 0)
        six_lines_output = "Double Streets:\n" + "\n".join(f"{name}: {score}" for name, score in state.six_line_scores.items() if score > 0)
        splits_output = "Splits:\n" + "\n".join(f"{name}: {score}" for name, score in state.split_scores.items() if score > 0)
        sides_output = "Sides of Zero:\n" + "\n".join(f"{name}: {score}" for name, score in state.side_scores.items())

        straight_up_df = pd.DataFrame(list(state.scores.items()), columns=["Number", "Score"])
        straight_up_df = straight_up_df[straight_up_df["Score"] > 0].sort_values(by="Score", ascending=False)
        straight_up_df["Left Neighbor"] = straight_up_df["Number"].apply(lambda x: current_neighbors[x][0] if x in current_neighbors else "")
        straight_up_df["Right Neighbor"] = straight_up_df["Number"].apply(lambda x: current_neighbors[x][1] if x in current_neighbors else "")
        straight_up_html = create_html_table(straight_up_df[["Number", "Left Neighbor", "Right Neighbor", "Score"]], "Strongest Numbers")

        top_18_df = straight_up_df.head(18).sort_values(by="Number", ascending=True)
        numbers = top_18_df["Number"].tolist()
        if len(numbers) < 18:
            numbers.extend([""] * (18 - len(numbers)))
        grid_data = [numbers[i::3] for i in range(3)]
        top_18_html = "<h3>Top 18 Strongest Numbers (Sorted Lowest to Highest)</h3>"
        top_18_html += '<table border="1" style="border-collapse: collapse; text-align: center;">'
        for row in grid_data:
            top_18_html += "<tr>"
            for num in row:
                top_18_html += f'<td style="padding: 5px; width: 40px;">{num}</td>'
            top_18_html += "</tr>"
        top_18_html += "</table>"

        strongest_numbers_output = get_strongest_numbers_with_neighbors(3)
        dynamic_table_html = create_dynamic_table(strategy_name, neighbours_count, strong_numbers_count)
        strategy_output = show_strategy_recommendations(strategy_name, neighbours_count, strong_numbers_count, *checkbox_args)

        return (new_spins, new_spins, spin_analysis_output, even_money_output, dozens_output, columns_output,
                streets_output, corners_output, six_lines_output, splits_output, sides_output,
                straight_up_html, top_18_html, strongest_numbers_output, dynamic_table_html, strategy_output)
    except FileNotFoundError:
        return ("", "", f"Error: The file '{file.name if file else 'unknown'}' was not found.", "", "", "", "", "", "", "", "", "", "", "", create_dynamic_table(strategy_name, neighbours_count, strong_numbers_count), "")
    except json.JSONDecodeError:
        return ("", "", "Error: The session file is corrupted or not valid JSON. Please upload a valid file.", "", "", "", "", "", "", "", "", "", "", "", create_dynamic_table(strategy_name, neighbours_count, strong_numbers_count), "")
    except Exception as e:
        return ("", "", f"Unexpected error loading session: {str(e)}. Please try again or check the file.", "", "", "", "", "", "", "", "", "", "", "", create_dynamic_table(strategy_name, neighbours_count, strong_numbers_count), "")

# Function to calculate statistical insights
def statistical_insights():
    if not state.last_spins:
        return "No spins to analyze yet—click some numbers first!"
    total_spins = len(state.last_spins)
    number_freq = {num: state.scores[num] for num in state.scores if state.scores[num] > 0}
    top_numbers = sorted(number_freq.items(), key=lambda x: x[1], reverse=True)[:5]
    output = [f"Total Spins: {total_spins}"]
    output.append("Top 5 Numbers by Hits:")
    for num, hits in top_numbers:
        output.append(f"Number {num}: {hits} hits")
    return "\n".join(output)

# Function to create HTML table (used in analyze_spins)
def create_html_table(df, title):
    if df.empty:
        return f"<h3>{title}</h3><p>No data to display.</p>"
    html = f"<h3>{title}</h3>"
    html += '<table border="1" style="border-collapse: collapse; text-align: center;">'
    html += "<tr>" + "".join(f"<th>{col}</th>" for col in df.columns) + "</tr>"
    for _, row in df.iterrows():
        html += "<tr>" + "".join(f"<td>{val}</td>" for val in row) + "</tr>"
    html += "</table>"
    return html
# New code (inserted after create_html_table)
def create_wheel_balance_bar():
    """Generate a horizontal bar showing Left vs Right Side of Zero hit balance."""
    left_score = state.side_scores.get("Left Side of Zero", 0)
    right_score = state.side_scores.get("Right Side of Zero", 0)
    
    if left_score == 0 and right_score == 0:
        return "<h4>Wheel Section Balance</h4><p>No spins yet to compare left and right sides.</p>"
    
    # Calculate balance: positive = left dominates, negative = right dominates
    balance = left_score - right_score
    max_range = max(left_score + right_score, 10)  # Avoid division by zero, min range 10
    normalized = balance / max_range * 100  # Scale to -100 (full right) to +100 (full left)
    
    # Bar styling
    bar_width = 300  # Total width in pixels
    bar_height = 20  # Height of the bar
    left_width = max(0, min(150, 150 * (normalized / 100))) if normalized > 0 else 0
    right_width = max(0, min(150, 150 * (-normalized / 100))) if normalized < 0 else 0
    
    html = f"""
    <h4 style='margin-bottom: 5px;'>Wheel Section Balance</h4>
    <div style='width: {bar_width}px; height: {bar_height + 30}px; font-family: Arial, sans-serif; position: relative;'>
        <div style='width: 100%; height: {bar_height}px; background-color: #f0f0f0; position: relative;'>
            <div style='width: {left_width}px; height: 100%; background: linear-gradient(to right, #4682B4, #87CEEB); position: absolute; left: 50%; transform: translateX(-100%);'></div>
            <div style='width: {right_width}px; height: 100%; background: linear-gradient(to left, #FF6347, #FFA07A); position: absolute; left: 50%;'></div>
            <div style='width: 2px; height: 100%; background-color: black; position: absolute; left: 50%;'></div>
        </div>
        <div style='position: absolute; top: {bar_height + 5}px; left: 0; font-size: 12px;'>Left: {left_score}</div>
        <div style='position: absolute; top: {bar_height + 5}px; right: 0; font-size: 12px;'>Right: {right_score}</div>
    </div>
    <p style='font-size: 12px; text-align: center; margin-top: 5px;'>
        {'Left side is hotter' if balance > 0 else 'Right side is hotter' if balance < 0 else 'Balanced'}
    </p>
    """
    return html
def create_strongest_numbers_with_neighbours_table():
    straight_up_df = pd.DataFrame(list(state.scores.items()), columns=["Number", "Score"])
    straight_up_df = straight_up_df[straight_up_df["Score"] > 0].sort_values(by="Score", ascending=False)

    if straight_up_df.empty:
        return "<h3>Strongest Numbers with Neighbours</h3><p>No numbers have hit yet.</p>"

    # Create the HTML table
    table_html = '<table border="1" style="border-collapse: collapse; text-align: center; font-family: Arial, sans-serif;">'
    table_html += "<tr><th>Hit</th><th>Left N.</th><th>Right N.</th><th>Score</th></tr>"  # Table header
    for _, row in straight_up_df.iterrows():
        num = str(row["Number"])
        left, right = current_neighbors.get(row["Number"], ("", ""))
        left = str(left) if left is not None else ""
        right = str(right) if right is not None else ""
        score = row["Score"]
        table_html += f"<tr><td>{num}</td><td>{left}</td><td>{right}</td><td>{score}</td></tr>"
    table_html += "</table>"

    return f"<h3>Strongest Numbers with Neighbours</h3>{table_html}"
def highlight_even_money(strategy_name, sorted_sections, top_color, middle_color, lower_color):
    """Highlight even money bets for relevant strategies."""
    if sorted_sections is None:
        return None, None, None, {}
    trending, second, third = None, None, None
    number_highlights = {}
    if strategy_name in ["Best Even Money Bets", "Best Even Money Bets + Top Pick 18 Numbers", 
                         "Best Dozens + Best Even Money Bets + Top Pick 18 Numbers", 
                         "Best Columns + Best Even Money Bets + Top Pick 18 Numbers"]:
        even_money_hits = [item for item in sorted_sections["even_money"] if item[1] > 0]
        if even_money_hits:
            trending = even_money_hits[0][0]
            second = even_money_hits[1][0] if len(even_money_hits) > 1 else None
            third = even_money_hits[2][0] if len(even_money_hits) > 2 else None
    elif strategy_name == "Hot Bet Strategy":
        trending = sorted_sections["even_money"][0][0] if sorted_sections["even_money"] else None
        second = sorted_sections["even_money"][1][0] if len(sorted_sections["even_money"]) > 1 else None
    elif strategy_name == "Cold Bet Strategy":
        sorted_even_money = sorted(state.even_money_scores.items(), key=lambda x: x[1])
        trending = sorted_even_money[0][0] if sorted_even_money else None
        second = sorted_even_money[1][0] if len(sorted_even_money) > 1 else None
    elif strategy_name in ["3-8-6 Rising Martingale", "Fibonacci To Fortune"]:
        trending = sorted_sections["even_money"][0][0] if sorted_sections["even_money"] else None
    return trending, second, third, number_highlights

def highlight_dozens(strategy_name, sorted_sections, top_color, middle_color, lower_color):
    """Highlight dozens for relevant strategies."""
    if sorted_sections is None:
        return None, None, {}
    trending, second = None, None
    number_highlights = {}
    if strategy_name in ["Best Dozens", "Best Dozens + Top Pick 18 Numbers", 
                         "Best Dozens + Best Even Money Bets + Top Pick 18 Numbers", 
                         "Best Dozens + Best Streets"]:
        dozens_hits = [item for item in sorted_sections["dozens"] if item[1] > 0]
        if dozens_hits:
            trending = dozens_hits[0][0]
            second = dozens_hits[1][0] if len(dozens_hits) > 1 else None
    elif strategy_name == "Hot Bet Strategy":
        trending = sorted_sections["dozens"][0][0] if sorted_sections["dozens"] else None
        second = sorted_sections["dozens"][1][0] if len(sorted_sections["dozens"]) > 1 else None
    elif strategy_name == "Cold Bet Strategy":
        sorted_dozens = sorted(state.dozen_scores.items(), key=lambda x: x[1])
        trending = sorted_dozens[0][0] if sorted_dozens else None
        second = sorted_dozens[1][0] if len(sorted_dozens) > 1 else None
    elif strategy_name in ["Fibonacci Strategy", "Fibonacci To Fortune"]:
        best_dozen_score = sorted_sections["dozens"][0][1] if sorted_sections["dozens"] else 0
        best_column_score = sorted_sections["columns"][0][1] if sorted_sections["columns"] else 0
        if best_dozen_score >= best_column_score:
            trending = sorted_sections["dozens"][0][0] if sorted_sections["dozens"] else None
    elif strategy_name == "1 Dozen +1 Column Strategy":
        trending = sorted_sections["dozens"][0][0] if sorted_sections["dozens"] and sorted_sections["dozens"][0][1] > 0 else None
    elif strategy_name == "Romanowksy Missing Dozen":
        trending = sorted_sections["dozens"][0][0] if sorted_sections["dozens"] and sorted_sections["dozens"][0][1] > 0 else None
        second = sorted_sections["dozens"][1][0] if len(sorted_sections["dozens"]) > 1 and sorted_sections["dozens"][1][1] > 0 else None
        weakest_dozen = min(state.dozen_scores.items(), key=lambda x: x[1], default=("1st Dozen", 0))[0]
        straight_up_df = pd.DataFrame(list(state.scores.items()), columns=["Number", "Score"])
        straight_up_df = straight_up_df[straight_up_df["Score"] > 0].sort_values(by="Score", ascending=False)
        weak_numbers = [row["Number"] for _, row in straight_up_df.iterrows() if row["Number"] in DOZENS[weakest_dozen]][:8]
        for num in weak_numbers:
            number_highlights[str(num)] = top_color
    return trending, second, number_highlights

def highlight_columns(strategy_name, sorted_sections, top_color, middle_color, lower_color):
    """Highlight columns for relevant strategies."""
    if sorted_sections is None:
        return None, None, {}
    trending, second = None, None
    number_highlights = {}
    if strategy_name in ["Best Columns", "Best Columns + Top Pick 18 Numbers", 
                         "Best Columns + Best Even Money Bets + Top Pick 18 Numbers", 
                         "Best Columns + Best Streets"]:
        columns_hits = [item for item in sorted_sections["columns"] if item[1] > 0]
        if columns_hits:
            trending = columns_hits[0][0]
            second = columns_hits[1][0] if len(columns_hits) > 1 else None
    elif strategy_name == "Hot Bet Strategy":
        trending = sorted_sections["columns"][0][0] if sorted_sections["columns"] else None
        second = sorted_sections["columns"][1][0] if len(sorted_sections["columns"]) > 1 else None
    elif strategy_name == "Cold Bet Strategy":
        sorted_columns = sorted(state.column_scores.items(), key=lambda x: x[1])
        trending = sorted_columns[0][0] if sorted_columns else None
        second = sorted_columns[1][0] if len(sorted_columns) > 1 else None
    elif strategy_name == "Fibonacci Strategy":
        best_dozen_score = sorted_sections["dozens"][0][1] if sorted_sections["dozens"] else 0
        best_column_score = sorted_sections["columns"][0][1] if sorted_sections["columns"] else 0
        if best_column_score > best_dozen_score:
            trending = sorted_sections["columns"][0][0] if sorted_sections["columns"] else None
    elif strategy_name == "1 Dozen +1 Column Strategy":
        trending = sorted_sections["columns"][0][0] if sorted_sections["columns"] and sorted_sections["columns"][0][1] > 0 else None
    return trending, second, number_highlights

def highlight_numbers(strategy_name, sorted_sections, top_color, middle_color, lower_color):
    """Highlight straight-up numbers for relevant strategies."""
    if sorted_sections is None:
        return {}
    number_highlights = {}
    straight_up_df = pd.DataFrame(list(state.scores.items()), columns=["Number", "Score"])
    straight_up_df = straight_up_df[straight_up_df["Score"] > 0].sort_values(by="Score", ascending=False)
    
    if strategy_name in ["Top Pick 18 Numbers without Neighbours", 
                         "Best Even Money Bets + Top Pick 18 Numbers", 
                         "Best Dozens + Top Pick 18 Numbers", 
                         "Best Columns + Top Pick 18 Numbers", 
                         "Best Dozens + Best Even Money Bets + Top Pick 18 Numbers", 
                         "Best Columns + Best Even Money Bets + Top Pick 18 Numbers"]:
        if len(straight_up_df) >= 18:
            top_18_numbers = straight_up_df["Number"].head(18).tolist()
            for i, num in enumerate(top_18_numbers):
                color = top_color if i < 6 else (middle_color if i < 12 else lower_color)
                number_highlights[str(num)] = color
    elif strategy_name == "Top Numbers with Neighbours (Tiered)":
        num_to_take = min(8, len(straight_up_df))
        top_numbers = set(straight_up_df["Number"].head(num_to_take).tolist())
        number_groups = []
        for num in top_numbers:
            left, right = current_neighbors.get(num, (None, None))
            group = [num]
            if left is not None:
                group.append(left)
            if right is not None:
                group.append(right)
            number_groups.append((state.scores[num], group))
        number_groups.sort(key=lambda x: x[0], reverse=True)
        ordered_numbers = []
        for _, group in number_groups:
            ordered_numbers.extend(group)
        ordered_numbers = ordered_numbers[:24]
        for i, num in enumerate(ordered_numbers):
            color = top_color if i < 8 else (middle_color if i < 16 else lower_color)
            number_highlights[str(num)] = color
    return number_highlights

def highlight_other_bets(strategy_name, sorted_sections, top_color, middle_color, lower_color):
    """Highlight streets, corners, splits, and double streets for relevant strategies."""
    if sorted_sections is None:
        return {}
    number_highlights = {}
    
    if strategy_name == "Hot Bet Strategy":
        for i, (street_name, _) in enumerate(sorted_sections["streets"][:9]):
            numbers = STREETS[street_name]
            color = top_color if i < 3 else (middle_color if 3 <= i < 6 else lower_color)
            for num in numbers:
                number_highlights[str(num)] = color
        for i, (corner_name, _) in enumerate(sorted_sections["corners"][:9]):
            numbers = CORNERS[corner_name]
            color = top_color if i < 3 else (middle_color if 3 <= i < 6 else lower_color)
            for num in numbers:
                number_highlights[str(num)] = color
        for i, (split_name, _) in enumerate(sorted_sections["splits"][:9]):
            numbers = SPLITS[split_name]
            color = top_color if i < 3 else (middle_color if 3 <= i < 6 else lower_color)
            for num in numbers:
                number_highlights[str(num)] = color
    elif strategy_name == "Cold Bet Strategy":
        sorted_streets = sorted(state.street_scores.items(), key=lambda x: x[1])
        sorted_corners = sorted(state.corner_scores.items(), key=lambda x: x[1])
        sorted_splits = sorted(state.split_scores.items(), key=lambda x: x[1])
        for i, (street_name, _) in enumerate(sorted_streets[:9]):
            numbers = STREETS[street_name]
            color = top_color if i < 3 else (middle_color if 3 <= i < 6 else lower_color)
            for num in numbers:
                number_highlights[str(num)] = color
        for i, (corner_name, _) in enumerate(sorted_corners[:9]):
            numbers = CORNERS[corner_name]
            color = top_color if i < 3 else (middle_color if 3 <= i < 6 else lower_color)
            for num in numbers:
                number_highlights[str(num)] = color
        for i, (split_name, _) in enumerate(sorted_splits[:9]):
            numbers = SPLITS[split_name]
            color = top_color if i < 3 else (middle_color if 3 <= i < 6 else lower_color)
            for num in numbers:
                number_highlights[str(num)] = color
    elif strategy_name == "Best Streets":
        for i, (street_name, _) in enumerate(sorted_sections["streets"][:9]):
            numbers = STREETS[street_name]
            color = top_color if i < 3 else (middle_color if 3 <= i < 6 else lower_color)
            for num in numbers:
                number_highlights[str(num)] = color
    elif strategy_name in ["Best Dozens + Best Streets", "Best Columns + Best Streets"]:
        for i, (street_name, _) in enumerate(sorted_sections["streets"][:9]):
            numbers = STREETS[street_name]
            color = top_color if i < 3 else (middle_color if 3 <= i < 6 else lower_color)
            for num in numbers:
                number_highlights[str(num)] = color
    elif strategy_name == "Best Double Streets":
        for i, (six_line_name, _) in enumerate(sorted_sections["six_lines"][:9]):
            numbers = SIX_LINES[six_line_name]
            color = top_color if i < 3 else (middle_color if 3 <= i < 6 else lower_color)
            for num in numbers:
                number_highlights[str(num)] = color
    elif strategy_name == "Best Corners":
        for i, (corner_name, _) in enumerate(sorted_sections["corners"][:9]):
            numbers = CORNERS[corner_name]
            color = top_color if i < 3 else (middle_color if 3 <= i < 6 else lower_color)
            for num in numbers:
                number_highlights[str(num)] = color
    elif strategy_name == "Best Splits":
        for i, (split_name, _) in enumerate(sorted_sections["splits"][:9]):
            numbers = SPLITS[split_name]
            color = top_color if i < 3 else (middle_color if 3 <= i < 6 else lower_color)
            for num in numbers:
                number_highlights[str(num)] = color
    elif strategy_name == "Non-Overlapping Double Street Strategy":
        non_overlapping_sets = [
            ["1ST D.STREET – 1, 4", "3RD D.STREET – 7, 10", "5TH D.STREET – 13, 16", "7TH D.STREET – 19, 22", "9TH D.STREET – 25, 28"],
            ["2ND D.STREET – 4, 7", "4TH D.STREET – 10, 13", "6TH D.STREET – 16, 19", "8TH D.STREET – 22, 25", "10TH D.STREET – 28, 31"]
        ]
        set_scores = []
        for idx, non_overlapping_set in enumerate(non_overlapping_sets):
            total_score = sum(state.six_line_scores.get(name, 0) for name in non_overlapping_set)
            set_scores.append((idx, total_score, non_overlapping_set))
        best_set = max(set_scores, key=lambda x: x[1], default=(0, 0, non_overlapping_sets[0]))
        sorted_best_set = sorted(best_set[2], key=lambda name: state.six_line_scores.get(name, 0), reverse=True)[:9]
        for i, double_street_name in enumerate(sorted_best_set):
            numbers = SIX_LINES[double_street_name]
            color = top_color if i < 3 else (middle_color if 3 <= i < 6 else lower_color)
            for num in numbers:
                number_highlights[str(num)] = color
    elif strategy_name == "Non-Overlapping Corner Strategy":
        sorted_corners = sorted(state.corner_scores.items(), key=lambda x: x[1], reverse=True)
        selected_corners = []
        selected_numbers = set()
        for corner_name, _ in sorted_corners:
            if len(selected_corners) >= 9:
                break
            corner_numbers = set(CORNERS[corner_name])
            if not corner_numbers & selected_numbers:
                selected_corners.append(corner_name)
                selected_numbers.update(corner_numbers)
        for i, corner_name in enumerate(selected_corners):
            numbers = CORNERS[corner_name]
            color = top_color if i < 3 else (middle_color if 3 <= i < 6 else lower_color)
            for num in numbers:
                number_highlights[str(num)] = color
    elif strategy_name == "3-8-6 Rising Martingale":
        top_streets = sorted_sections["streets"][:8]
        for i, (street_name, _) in enumerate(top_streets):
            numbers = STREETS[street_name]
            color = top_color if i < 3 else (middle_color if 3 <= i < 6 else lower_color)
            for num in numbers:
                number_highlights[str(num)] = color
    elif strategy_name == "Fibonacci To Fortune":
        weakest_dozen = min(state.dozen_scores.items(), key=lambda x: x[1], default=("1st Dozen", 0))[0]
        double_streets_in_weakest = [(name, state.six_line_scores.get(name, 0)) for name, numbers in SIX_LINES.items() if set(numbers).issubset(DOZENS[weakest_dozen])]
        if double_streets_in_weakest:
            top_double_street = max(double_streets_in_weakest, key=lambda x: x[1])[0]
            for num in SIX_LINES[top_double_street]:
                number_highlights[str(num)] = top_color
    return number_highlights

def highlight_neighbors(strategy_name, sorted_sections, neighbours_count, strong_numbers_count, top_color, middle_color):
    """Highlight neighbors for the Neighbours of Strong Number strategy."""
    if sorted_sections is None:
        return {}
    number_highlights = {}
    if strategy_name == "Neighbours of Strong Number":
        sorted_numbers = sorted(state.scores.items(), key=lambda x: (-x[1], x[0]))
        numbers_hits = [item for item in sorted_numbers if item[1] > 0]
        if numbers_hits:
            strong_numbers_count = min(strong_numbers_count, len(numbers_hits))
            top_numbers = set(item[0] for item in numbers_hits[:strong_numbers_count])
            neighbors_set = set()
            for strong_number in top_numbers:
                current_number = strong_number
                for _ in range(neighbours_count):
                    left, _ = current_neighbors.get(current_number, (None, None))
                    if left is not None:
                        neighbors_set.add(left)
                        current_number = left
                    else:
                        break
                current_number = strong_number
                for _ in range(neighbours_count):
                    _, right = current_neighbors.get(current_number, (None, None))
                    if right is not None:
                        neighbors_set.add(right)
                        current_number = right
                    else:
                        break
            neighbors_set = neighbors_set - top_numbers
            for num in top_numbers:
                number_highlights[str(num)] = top_color
            for num in neighbors_set:
                number_highlights[str(num)] = middle_color
    return number_highlights
# Function to create the dynamic roulette table with highlighted trending sections
def calculate_trending_sections():
    """Calculate trending sections based on current scores."""
    if not any(state.scores.values()) and not any(state.even_money_scores.values()):
        return None  # Indicates no data to process

    return {
        "even_money": sorted(state.even_money_scores.items(), key=lambda x: x[1], reverse=True),
        "dozens": sorted(state.dozen_scores.items(), key=lambda x: x[1], reverse=True),
        "columns": sorted(state.column_scores.items(), key=lambda x: x[1], reverse=True),
        "streets": sorted(state.street_scores.items(), key=lambda x: x[1], reverse=True),
        "six_lines": sorted(state.six_line_scores.items(), key=lambda x: x[1], reverse=True),
        "corners": sorted(state.corner_scores.items(), key=lambda x: x[1], reverse=True),
        "splits": sorted(state.split_scores.items(), key=lambda x: x[1], reverse=True)
    }

def apply_strategy_highlights(strategy_name, neighbours_count, strong_numbers_count, sorted_sections, top_color=None, middle_color=None, lower_color=None):
    """Apply highlights based on the selected strategy with custom colors."""
    if sorted_sections is None:
        return None, None, None, None, None, None, None, {}, "white", "white", "white"

    # Set default colors unless overridden
    if strategy_name == "Cold Bet Strategy":
        top_color = "#D3D3D3"  # Light Gray (Cold Top)
        middle_color = "#DDA0DD"  # Plum (Cold Middle)
        lower_color = "#E0FFFF"  # Light Cyan (Cold Lower)
    else:
        top_color = top_color if top_color else "rgba(255, 255, 0, 0.5)"  # Yellow
        middle_color = middle_color if middle_color else "rgba(0, 255, 255, 0.5)"  # Cyan
        lower_color = lower_color if lower_color else "rgba(0, 255, 0, 0.5)"  # Green

    # Initialize highlight variables
    trending_even_money, second_even_money, third_even_money = None, None, None
    trending_dozen, second_dozen = None, None
    trending_column, second_column = None, None
    number_highlights = {}

    # Apply highlights based onShannon (state, strategy_name)
    if strategy_name and strategy_name in STRATEGIES:
        strategy_info = STRATEGIES[strategy_name]
        if strategy_name == "Neighbours of Strong Number":
            strategy_output = strategy_info["function"](neighbours_count, strong_numbers_count)
        else:
            strategy_output = strategy_info["function"]()
        
        # Delegate to helper functions
        em_trending, em_second, em_third, em_highlights = highlight_even_money(strategy_name, sorted_sections, top_color, middle_color, lower_color)
        dz_trending, dz_second, dz_highlights = highlight_dozens(strategy_name, sorted_sections, top_color, middle_color, lower_color)
        col_trending, col_second, col_highlights = highlight_columns(strategy_name, sorted_sections, top_color, middle_color, lower_color)
        num_highlights = highlight_numbers(strategy_name, sorted_sections, top_color, middle_color, lower_color)
        other_highlights = highlight_other_bets(strategy_name, sorted_sections, top_color, middle_color, lower_color)
        neighbor_highlights = highlight_neighbors(strategy_name, sorted_sections, neighbours_count, strong_numbers_count, top_color, middle_color)

        # Combine highlights
        trending_even_money = em_trending
        second_even_money = em_second
        third_even_money = em_third
        trending_dozen = dz_trending
        second_dozen = dz_second
        trending_column = col_trending
        second_column = col_second
        number_highlights.update(em_highlights)
        number_highlights.update(dz_highlights)
        number_highlights.update(col_highlights)
        number_highlights.update(num_highlights)
        number_highlights.update(other_highlights)
        number_highlights.update(neighbor_highlights)

    # Dozen Tracker Logic (When No Strategy is Selected)
    if strategy_name == "None":
        recent_spins = state.last_spins[-neighbours_count:] if len(state.last_spins) >= neighbours_count else state.last_spins
        dozen_counts = {"1st Dozen": 0, "2nd Dozen": 0, "3rd Dozen": 0}
        for spin in recent_spins:
            spin_value = int(spin)
            if spin_value != 0:
                for name, numbers in DOZENS.items():
                    if spin_value in numbers:
                        dozen_counts[name] += 1
                        break
        sorted_dozens = sorted(dozen_counts.items(), key=lambda x: x[1], reverse=True)
        if sorted_dozens[0][1] > 0:
            trending_dozen = sorted_dozens[0][0]
        if sorted_dozens[1][1] > 0:
            second_dozen = sorted_dozens[1][0]

    return trending_even_money, second_even_money, third_even_money, trending_dozen, second_dozen, trending_column, second_column, number_highlights, top_color, middle_color, lower_color

def render_dynamic_table_html(trending_even_money, second_even_money, third_even_money, trending_dozen, second_dozen, trending_column, second_column, number_highlights, top_color, middle_color, lower_color):
    """Generate HTML for the dynamic roulette table with improved visual clarity."""
    if all(v is None for v in [trending_even_money, second_even_money, third_even_money, trending_dozen, second_dozen, trending_column, second_column]) and not number_highlights:
        return "<p>Please analyze some spins first to see highlights on the dynamic table.</p>"

    # Define casino winners if highlighting is enabled, only for non-zero data
    casino_winners = {"hot_numbers": set(), "cold_numbers": set(), "even_money": set(), "dozens": set(), "columns": set()}
    if state.use_casino_winners:
        casino_winners["hot_numbers"] = set(state.casino_data["hot_numbers"].keys())
        casino_winners["cold_numbers"] = set(state.casino_data["cold_numbers"].keys())
        if any(state.casino_data["even_odd"].values()):
            casino_winners["even_money"].add(max(state.casino_data["even_odd"], key=state.casino_data["even_odd"].get))
        if any(state.casino_data["red_black"].values()):
            casino_winners["even_money"].add(max(state.casino_data["red_black"], key=state.casino_data["red_black"].get))
        if any(state.casino_data["low_high"].values()):
            casino_winners["even_money"].add(max(state.casino_data["low_high"], key=state.casino_data["low_high"].get))
        if any(state.casino_data["dozens"].values()):
            casino_winners["dozens"] = {max(state.casino_data["dozens"], key=state.casino_data["dozens"].get)}
        if any(state.casino_data["columns"].values()):
            casino_winners["columns"] = {max(state.casino_data["columns"], key=state.casino_data["columns"].get)}
        print(f"Casino Winners Set: Hot={casino_winners['hot_numbers']}, Cold={casino_winners['cold_numbers']}, Even Money={casino_winners['even_money']}, Dozens={casino_winners['dozens']}, Columns={casino_winners['columns']}")

    table_layout = [
        ["", "3", "6", "9", "12", "15", "18", "21", "24", "27", "30", "33", "36"],
        ["0", "2", "5", "8", "11", "14", "17", "20", "23", "26", "29", "32", "35"],
        ["", "1", "4", "7", "10", "13", "16", "19", "22", "25", "28", "31", "34"]
    ]

    html = '<table border="1" style="border-collapse: collapse; text-align: center; font-size: 14px; font-family: Arial, sans-serif; border-color: black; table-layout: fixed; width: 100%; max-width: 600px;">'
    html += '<colgroup>'
    html += '<col style="width: 40px;">'
    for _ in range(12):
        html += '<col style="width: 40px;">'
    html += '<col style="width: 80px;">'
    html += '</colgroup>'

    for row_idx, row in enumerate(table_layout):
        html += "<tr>"
        for num in row:
            if num == "":
                html += '<td style="height: 40px; border-color: black; box-sizing: border-box;"></td>'
            else:
                base_color = colors.get(num, "black")
                highlight_color = number_highlights.get(num, base_color)
                if num in casino_winners["hot_numbers"]:
                    border_style = "3px dashed #FFD700"  # Gold for Hot Numbers
                elif num in casino_winners["cold_numbers"]:
                    border_style = "3px dashed #C0C0C0"  # Silver for Cold Numbers
                else:
                    border_style = "3px solid black"
                text_style = "color: white; font-weight: bold; text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.8);"
                html += f'<td style="height: 40px; background-color: {highlight_color}; {text_style} border: {border_style}; padding: 0; vertical-align: middle; box-sizing: border-box; text-align: center;">{num}</td>'
        if row_idx == 0:
            bg_color = top_color if trending_column == "3rd Column" else (middle_color if second_column == "3rd Column" else "white")
            border_style = "3px dashed #FFD700" if "3rd Column" in casino_winners["columns"] else "1px solid black"
            html += f'<td style="background-color: {bg_color}; border: {border_style}; padding: 0; font-size: 10px; vertical-align: middle; box-sizing: border-box; height: 40px; text-align: center;">3rd Column</td>'
        elif row_idx == 1:
            bg_color = top_color if trending_column == "2nd Column" else (middle_color if second_column == "2nd Column" else "white")
            border_style = "3px dashed #FFD700" if "2nd Column" in casino_winners["columns"] else "1px solid black"
            html += f'<td style="background-color: {bg_color}; border: {border_style}; padding: 0; font-size: 10px; vertical-align: middle; box-sizing: border-box; height: 40px; text-align: center;">2nd Column</td>'
        elif row_idx == 2:
            bg_color = top_color if trending_column == "1st Column" else (middle_color if second_column == "1st Column" else "white")
            border_style = "3px dashed #FFD700" if "1st Column" in casino_winners["columns"] else "1px solid black"
            html += f'<td style="background-color: {bg_color}; border: {border_style}; padding: 0; font-size: 10px; vertical-align: middle; box-sizing: border-box; height: 40px; text-align: center;">1st Column</td>'
        html += "</tr>"

    html += "<tr>"
    html += '<td style="height: 40px; border-color: black; box-sizing: border-box;"></td>'
    bg_color = top_color if trending_even_money == "Low" else (middle_color if second_even_money == "Low" else (lower_color if third_even_money == "Low" else "white"))
    border_style = "3px dashed #FFD700" if "Low" in casino_winners["even_money"] else "1px solid black"
    html += f'<td colspan="6" style="background-color: {bg_color}; color: black; border: {border_style}; padding: 0; font-size: 10px; vertical-align: middle; box-sizing: border-box; height: 40px; text-align: center;">Low (1 to 18)</td>'
    bg_color = top_color if trending_even_money == "High" else (middle_color if second_even_money == "High" else (lower_color if third_even_money == "High" else "white"))
    border_style = "3px dashed #FFD700" if "High" in casino_winners["even_money"] else "1px solid black"
    html += f'<td colspan="6" style="background-color: {bg_color}; color: black; border: {border_style}; padding: 0; font-size: 10px; vertical-align: middle; box-sizing: border-box; height: 40px; text-align: center;">High (19 to 36)</td>'
    html += '<td style="border-color: black; box-sizing: border-box;"></td>'
    html += "</tr>"

    html += "<tr>"
    html += '<td style="height: 40px; border-color: black; box-sizing: border-box;"></td>'
    bg_color = top_color if trending_dozen == "1st Dozen" else (middle_color if second_dozen == "1st Dozen" else "white")
    border_style = "3px dashed #FFD700" if "1st Dozen" in casino_winners["dozens"] else "1px solid black"
    html += f'<td colspan="4" style="background-color: {bg_color}; color: black; border: {border_style}; padding: 0; font-size: 10px; vertical-align: middle; box-sizing: border-box; height: 40px; text-align: center;">1st Dozen</td>'
    bg_color = top_color if trending_dozen == "2nd Dozen" else (middle_color if second_dozen == "2nd Dozen" else "white")
    border_style = "3px dashed #FFD700" if "2nd Dozen" in casino_winners["dozens"] else "1px solid black"
    html += f'<td colspan="4" style="background-color: {bg_color}; color: black; border: {border_style}; padding: 0; font-size: 10px; vertical-align: middle; box-sizing: border-box; height: 40px; text-align: center;">2nd Dozen</td>'
    bg_color = top_color if trending_dozen == "3rd Dozen" else (middle_color if second_dozen == "3rd Dozen" else "white")
    border_style = "3px dashed #FFD700" if "3rd Dozen" in casino_winners["dozens"] else "1px solid black"
    html += f'<td colspan="4" style="background-color: {bg_color}; color: black; border: {border_style}; padding: 0; font-size: 10px; vertical-align: middle; box-sizing: border-box; height: 40px; text-align: center;">3rd Dozen</td>'
    html += '<td style="border-color: black; box-sizing: border-box;"></td>'
    html += "</tr>"

    html += "<tr>"
    html += '<td style="height: 40px; border-color: black; box-sizing: border-box;"></td>'
    bg_color = top_color if trending_even_money == "Odd" else (middle_color if second_even_money == "Odd" else (lower_color if third_even_money == "Odd" else "white"))
    border_style = "3px dashed #FFD700" if "Odd" in casino_winners["even_money"] else "1px solid black"
    html += f'<td colspan="4" style="border-color: black; box-sizing: border-box;"></td>'
    html += f'<td style="background-color: {bg_color}; color: black; border: {border_style}; padding: 0; font-size: 10px; vertical-align: middle; box-sizing: border-box; height: 40px; text-align: center;">ODD</td>'
    bg_color = top_color if trending_even_money == "Red" else (middle_color if second_even_money == "Red" else (lower_color if third_even_money == "Red" else "white"))
    border_style = "3px dashed #FFD700" if "Red" in casino_winners["even_money"] else "1px solid black"
    html += f'<td style="background-color: {bg_color}; color: black; border: {border_style}; padding: 0; font-size: 10px; vertical-align: middle; box-sizing: border-box; height: 40px; text-align: center;">RED</td>'
    bg_color = top_color if trending_even_money == "Black" else (middle_color if second_even_money == "Black" else (lower_color if third_even_money == "Black" else "white"))
    border_style = "3px dashed #FFD700" if "Black" in casino_winners["even_money"] else "1px solid black"
    html += f'<td style="background-color: {bg_color}; color: black; border: {border_style}; padding: 0; font-size: 10px; vertical-align: middle; box-sizing: border-box; height: 40px; text-align: center;">BLACK</td>'
    bg_color = top_color if trending_even_money == "Even" else (middle_color if second_even_money == "Even" else (lower_color if third_even_money == "Even" else "white"))
    border_style = "3px dashed #FFD700" if "Even" in casino_winners["even_money"] else "1px solid black"
    html += f'<td style="background-color: {bg_color}; color: black; border: {border_style}; padding: 0; font-size: 10px; vertical-align: middle; box-sizing: border-box; height: 40px; text-align: center;">EVEN</td>'
    html += f'<td colspan="4" style="border-color: black; box-sizing: border-box;"></td>'
    html += '<td style="border-color: black; box-sizing: border-box;"></td>'
    html += "</tr>"

    html += "</table>"
    return html

def update_casino_data(spins_count, even_percent, odd_percent, red_percent, black_percent, low_percent, high_percent, dozen1_percent, dozen2_percent, dozen3_percent, col1_percent, col2_percent, col3_percent, use_winners):
    """Parse casino data inputs, update state, and generate HTML output."""
    try:
        state.casino_data["spins_count"] = int(spins_count)
        state.use_casino_winners = use_winners

        # Remove Hot/Cold Numbers parsing
        state.casino_data["hot_numbers"] = {}
        state.casino_data["cold_numbers"] = {}

        # Parse percentages from dropdowns
        def parse_percent(value, category, key):
            try:
                return float(value) if value != "00" else 0.0
            except ValueError:
                raise ValueError(f"Invalid {category} percentage for {key}: {value}")

        # Even/Odd
        even_val = parse_percent(even_percent, "Even vs Odd", "Even")
        odd_val = parse_percent(odd_percent, "Even vs Odd", "Odd")
        state.casino_data["even_odd"] = {"Even": even_val, "Odd": odd_val}
        has_even_odd = even_val > 0 or odd_val > 0

        # Red/Black
        red_val = parse_percent(red_percent, "Red vs Black", "Red")
        black_val = parse_percent(black_percent, "Red vs Black", "Black")
        state.casino_data["red_black"] = {"Red": red_val, "Black": black_val}
        has_red_black = red_val > 0 or black_val > 0

        # Low/High
        low_val = parse_percent(low_percent, "Low vs High", "Low")
        high_val = parse_percent(high_percent, "Low vs High", "High")
        state.casino_data["low_high"] = {"Low": low_val, "High": high_val}
        has_low_high = low_val > 0 or high_val > 0

        # Dozens
        d1_val = parse_percent(dozen1_percent, "Dozens", "1st Dozen")
        d2_val = parse_percent(dozen2_percent, "Dozens", "2nd Dozen")
        d3_val = parse_percent(dozen3_percent, "Dozens", "3rd Dozen")
        state.casino_data["dozens"] = {"1st Dozen": d1_val, "2nd Dozen": d2_val, "3rd Dozen": d3_val}
        has_dozens = d1_val > 0 or d2_val > 0 or d3_val > 0

        # Columns
        c1_val = parse_percent(col1_percent, "Columns", "1st Column")
        c2_val = parse_percent(col2_percent, "Columns", "2nd Column")
        c3_val = parse_percent(col3_percent, "Columns", "3rd Column")
        state.casino_data["columns"] = {"1st Column": c1_val, "2nd Column": c2_val, "3rd Column": c3_val}
        has_columns = c1_val > 0 or c2_val > 0 or c3_val > 0

        # Check for empty data when highlighting is enabled
        if use_winners and not any([has_even_odd, has_red_black, has_low_high, has_dozens, has_columns]):
            gr.Warning("Highlight Casino Winners is enabled, but no casino data is provided. Enter percentages to see highlights.")
            return "<p>Warning: No casino data provided for highlighting. Please enter percentages for Even/Odd, Red/Black, Low/High, Dozens, or Columns.</p>"

        # Generate HTML Output
        output = f"<h4>Casino Data Insights (Last {spins_count} Spins):</h4>"
        for key, name, has_data in [
            ("even_odd", "Even vs Odd", has_even_odd),
            ("red_black", "Red vs Black", has_red_black),
            ("low_high", "Low vs High", has_low_high)
        ]:
            if has_data:
                winner = max(state.casino_data[key], key=state.casino_data[key].get)
                output += f"<p>{name}: " + " vs ".join(
                    f"<b>{v:.1f}%</b>" if k == winner else f"{v:.1f}%" for k, v in state.casino_data[key].items()
                ) + f" (Winner: {winner})</p>"
            else:
                output += f"<p>{name}: Not set</p>"
        for key, name, has_data in [
            ("dozens", "Dozens", has_dozens),
            ("columns", "Columns", has_columns)
        ]:
            if has_data:
                winner = max(state.casino_data[key], key=state.casino_data[key].get)
                output += f"<p>{name}: " + " vs ".join(
                    f"<b>{v:.1f}%</b>" if k == winner else f"{v:.1f}%" for k, v in state.casino_data[key].items()
                ) + f" (Winner: {winner})</p>"
            else:
                output += f"<p>{name}: Not set</p>"
        print(f"Generated HTML Output: {output}")
        return output
    except ValueError as e:
        return f"<p>Error: {str(e)}</p>"
    except Exception as e:
        return f"<p>Unexpected error parsing casino data: {str(e)}</p>"
        
def reset_casino_data():
    """Reset casino data to defaults and clear UI inputs."""
    state.casino_data = {
        "spins_count": 100,
        "hot_numbers": {},
        "cold_numbers": {},
        "even_odd": {"Even": 0.0, "Odd": 0.0},
        "red_black": {"Red": 0.0, "Black": 0.0},
        "low_high": {"Low": 0.0, "High": 0.0},
        "dozens": {"1st Dozen": 0.0, "2nd Dozen": 0.0, "3rd Dozen": 0.0},
        "columns": {"1st Column": 0.0, "2nd Column": 0.0, "3rd Column": 0.0}
    }
    state.use_casino_winners = False
    return (
        "100",  # spins_count_dropdown
        "",     # hot_numbers_input
        "",     # cold_numbers_input
        "",     # even_odd_input
        "",     # red_black_input
        "",     # low_high_input
        "",     # dozens_input
        "",     # columns_input
        False,  # use_winners_checkbox
        "<p>Casino data reset to defaults.</p>"  # casino_data_output
    )

def create_dynamic_table(strategy_name=None, neighbours_count=2, strong_numbers_count=1, dozen_tracker_spins=5, top_color=None, middle_color=None, lower_color=None):
    print(f"create_dynamic_table called with strategy: {strategy_name}, neighbours_count: {neighbours_count}, strong_numbers_count: {strong_numbers_count}, dozen_tracker_spins: {dozen_tracker_spins}, top_color: {top_color}, middle_color: {middle_color}, lower_color: {lower_color}")
    print(f"Using casino winners: {state.use_casino_winners}, Hot Numbers: {state.casino_data['hot_numbers']}, Cold Numbers: {state.casino_data['cold_numbers']}")
    sorted_sections = calculate_trending_sections()
    
    # If no spins yet, initialize with default even money focus
    if sorted_sections is None and strategy_name == "Best Even Money Bets":
        trending_even_money = "Red"  # Default to "Red" as an example
        second_even_money = "Black"
        third_even_money = "Even"
        trending_dozen = None
        second_dozen = None
        trending_column = None
        second_column = None
        number_highlights = {}
        top_color = top_color if top_color else "rgba(255, 255, 0, 0.5)"
        middle_color = middle_color if middle_color else "rgba(0, 255, 255, 0.5)"
        lower_color = lower_color if lower_color else "rgba(0, 255, 0, 0.5)"
    else:
        trending_even_money, second_even_money, third_even_money, trending_dozen, second_dozen, trending_column, second_column, number_highlights, top_color, middle_color, lower_color = apply_strategy_highlights(strategy_name, int(dozen_tracker_spins) if strategy_name == "None" else neighbours_count, strong_numbers_count, sorted_sections, top_color, middle_color, lower_color)
    
    # If still no highlights and no sorted_sections, provide a default message
    if sorted_sections is None and not any([trending_even_money, second_even_money, third_even_money, trending_dozen, second_dozen, trending_column, second_column, number_highlights]):
        return "<p>No spins yet. Select a strategy to see default highlights.</p>"
    
    return render_dynamic_table_html(trending_even_money, second_even_money, third_even_money, trending_dozen, second_dozen, trending_column, second_column, number_highlights, top_color, middle_color, lower_color)
    
    # If still no highlights and no sorted_sections, provide a default message
    if sorted_sections is None and not any([trending_even_money, second_even_money, third_even_money, trending_dozen, second_dozen, trending_column, second_column, number_highlights]):
        return "<p>No spins yet. Select a strategy to see default highlights.</p>"
    
    return render_dynamic_table_html(trending_even_money, second_even_money, third_even_money, trending_dozen, second_dozen, trending_column, second_column, number_highlights, top_color, middle_color, lower_color)

# Function to get strongest numbers with neighbors
def get_strongest_numbers_with_neighbors(num_count):
    num_count = int(num_count)
    straight_up_df = pd.DataFrame(list(state.scores.items()), columns=["Number", "Score"])
    straight_up_df = straight_up_df[straight_up_df["Score"] > 0].sort_values(by="Score", ascending=False)

    if straight_up_df.empty:
        return "No numbers have hit yet."

    num_to_take = max(1, num_count // 3)
    top_numbers = straight_up_df["Number"].head(num_to_take).tolist()

    if not top_numbers:
        return "No strong numbers available to display."

    all_numbers = set()
    for num in top_numbers:
        neighbors = current_neighbors.get(num, (None, None))
        left, right = neighbors
        all_numbers.add(num)
        if left is not None:
            all_numbers.add(left)
        if right is not None:
            all_numbers.add(right)

    sorted_numbers = sorted(list(all_numbers))
    return f"Strongest {len(sorted_numbers)} Numbers (Sorted Lowest to Highest): {', '.join(map(str, sorted_numbers))}"

# Line 1 (start of updated function)
def analyze_spins(spins_input, reset_scores, strategy_name, neighbours_count, *checkbox_args):
    try:
        print(f"analyze_spins: Starting with spins_input='{spins_input}', strategy_name='{strategy_name}', neighbours_count={neighbours_count}")
        if not spins_input or not spins_input.strip():
            print("analyze_spins: No spins input provided.")
            return "Please enter at least one number (e.g., 5, 12, 0).", "", "", "", "", "", "", "", "", "", "", "", "", "", "<h4>Wheel Section Balance</h4><p>No spins yet to compare left and right sides.</p>"

        raw_spins = [spin.strip() for spin in spins_input.split(",") if spin.strip()]
        spins = []
        errors = []

        for spin in raw_spins:
            try:
                num = int(spin)
                if not (0 <= num <= 36):
                    errors.append(f"Error: '{spin}' is out of range. Use numbers between 0 and 36.")
                    continue
                spins.append(str(num))
            except ValueError:
                errors.append(f"Error: '{spin}' is not a valid number. Use whole numbers (e.g., 5, 12, 0).")
                continue

        if errors:
            error_msg = "\n".join(errors)
            print(f"analyze_spins: Errors found - {error_msg}")
            return error_msg, "", "", "", "", "", "", "", "", "", "", "", "", "", "<h4>Wheel Section Balance</h4><p>Some inputs failed.</p>"

        if not spins:
            print("analyze_spins: No valid spins found.")
            return "No valid numbers found. Please enter numbers like '5, 12, 0'.", "", "", "", "", "", "", "", "", "", "", "", "", "", "<h4>Wheel Section Balance</h4><p>No spins yet to compare left and right sides.</p>"

        if reset_scores:
            state.reset()
            print("analyze_spins: Scores reset.")

        # Debug: Log side scores before update
        print(f"analyze_spins: Before update - side_scores = {state.side_scores}")

        # Batch update scores
        action_log = update_scores_batch(spins)

        # Generate spin analysis output
        spin_results = []
        state.selected_numbers.clear()  # Clear before rebuilding
        for idx, spin in enumerate(spins):
            spin_value = int(spin)
            hit_sections = []
            action = action_log[idx]

            # Reconstruct hit sections from increments
            for name, increment in action["increments"].get("even_money_scores", {}).items():
                if increment > 0:
                    hit_sections.append(name)
            for name, increment in action["increments"].get("dozen_scores", {}).items():
                if increment > 0:
                    hit_sections.append(name)
            for name, increment in action["increments"].get("column_scores", {}).items():
                if increment > 0:
                    hit_sections.append(name)
            for name, increment in action["increments"].get("street_scores", {}).items():
                if increment > 0:
                    hit_sections.append(name)
            for name, increment in action["increments"].get("corner_scores", {}).items():
                if increment > 0:
                    hit_sections.append(name)
            for name, increment in action["increments"].get("six_line_scores", {}).items():
                if increment > 0:
                    hit_sections.append(name)
            for name, increment in action["increments"].get("split_scores", {}).items():
                if increment > 0:
                    hit_sections.append(name)
            if spin_value in action["increments"].get("scores", {}):
                hit_sections.append(f"Straight Up {spin}")
            for name, increment in action["increments"].get("side_scores", {}).items():
                if increment > 0:
                    hit_sections.append(name)

            # Add neighbor information
            if spin_value in current_neighbors:
                left, right = current_neighbors[spin_value]
                hit_sections.append(f"Left Neighbor: {left}")
                hit_sections.append(f"Right Neighbor: {right}")

            spin_results.append(f"Spin {spin} hits: {', '.join(hit_sections)}\nTotal sections hit: {len(hit_sections)}")
            state.last_spins.append(spin)
            state.spin_history.append(action)
            # Limit spin history to 100 spins
            if len(state.spin_history) > 100:
                state.spin_history.pop(0)
        state.selected_numbers = set(int(s) for s in state.last_spins if s.isdigit())  # Sync with last_spins

        spin_analysis_output = "\n".join(spin_results)
        print(f"analyze_spins: spin_analysis_output='{spin_analysis_output}'")
        even_money_output = "Even Money Bets:\n" + "\n".join(f"{name}: {score}" for name, score in state.even_money_scores.items())
        print(f"analyze_spins: even_money_output='{even_money_output}'")
        dozens_output = "Dozens:\n" + "\n".join(f"{name}: {score}" for name, score in state.dozen_scores.items())
        print(f"analyze_spins: dozens_output='{dozens_output}'")
        columns_output = "Columns:\n" + "\n".join(f"{name}: {score}" for name, score in state.column_scores.items())
        print(f"analyze_spins: columns_output='{columns_output}'")
        streets_output = "Streets:\n" + "\n".join(f"{name}: {score}" for name, score in state.street_scores.items() if score > 0)
        print(f"analyze_spins: streets_output='{streets_output}'")
        corners_output = "Corners:\n" + "\n".join(f"{name}: {score}" for name, score in state.corner_scores.items() if score > 0)
        print(f"analyze_spins: corners_output='{corners_output}'")
        six_lines_output = "Double Streets:\n" + "\n".join(f"{name}: {score}" for name, score in state.six_line_scores.items() if score > 0)
        print(f"analyze_spins: six_lines_output='{six_lines_output}'")
        splits_output = "Splits:\n" + "\n".join(f"{name}: {score}" for name, score in state.split_scores.items() if score > 0)
        print(f"analyze_spins: splits_output='{splits_output}'")
        sides_output = "Sides of Zero:\n" + "\n".join(f"{name}: {score}" for name, score in state.side_scores.items())
        print(f"analyze_spins: sides_output='{sides_output}'")

        straight_up_df = pd.DataFrame(list(state.scores.items()), columns=["Number", "Score"])
        straight_up_df = straight_up_df[straight_up_df["Score"] > 0].sort_values(by="Score", ascending=False)
        straight_up_df["Left Neighbor"] = straight_up_df["Number"].apply(lambda x: current_neighbors[x][0] if x in current_neighbors else "")
        straight_up_df["Right Neighbor"] = straight_up_df["Number"].apply(lambda x: current_neighbors[x][1] if x in current_neighbors else "")
        straight_up_html = create_html_table(straight_up_df[["Number", "Left Neighbor", "Right Neighbor", "Score"]], "Strongest Numbers")
        print(f"analyze_spins: straight_up_html generated")

        top_18_df = straight_up_df.head(18).sort_values(by="Number", ascending=True)
        numbers = top_18_df["Number"].tolist()
        if len(numbers) < 18:
            numbers.extend([""] * (18 - len(numbers)))
        grid_data = [numbers[i::3] for i in range(3)]
        top_18_html = "<h3>Top 18 Strongest Numbers (Sorted Lowest to Highest)</h3>"
        top_18_html += '<table border="1" style="border-collapse: collapse; text-align: center;">'
        for row in grid_data:
            top_18_html += "<tr>"
            for num in row:
                top_18_html += f'<td style="padding: 5px; width: 40px;">{num}</td>'
            top_18_html += "</tr>"
        top_18_html += "</table>"
        print(f"analyze_spins: top_18_html generated")

        strongest_numbers_output = get_strongest_numbers_with_neighbors(3)
        print(f"analyze_spins: strongest_numbers_output='{strongest_numbers_output}'")

        dynamic_table_html = create_dynamic_table(strategy_name, neighbours_count)
        print(f"analyze_spins: dynamic_table_html generated")

        strategy_output = show_strategy_recommendations(strategy_name, neighbours_count, *checkbox_args)
        print(f"analyze_spins: Strategy output = {strategy_output}")

        # Debug: Log side scores after update
        print(f"analyze_spins: After update - side_scores = {state.side_scores}, spins = {spins}")

        return (spin_analysis_output, even_money_output, dozens_output, columns_output,
                streets_output, corners_output, six_lines_output, splits_output, sides_output,
                straight_up_html, top_18_html, strongest_numbers_output, dynamic_table_html, strategy_output,
                create_wheel_balance_bar())
    except Exception as e:
        print(f"analyze_spins: Unexpected error: {str(e)}")
        return f"Unexpected error while analyzing spins: {str(e)}. Please try again.", "", "", "", "", "", "", "", "", "", "", "", "", ""

# Function to reset scores
def reset_scores():
    state.reset()
    return "Scores reset!"

def undo_last_spin(current_spins_display, undo_count, strategy_name, neighbours_count, strong_numbers_count, *checkbox_args):
    if not state.spin_history:
        return ("No spins to undo.", "", "", "", "", "", "", "", "", "", "", current_spins_display, current_spins_display, "", create_dynamic_table(strategy_name, neighbours_count, strong_numbers_count), "", create_color_code_table(), update_spin_counter(), "<h4>Wheel Section Balance</h4><p>No spins yet to compare left and right sides.</p>")

    try:
        undo_count = int(undo_count)
        if undo_count <= 0:
            return ("Please select a positive number of spins to undo.", "", "", "", "", "", "", "", "", "", "", current_spins_display, current_spins_display, "", create_dynamic_table(strategy_name, neighbours_count, strong_numbers_count), "", create_color_code_table())
        undo_count = min(undo_count, len(state.spin_history))  # Don't exceed history length

        # Undo the specified number of spins
        undone_spins = []
        for _ in range(undo_count):
            if not state.spin_history:
                break
            action = state.spin_history.pop()
            spin_value = action["spin"]
            undone_spins.append(str(spin_value))

            # Decrement scores based on recorded increments
            for category, increments in action["increments"].items():
                score_dict = getattr(state, category)
                for key, value in increments.items():
                    score_dict[key] -= value
                    if score_dict[key] < 0:  # Prevent negative scores
                        score_dict[key] = 0

            state.last_spins.pop()  # Remove from last_spins too

        spins_input = ", ".join(state.last_spins) if state.last_spins else ""
        spin_analysis_output = f"Undo successful: Removed {undo_count} spin(s) - {', '.join(undone_spins)}"

        even_money_output = "Even Money Bets:\n" + "\n".join(f"{name}: {score}" for name, score in state.even_money_scores.items())
        dozens_output = "Dozens:\n" + "\n".join(f"{name}: {score}" for name, score in state.dozen_scores.items())
        columns_output = "Columns:\n" + "\n".join(f"{name}: {score}" for name, score in state.column_scores.items())
        streets_output = "Streets:\n" + "\n".join(f"{name}: {score}" for name, score in state.street_scores.items() if score > 0)
        corners_output = "Corners:\n" + "\n".join(f"{name}: {score}" for name, score in state.corner_scores.items() if score > 0)
        six_lines_output = "Double Streets:\n" + "\n".join(f"{name}: {score}" for name, score in state.six_line_scores.items() if score > 0)
        splits_output = "Splits:\n" + "\n".join(f"{name}: {score}" for name, score in state.split_scores.items() if score > 0)
        sides_output = "Sides of Zero:\n" + "\n".join(f"{name}: {score}" for name, score in state.side_scores.items())

        straight_up_df = pd.DataFrame(list(state.scores.items()), columns=["Number", "Score"])
        straight_up_df = straight_up_df[straight_up_df["Score"] > 0].sort_values(by="Score", ascending=False)
        straight_up_df["Left Neighbor"] = straight_up_df["Number"].apply(lambda x: current_neighbors[x][0] if x in current_neighbors else "")
        straight_up_df["Right Neighbor"] = straight_up_df["Number"].apply(lambda x: current_neighbors[x][1] if x in current_neighbors else "")
        straight_up_html = create_html_table(straight_up_df[["Number", "Left Neighbor", "Right Neighbor", "Score"]], "Strongest Numbers")

        top_18_df = straight_up_df.head(18).sort_values(by="Number", ascending=True)
        numbers = top_18_df["Number"].tolist()
        if len(numbers) < 18:
            numbers.extend([""] * (18 - len(numbers)))
        grid_data = [numbers[i::3] for i in range(3)]
        top_18_html = "<h3>Top 18 Strongest Numbers (Sorted Lowest to Highest)</h3>"
        top_18_html += '<table border="1" style="border-collapse: collapse; text-align: center;">'
        for row in grid_data:
            top_18_html += "<tr>"
            for num in row:
                top_18_html += f'<td style="padding: 5px; width: 40px;">{num}</td>'
            top_18_html += "</tr>"
        top_18_html += "</table>"

        strongest_numbers_output = get_strongest_numbers_with_neighbors(3)
        dynamic_table_html = create_dynamic_table(strategy_name, neighbours_count, strong_numbers_count)

        print(f"undo_last_spin: Generating strategy recommendations for {strategy_name}")
        strategy_output = show_strategy_recommendations(strategy_name, neighbours_count, strong_numbers_count, *checkbox_args)

        return (spin_analysis_output, even_money_output, dozens_output, columns_output,
            streets_output, corners_output, six_lines_output, splits_output, sides_output,
            straight_up_html, top_18_html, strongest_numbers_output, spins_input, spins_input,
            dynamic_table_html, strategy_output, create_color_code_table(), update_spin_counter())
    except ValueError:
        return ("Error: Invalid undo count. Please use a positive number.", "", "", "", "", "", "", "", "", "", "", current_spins_display, current_spins_display, "", create_dynamic_table(strategy_name, neighbours_count, strong_numbers_count), "", create_color_code_table())
    except Exception as e:
        print(f"undo_last_spin: Unexpected error: {str(e)}")
        return (f"Unexpected error during undo: {str(e)}", "", "", "", "", "", "", "", "", "", "", current_spins_display, current_spins_display, "", create_dynamic_table(strategy_name, neighbours_count, strong_numbers_count), "", create_color_code_table())

def clear_all():
    state.selected_numbers.clear()
    state.last_spins = []
    state.reset()
    return "", "", "All spins and scores cleared successfully!", "", "", "", "", "", "", "", "", "", "", "", "", update_spin_counter()

def reset_strategy_dropdowns():
    default_category = "Even Money Strategies"
    default_strategy = "Best Even Money Bets"
    strategy_choices = strategy_categories[default_category]
    return default_category, default_strategy, strategy_choices

def generate_random_spins(num_spins, current_spins_display, last_spin_count):
    try:
        num_spins = int(num_spins)
        if num_spins <= 0:
            return current_spins_display, current_spins_display, "Please select a number of spins greater than 0.", update_spin_counter()

        new_spins = [str(random.randint(0, 36)) for _ in range(num_spins)]
        if current_spins_display and current_spins_display.strip():
            current_spins = current_spins_display.split(", ")
            updated_spins = current_spins + new_spins
        else:
            updated_spins = new_spins

        # Update state.last_spins
        state.last_spins = updated_spins  # Replace the list entirely
        spins_text = ", ".join(updated_spins)
        print(f"generate_random_spins: Setting spins_textbox to '{spins_text}'")
        return spins_text, spins_text, f"Generated {num_spins} random spins: {', '.join(new_spins)}", update_spin_counter()
    except ValueError:
        print("generate_random_spins: Invalid number of spins entered.")
        return current_spins_display, current_spins_display, "Please enter a valid number of spins.", update_spin_counter()
    except Exception as e:
        print(f"generate_random_spins: Unexpected error: {str(e)}")
        return current_spins_display, current_spins_display, f"Error generating spins: {str(e)}", update_spin_counter()

# Strategy functions
def best_even_money_bets():
    recommendations = []
    sorted_even_money = sorted(state.even_money_scores.items(), key=lambda x: x[1], reverse=True)
    even_money_hits = [item for item in sorted_even_money if item[1] > 0]
    
    if not even_money_hits:
        recommendations.append("Best Even Money Bets: No hits yet.")
        return "\n".join(recommendations)

    # Collect the top 3 bets, including ties
    top_bets = []
    scores_seen = set()
    for name, score in sorted_even_money:
        if len(top_bets) < 3 or score in scores_seen:
            top_bets.append((name, score))
            scores_seen.add(score)
        else:
            break

    # Display the top 3 bets
    recommendations.append("Best Even Money Bets (Top 3):")
    for i, (name, score) in enumerate(top_bets[:3], 1):
        recommendations.append(f"{i}. {name}: {score}")

    # Check for ties among the top 3 positions
    if len(top_bets) > 1:
        # Check for ties at the 1st position
        first_score = top_bets[0][1]
        tied_first = [name for name, score in top_bets if score == first_score]
        if len(tied_first) > 1:
            recommendations.append(f"Note: Tie for 1st place among {', '.join(tied_first)} with score {first_score}")

        # Check for ties at the 2nd position
        if len(top_bets) > 1:
            second_score = top_bets[1][1]
            tied_second = [name for name, score in top_bets if score == second_score]
            if len(tied_second) > 1:
                recommendations.append(f"Note: Tie for 2nd place among {', '.join(tied_second)} with score {second_score}")

        # Check for ties at the 3rd position
        if len(top_bets) > 2:
            third_score = top_bets[2][1]
            tied_third = [name for name, score in top_bets if score == third_score]
            if len(tied_third) > 1:
                recommendations.append(f"Note: Tie for 3rd place among {', '.join(tied_third)} with score {third_score}")

    return "\n".join(recommendations)

def hot_bet_strategy():
    recommendations = []
    sorted_even_money = sorted(state.even_money_scores.items(), key=lambda x: x[1], reverse=True)
    even_money_hits = [item for item in sorted_even_money if item[1] > 0]
    if even_money_hits:
        recommendations.append("Even Money (Top 2):")
        for i, (name, score) in enumerate(even_money_hits[:2], 1):
            recommendations.append(f"{i}. {name}: {score}")
    else:
        recommendations.append("Even Money: No hits yet.")

    sorted_dozens = sorted(state.dozen_scores.items(), key=lambda x: x[1], reverse=True)
    dozens_hits = [item for item in sorted_dozens if item[1] > 0]
    if dozens_hits:
        recommendations.append("\nDozens (Top 2):")
        for i, (name, score) in enumerate(dozens_hits[:2], 1):
            recommendations.append(f"{i}. {name}: {score}")
    else:
        recommendations.append("\nDozens: No hits yet.")

    sorted_columns = sorted(state.column_scores.items(), key=lambda x: x[1], reverse=True)
    columns_hits = [item for item in sorted_columns if item[1] > 0]
    if columns_hits:
        recommendations.append("\nColumns (Top 2):")
        for i, (name, score) in enumerate(columns_hits[:2], 1):
            recommendations.append(f"{i}. {name}: {score}")
    else:
        recommendations.append("\nColumns: No hits yet.")

    sorted_streets = sorted(state.street_scores.items(), key=lambda x: x[1], reverse=True)
    streets_hits = [item for item in sorted_streets if item[1] > 0]
    if streets_hits:
        recommendations.append("\nStreets (Ranked):")
        for i, (name, score) in enumerate(streets_hits, 1):
            recommendations.append(f"{i}. {name}: {score}")
    else:
        recommendations.append("\nStreets: No hits yet.")

    sorted_corners = sorted(state.corner_scores.items(), key=lambda x: x[1], reverse=True)
    corners_hits = [item for item in sorted_corners if item[1] > 0]
    if corners_hits:
        recommendations.append("\nCorners (Ranked):")
        for i, (name, score) in enumerate(corners_hits, 1):
            recommendations.append(f"{i}. {name}: {score}")
    else:
        recommendations.append("\nCorners: No hits yet.")

    sorted_six_lines = sorted(state.six_line_scores.items(), key=lambda x: x[1], reverse=True)
    six_lines_hits = [item for item in sorted_six_lines if item[1] > 0]
    if six_lines_hits:
        recommendations.append("\nDouble Streets (Ranked):")
        for i, (name, score) in enumerate(six_lines_hits, 1):
            recommendations.append(f"{i}. {name}: {score}")
    else:
        recommendations.append("\nDouble Streets: No hits yet.")

    sorted_splits = sorted(state.split_scores.items(), key=lambda x: x[1], reverse=True)
    splits_hits = [item for item in sorted_splits if item[1] > 0]
    if splits_hits:
        recommendations.append("\nSplits (Ranked):")
        for i, (name, score) in enumerate(splits_hits, 1):
            recommendations.append(f"{i}. {name}: {score}")
    else:
        recommendations.append("\nSplits: No hits yet.")

    sorted_sides = sorted(state.side_scores.items(), key=lambda x: x[1], reverse=True)
    sides_hits = [item for item in sorted_sides if item[1] > 0]
    if sides_hits:
        recommendations.append("\nSides of Zero:")
        recommendations.append(f"1. {sides_hits[0][0]}: {sides_hits[0][1]}")
    else:
        recommendations.append("\nSides of Zero: No hits yet.")

    sorted_numbers = sorted(state.scores.items(), key=lambda x: x[1], reverse=True)
    numbers_hits = [item for item in sorted_numbers if item[1] > 0]
    if numbers_hits:
        number_best = numbers_hits[0]
        left_neighbor, right_neighbor = current_neighbors[number_best[0]]
        recommendations.append(f"\nStrongest Number: {number_best[0]} (Score: {number_best[1]}) with neighbors {left_neighbor} and {right_neighbor}")
    else:
        recommendations.append("\nStrongest Number: No hits yet.")

    return "\n".join(recommendations)

# Function for Cold Bet Strategy
def cold_bet_strategy():
    recommendations = []
    sorted_even_money = sorted(state.even_money_scores.items(), key=lambda x: x[1])
    even_money_non_hits = [item for item in sorted_even_money if item[1] == 0]
    even_money_hits = [item for item in sorted_even_money if item[1] > 0]
    if even_money_non_hits:
        recommendations.append("Even Money (Not Hit):")
        recommendations.append(", ".join(item[0] for item in even_money_non_hits))
    if even_money_hits:
        recommendations.append("\nEven Money (Lowest Scores):")
        for i, (name, score) in enumerate(even_money_hits[:2], 1):
            recommendations.append(f"{i}. {name}: {score}")

    sorted_dozens = sorted(state.dozen_scores.items(), key=lambda x: x[1])
    dozens_non_hits = [item for item in sorted_dozens if item[1] == 0]
    dozens_hits = [item for item in sorted_dozens if item[1] > 0]
    if dozens_non_hits:
        recommendations.append("\nDozens (Not Hit):")
        recommendations.append(", ".join(item[0] for item in dozens_non_hits))
    if dozens_hits:
        recommendations.append("\nDozens (Lowest Scores):")
        for i, (name, score) in enumerate(dozens_hits[:2], 1):
            recommendations.append(f"{i}. {name}: {score}")

    sorted_columns = sorted(state.column_scores.items(), key=lambda x: x[1])
    columns_non_hits = [item for item in sorted_columns if item[1] == 0]
    columns_hits = [item for item in sorted_columns if item[1] > 0]
    if columns_non_hits:
        recommendations.append("\nColumns (Not Hit):")
        recommendations.append(", ".join(item[0] for item in columns_non_hits))
    if columns_hits:
        recommendations.append("\nColumns (Lowest Scores):")
        for i, (name, score) in enumerate(columns_hits[:2], 1):
            recommendations.append(f"{i}. {name}: {score}")

    sorted_streets = sorted(state.street_scores.items(), key=lambda x: x[1])
    streets_non_hits = [item for item in sorted_streets if item[1] == 0]
    streets_hits = [item for item in sorted_streets if item[1] > 0]
    if streets_non_hits:
        recommendations.append("\nStreets (Not Hit):")
        recommendations.append(", ".join(item[0] for item in streets_non_hits))
    if streets_hits:
        recommendations.append("\nStreets (Lowest Scores):")
        for i, (name, score) in enumerate(streets_hits[:3], 1):
            recommendations.append(f"{i}. {name}: {score}")

    sorted_corners = sorted(state.corner_scores.items(), key=lambda x: x[1])
    corners_non_hits = [item for item in sorted_corners if item[1] == 0]
    corners_hits = [item for item in sorted_corners if item[1] > 0]
    if corners_non_hits:
        recommendations.append("\nCorners (Not Hit):")
        recommendations.append(", ".join(item[0] for item in corners_non_hits))
    if corners_hits:
        recommendations.append("\nCorners (Lowest Scores):")
        for i, (name, score) in enumerate(corners_hits[:3], 1):
            recommendations.append(f"{i}. {name}: {score}")

    sorted_six_lines = sorted(state.six_line_scores.items(), key=lambda x: x[1])
    six_lines_non_hits = [item for item in sorted_six_lines if item[1] == 0]
    six_lines_hits = [item for item in sorted_six_lines if item[1] > 0]
    if six_lines_non_hits:
        recommendations.append("\nDouble Streets (Not Hit):")
        recommendations.append(", ".join(item[0] for item in six_lines_non_hits))
    if six_lines_hits:
        recommendations.append("\nDouble Streets (Lowest Scores):")
        for i, (name, score) in enumerate(six_lines_hits[:3], 1):
            recommendations.append(f"{i}. {name}: {score}")

    sorted_splits = sorted(state.split_scores.items(), key=lambda x: x[1])
    splits_non_hits = [item for item in sorted_splits if item[1] == 0]
    splits_hits = [item for item in sorted_splits if item[1] > 0]
    if splits_non_hits:
        recommendations.append("\nSplits (Not Hit):")
        recommendations.append(", ".join(item[0] for item in splits_non_hits))
    if splits_hits:
        recommendations.append("\nSplits (Lowest Scores):")
        for i, (name, score) in enumerate(splits_hits[:3], 1):
            recommendations.append(f"{i}. {name}: {score}")

    sorted_sides = sorted(state.side_scores.items(), key=lambda x: x[1])
    sides_non_hits = [item for item in sorted_sides if item[1] == 0]
    sides_hits = [item for item in sorted_sides if item[1] > 0]
    if sides_non_hits:
        recommendations.append("\nSides of Zero (Not Hit):")
        recommendations.append(", ".join(item[0] for item in sides_non_hits))
    if sides_hits:
        recommendations.append("\nSides of Zero (Lowest Score):")
        recommendations.append(f"1. {sides_hits[0][0]}: {sides_hits[0][1]}")

    sorted_numbers = sorted(state.scores.items(), key=lambda x: x[1])
    numbers_non_hits = [item for item in sorted_numbers if item[1] == 0]
    numbers_hits = [item for item in sorted_numbers if item[1] > 0]
    if numbers_non_hits:
        recommendations.append("\nNumbers (Not Hit):")
        recommendations.append(", ".join(str(item[0]) for item in numbers_non_hits))
    if numbers_hits:
        number_worst = numbers_hits[0]
        left_neighbor, right_neighbor = current_neighbors[number_worst[0]]
        recommendations.append(f"\nColdest Number: {number_worst[0]} (Score: {number_worst[1]}) with neighbors {left_neighbor} and {right_neighbor}")

    return "\n".join(recommendations)

def best_dozens():
    recommendations = []
    sorted_dozens = sorted(state.dozen_scores.items(), key=lambda x: x[1], reverse=True)
    dozens_hits = [item for item in sorted_dozens if item[1] > 0]
    if dozens_hits:
        recommendations.append("Best Dozens (Top 2):")
        for i, (name, score) in enumerate(dozens_hits[:2], 1):
            recommendations.append(f"{i}. {name}: {score}")
    else:
        recommendations.append("Best Dozens: No hits yet.")
    return "\n".join(recommendations)

def best_columns():
    recommendations = []
    sorted_columns = sorted(state.column_scores.items(), key=lambda x: x[1], reverse=True)
    columns_hits = [item for item in sorted_columns if item[1] > 0]
    if columns_hits:
        recommendations.append("Best Columns (Top 2):")
        for i, (name, score) in enumerate(columns_hits[:2], 1):
            recommendations.append(f"{i}. {name}: {score}")
    else:
        recommendations.append("Best Columns: No hits yet.")
    return "\n".join(recommendations)

def fibonacci_strategy():
    recommendations = []
    sorted_dozens = sorted(state.dozen_scores.items(), key=lambda x: x[1], reverse=True)
    dozens_hits = [item for item in sorted_dozens if item[1] > 0]
    sorted_columns = sorted(state.column_scores.items(), key=lambda x: x[1], reverse=True)
    columns_hits = [item for item in sorted_columns if item[1] > 0]

    if not dozens_hits and not columns_hits:
        recommendations.append("Fibonacci Strategy: No hits in Dozens or Columns yet.")
        return "\n".join(recommendations)

    best_dozen_score = dozens_hits[0][1] if dozens_hits else 0
    best_column_score = columns_hits[0][1] if columns_hits else 0

    if best_dozen_score > best_column_score:
        recommendations.append("Best Category: Dozens")
        recommendations.append(f"Best Dozen: {dozens_hits[0][0]} (Score: {dozens_hits[0][1]})")
    elif best_column_score > best_dozen_score:
        recommendations.append("Best Category: Columns")
        recommendations.append(f"Best Column: {columns_hits[0][0]} (Score: {columns_hits[0][1]})")
    else:
        recommendations.append(f"Best Category (Tied): Dozens and Columns (Score: {best_dozen_score})")
        if dozens_hits:
            recommendations.append(f"Best Dozen: {dozens_hits[0][0]} (Score: {dozens_hits[0][1]})")
        if columns_hits:
            recommendations.append(f"Best Column: {columns_hits[0][0]} (Score: {columns_hits[0][1]})")

    return "\n".join(recommendations)

def best_streets():
    recommendations = []
    sorted_streets = sorted(state.street_scores.items(), key=lambda x: x[1], reverse=True)
    streets_hits = [item for item in sorted_streets if item[1] > 0]

    if not streets_hits:
        recommendations.append("Best Streets: No hits yet.")
        return "\n".join(recommendations)

    recommendations.append("Top 3 Streets:")
    for i, (name, score) in enumerate(streets_hits[:3], 1):
        recommendations.append(f"{i}. {name}: {score}")

    recommendations.append("\nTop 6 Streets:")
    for i, (name, score) in enumerate(streets_hits[:6], 1):
        recommendations.append(f"{i}. {name}: {score}")

    return "\n".join(recommendations)

def best_double_streets():
    recommendations = []
    sorted_six_lines = sorted(state.six_line_scores.items(), key=lambda x: x[1], reverse=True)
    six_lines_hits = [item for item in sorted_six_lines if item[1] > 0]

    if not six_lines_hits:
        recommendations.append("Best Double Streets: No hits yet.")
        return "\n".join(recommendations)

    recommendations.append("Double Streets (Ranked):")
    for i, (name, score) in enumerate(six_lines_hits, 1):
        recommendations.append(f"{i}. {name}: {score}")

    return "\n".join(recommendations)

def best_corners():
    recommendations = []
    sorted_corners = sorted(state.corner_scores.items(), key=lambda x: x[1], reverse=True)
    corners_hits = [item for item in sorted_corners if item[1] > 0]

    if not corners_hits:
        recommendations.append("Best Corners: No hits yet.")
        return "\n".join(recommendations)

    recommendations.append("Corners (Ranked):")
    for i, (name, score) in enumerate(corners_hits, 1):
        recommendations.append(f"{i}. {name}: {score}")

    return "\n".join(recommendations)

def best_splits():
    recommendations = []
    sorted_splits = sorted(state.split_scores.items(), key=lambda x: x[1], reverse=True)
    splits_hits = [item for item in sorted_splits if item[1] > 0]

    if not splits_hits:
        recommendations.append("Best Splits: No hits yet.")
        return "\n".join(recommendations)

    recommendations.append("Splits (Ranked):")
    for i, (name, score) in enumerate(splits_hits, 1):
        recommendations.append(f"{i}. {name}: {score}")

    return "\n".join(recommendations)

def best_dozens_and_streets():
    recommendations = []
    sorted_dozens = sorted(state.dozen_scores.items(), key=lambda x: x[1], reverse=True)
    dozens_hits = [item for item in sorted_dozens if item[1] > 0]
    if dozens_hits:
        recommendations.append("Best Dozens (Top 2):")
        for i, (name, score) in enumerate(dozens_hits[:2], 1):
            recommendations.append(f"{i}. {name}: {score}")
    else:
        recommendations.append("Best Dozens: No hits yet.")

    sorted_streets = sorted(state.street_scores.items(), key=lambda x: x[1], reverse=True)
    streets_hits = [item for item in sorted_streets if item[1] > 0]
    if streets_hits:
        recommendations.append("\nTop 3 Streets (Yellow):")
        for i, (name, score) in enumerate(streets_hits[:3], 1):
            recommendations.append(f"{i}. {name}: {score}")
        recommendations.append("\nMiddle 3 Streets (Cyan):")
        for i, (name, score) in enumerate(streets_hits[3:6], 1):
            recommendations.append(f"{i}. {name}: {score}")
        recommendations.append("\nBottom 3 Streets (Green):")
        for i, (name, score) in enumerate(streets_hits[6:9], 1):
            recommendations.append(f"{i}. {name}: {score}")
    else:
        recommendations.append("\nBest Streets: No hits yet.")

    return "\n".join(recommendations)

def best_columns_and_streets():
    recommendations = []
    sorted_columns = sorted(state.column_scores.items(), key=lambda x: x[1], reverse=True)
    columns_hits = [item for item in sorted_columns if item[1] > 0]
    if columns_hits:
        recommendations.append("Best Columns (Top 2):")
        for i, (name, score) in enumerate(columns_hits[:2], 1):
            recommendations.append(f"{i}. {name}: {score}")
    else:
        recommendations.append("Best Columns: No hits yet.")

    sorted_streets = sorted(state.street_scores.items(), key=lambda x: x[1], reverse=True)
    streets_hits = [item for item in sorted_streets if item[1] > 0]
    if streets_hits:
        recommendations.append("\nTop 3 Streets (Yellow):")
        for i, (name, score) in enumerate(streets_hits[:3], 1):
            recommendations.append(f"{i}. {name}: {score}")
        recommendations.append("\nMiddle 3 Streets (Cyan):")
        for i, (name, score) in enumerate(streets_hits[3:6], 1):
            recommendations.append(f"{i}. {name}: {score}")
        recommendations.append("\nBottom 3 Streets (Green):")
        for i, (name, score) in enumerate(streets_hits[6:9], 1):
            recommendations.append(f"{i}. {name}: {score}")
    else:
        recommendations.append("\nBest Streets: No hits yet.")

    return "\n".join(recommendations)

def non_overlapping_double_street_strategy():
    non_overlapping_sets = [
        ["1ST D.STREET – 1, 4", "3RD D.STREET – 7, 10", "5TH D.STREET – 13, 16", "7TH D.STREET – 19, 22", "9TH D.STREET – 25, 28"],
        ["2ND D.STREET – 4, 7", "4TH D.STREET – 10, 13", "6TH D.STREET – 16, 19", "8TH D.STREET – 22, 25", "10TH D.STREET – 28, 31"]
    ]

    set_scores = []
    for idx, non_overlapping_set in enumerate(non_overlapping_sets):
        total_score = sum(state.six_line_scores[name] for name in non_overlapping_set)
        set_scores.append((idx, total_score, non_overlapping_set))

    best_set = max(set_scores, key=lambda x: x[1])
    best_set_idx, best_set_score, best_set_streets = best_set

    sorted_streets = sorted(best_set_streets, key=lambda name: state.six_line_scores[name], reverse=True)

    recommendations = []
    recommendations.append(f"Non-Overlapping Double Streets Strategy (Set {best_set_idx + 1} with Total Score: {best_set_score})")
    recommendations.append("Hottest Non-Overlapping Double Streets (Sorted by Hotness):")
    for i, name in enumerate(sorted_streets, 1):
        score = state.six_line_scores[name]
        recommendations.append(f"{i}. {name}: {score}")

    return "\n".join(recommendations)

def non_overlapping_corner_strategy():
    non_overlapping_sets = [
        ["1ST CORNER – 1, 2, 4, 5", "5TH CORNER – 7, 8, 10, 11", "9TH CORNER – 13, 14, 16, 17", "13TH CORNER – 19, 20, 22, 23", "17TH CORNER – 25, 26, 28, 29", "21ST CORNER – 31, 32, 34, 35"],
        ["2ND CORNER – 2, 3, 5, 6", "6TH CORNER – 8, 9, 11, 12", "10TH CORNER – 14, 15, 17, 18", "14TH CORNER – 20, 21, 23, 24", "18TH CORNER – 26, 27, 29, 30", "22ND CORNER – 32, 33, 35, 36"]
    ]

    set_scores = []
    for idx, non_overlapping_set in enumerate(non_overlapping_sets):
        total_score = sum(state.corner_scores[name] for name in non_overlapping_set)
        set_scores.append((idx, total_score, non_overlapping_set))

    best_set = max(set_scores, key=lambda x: x[1])
    best_set_idx, best_set_score, best_set_corners = best_set

    sorted_corners = sorted(best_set_corners, key=lambda name: state.corner_scores[name], reverse=True)

    recommendations = []
    recommendations.append(f"Non-Overlapping Corner Strategy (Set {best_set_idx + 1} with Total Score: {best_set_score})")
    recommendations.append("Hottest Non-Overlapping Corners (Sorted by Hotness):")
    for i, name in enumerate(sorted_corners, 1):
        score = state.corner_scores[name]
        recommendations.append(f"{i}. {name}: {score}")

    return "\n".join(recommendations)

def romanowksy_missing_dozen_strategy():
    recommendations = []
    sorted_dozens = sorted(state.dozen_scores.items(), key=lambda x: x[1], reverse=True)
    dozens_hits = [item for item in sorted_dozens if item[1] > 0]
    dozens_no_hits = [item for item in sorted_dozens if item[1] == 0]

    if not dozens_hits and not dozens_no_hits:
        recommendations.append("Romanowksy Missing Dozen Strategy: No spins recorded yet.")
        return "\n".join(recommendations)

    if len(dozens_hits) < 2:
        recommendations.append("Romanowksy Missing Dozen Strategy: Not enough dozens have hit yet.")
        if dozens_hits:
            recommendations.append(f"Hottest Dozen: {dozens_hits[0][0]} (Score: {dozens_hits[0][1]})")
        return "\n".join(recommendations)

    top_dozens = []
    scores_seen = set()
    for name, score in sorted_dozens:
        if len(top_dozens) < 2 or score in scores_seen:
            top_dozens.append((name, score))
            scores_seen.add(score)
        else:
            break

    recommendations.append("Hottest Dozens (Top 2):")
    for i, (name, score) in enumerate(top_dozens[:2], 1):
        recommendations.append(f"{i}. {name}: {score}")
    if len(top_dozens) > 2 and top_dozens[1][1] == top_dozens[2][1]:
        tied_dozens = [name for name, score in top_dozens if score == top_dozens[1][1]]
        recommendations.append(f"Note: Tie detected among {', '.join(tied_dozens)} with score {top_dozens[1][1]}")

    weakest_dozen = sorted_dozens[-1]
    weakest_dozen_name, weakest_dozen_score = weakest_dozen
    recommendations.append(f"\nWeakest Dozen: {weakest_dozen_name} (Score: {weakest_dozen_score})")

    weakest_dozen_numbers = set(DOZENS[weakest_dozen_name])
    straight_up_df = pd.DataFrame(list(state.scores.items()), columns=["Number", "Score"])
    straight_up_df = straight_up_df[straight_up_df["Score"] > 0].sort_values(by="Score", ascending=False)

    if straight_up_df.empty:
        recommendations.append("No strong numbers have hit yet in any dozen.")
        return "\n".join(recommendations)

    strong_numbers_in_weakest = []
    neighbors_in_weakest = []
    for _, row in straight_up_df.iterrows():
        number = row["Number"]
        score = row["Score"]
        if number in weakest_dozen_numbers:
            strong_numbers_in_weakest.append((number, score))
        else:
            if number in current_neighbors:
                left, right = current_neighbors[number]
                if left in weakest_dozen_numbers:
                    neighbors_in_weakest.append((left, number, score))
                if right in weakest_dozen_numbers:
                    neighbors_in_weakest.append((right, number, score))

    if strong_numbers_in_weakest:
        recommendations.append("\nStrongest Numbers in Weakest Dozen:")
        for number, score in strong_numbers_in_weakest:
            recommendations.append(f"Number {number} (Score: {score})")
    else:
        recommendations.append("\nNo strong numbers directly in the Weakest Dozen.")

    if neighbors_in_weakest:
        recommendations.append("\nNeighbors of Strong Numbers in Weakest Dozen:")
        for neighbor, strong_number, score in neighbors_in_weakest:
            recommendations.append(f"Number {neighbor} (Neighbor of {strong_number}, Score: {score})")
    else:
        if not strong_numbers_in_weakest:
            recommendations.append("No neighbors of strong numbers in the Weakest Dozen.")

    return "\n".join(recommendations)

def fibonacci_to_fortune_strategy():
    recommendations = []

    fib_recommendations = fibonacci_strategy()
    recommendations.append("Fibonacci Strategy:")
    recommendations.append(fib_recommendations)

    even_money_sorted = sorted(state.even_money_scores.items(), key=lambda x: x[1], reverse=True)
    even_money_hits = [item for item in even_money_sorted if item[1] > 0]
    if even_money_hits:
        best_even_money = even_money_hits[0]
        name, score = best_even_money
        recommendations.append("\nBest Even Money Bet:")
        recommendations.append(f"1. {name}: {score}")
    else:
        recommendations.append("\nBest Even Money Bet: No hits yet.")

    columns_sorted = sorted(state.column_scores.items(), key=lambda x: x[1], reverse=True)
    columns_hits = [item for item in columns_sorted if item[1] > 0]
    if columns_hits:
        recommendations.append("\nBest Two Columns:")
        for i, (name, score) in enumerate(columns_hits[:2], 1):
            recommendations.append(f"{i}. {name}: {score}")
    else:
        recommendations.append("\nBest Two Columns: No hits yet.")

    dozens_sorted = sorted(state.dozen_scores.items(), key=lambda x: x[1], reverse=True)
    dozens_hits = [item for item in dozens_sorted if item[1] > 0]
    if dozens_hits:
        recommendations.append("\nBest Two Dozens:")
        for i, (name, score) in enumerate(dozens_hits[:2], 1):
            recommendations.append(f"{i}. {name}: {score}")
    else:
        recommendations.append("\nBest Two Dozens: No hits yet.")

    weakest_dozen = min(state.dozen_scores.items(), key=lambda x: x[1])
    weakest_dozen_name, weakest_dozen_score = weakest_dozen
    weakest_dozen_numbers = set(DOZENS[weakest_dozen_name])

    top_two_dozens = [item[0] for item in dozens_sorted[:2]]
    top_two_dozen_numbers = set()
    for dozen_name in top_two_dozens:
        top_two_dozen_numbers.update(DOZENS[dozen_name])

    double_streets_in_weakest = []
    for name, numbers in SIX_LINES.items():
        numbers_set = set(numbers)
        if numbers_set.issubset(weakest_dozen_numbers) and not numbers_set.intersection(top_two_dozen_numbers):
            double_streets_in_weakest.append((name, state.six_line_scores[name]))

    if double_streets_in_weakest:
        double_streets_sorted = sorted(double_streets_in_weakest, key=lambda x: x[1], reverse=True)
        best_double_street = double_streets_sorted[0]
        name, score = best_double_street
        recommendations.append(f"\nBest Double Street in Weakest Dozen ({weakest_dozen_name}):")
        recommendations.append(f"1. {name}: {score}")
    else:
        recommendations.append(f"\nBest Double Street in Weakest Dozen ({weakest_dozen_name}): No suitable double street available.")

    return "\n".join(recommendations)

def three_eight_six_rising_martingale():
    recommendations = []
    sorted_streets = sorted(state.street_scores.items(), key=lambda x: x[1], reverse=True)
    streets_hits = [item for item in sorted_streets if item[1] > 0]

    if not streets_hits:
        recommendations.append("3-8-6 Rising Martingale: No streets have hit yet.")
        return "\n".join(recommendations)

    recommendations.append("Top 3 Streets (Yellow):")
    for i, (name, score) in enumerate(streets_hits[:3], 1):
        recommendations.append(f"{i}. {name}: {score}")

    recommendations.append("\nMiddle 3 Streets (Cyan):")
    for i, (name, score) in enumerate(streets_hits[3:6], 1):
        recommendations.append(f"{i}. {name}: {score}")

    recommendations.append("\nBottom 2 Streets (Green):")
    for i, (name, score) in enumerate(streets_hits[6:8], 1):
        recommendations.append(f"{i}. {name}: {score}")

    return "\n".join(recommendations)

def one_dozen_one_column_strategy():
    recommendations = []
    sorted_dozens = sorted(state.dozen_scores.items(), key=lambda x: x[1], reverse=True)
    dozens_hits = [item for item in sorted_dozens if item[1] > 0]

    if not dozens_hits:
        recommendations.append("Best Dozen: No dozens have hit yet.")
    else:
        top_score = dozens_hits[0][1]
        top_dozens = [item for item in sorted_dozens if item[1] == top_score]
        if len(top_dozens) == 1:
            recommendations.append(f"Best Dozen: {top_dozens[0][0]}")
        else:
            recommendations.append("Best Dozens (Tied):")
            for name, _ in top_dozens:
                recommendations.append(f"- {name}")

    sorted_columns = sorted(state.column_scores.items(), key=lambda x: x[1], reverse=True)
    columns_hits = [item for item in sorted_columns if item[1] > 0]

    if not columns_hits:
        recommendations.append("Best Column: No columns have hit yet.")
    else:
        top_score = columns_hits[0][1]
        top_columns = [item for item in sorted_columns if item[1] == top_score]
        if len(top_columns) == 1:
            recommendations.append(f"Best Column: {top_columns[0][0]}")
        else:
            recommendations.append("Best Columns (Tied):")
            for name, _ in top_columns:
                recommendations.append(f"- {name}")

    return "\n".join(recommendations)

def top_pick_18_numbers_without_neighbours():
    recommendations = []
    straight_up_df = pd.DataFrame(list(state.scores.items()), columns=["Number", "Score"])
    straight_up_df = straight_up_df[straight_up_df["Score"] > 0].sort_values(by="Score", ascending=False)

    if straight_up_df.empty or len(straight_up_df) < 18:
        recommendations.append("Top Pick 18 Numbers without Neighbours: Not enough numbers have hit yet (need at least 18).")
        return "\n".join(recommendations)

    top_18_df = straight_up_df.head(18)
    top_18_numbers = top_18_df["Number"].tolist()

    top_6 = top_18_numbers[:6]
    next_6 = top_18_numbers[6:12]
    last_6 = top_18_numbers[12:18]

    recommendations.append("Top Pick 18 Numbers without Neighbours:")
    recommendations.append("\nTop 6 Numbers (Yellow):")
    for i, num in enumerate(top_6, 1):
        score = top_18_df[top_18_df["Number"] == num]["Score"].iloc[0]
        recommendations.append(f"{i}. Number {num} (Score: {score})")

    recommendations.append("\nNext 6 Numbers (Blue):")
    for i, num in enumerate(next_6, 1):
        score = top_18_df[top_18_df["Number"] == num]["Score"].iloc[0]
        recommendations.append(f"{i}. Number {num} (Score: {score})")

    recommendations.append("\nLast 6 Numbers (Green):")
    for i, num in enumerate(last_6, 1):
        score = top_18_df[top_18_df["Number"] == num]["Score"].iloc[0]
        recommendations.append(f"{i}. Number {num} (Score: {score})")

    return "\n".join(recommendations)

def best_even_money_and_top_18():
    recommendations = []

    # Best Even Money Bets (Top 3 with tie handling, same as best_even_money_bets)
    sorted_even_money = sorted(state.even_money_scores.items(), key=lambda x: x[1], reverse=True)
    even_money_hits = [item for item in sorted_even_money if item[1] > 0]
    
    if even_money_hits:
        # Collect the top 3 bets, including ties
        top_bets = []
        scores_seen = set()
        for name, score in sorted_even_money:
            if len(top_bets) < 3 or score in scores_seen:
                top_bets.append((name, score))
                scores_seen.add(score)
            else:
                break

        # Display the top 3 bets
        recommendations.append("Best Even Money Bets (Top 3):")
        for i, (name, score) in enumerate(top_bets[:3], 1):
            recommendations.append(f"{i}. {name}: {score}")

        # Check for ties among the top 3 positions
        if len(top_bets) > 1:
            first_score = top_bets[0][1]
            tied_first = [name for name, score in top_bets if score == first_score]
            if len(tied_first) > 1:
                recommendations.append(f"Note: Tie for 1st place among {', '.join(tied_first)} with score {first_score}")

            if len(top_bets) > 1:
                second_score = top_bets[1][1]
                tied_second = [name for name, score in top_bets if score == second_score]
                if len(tied_second) > 1:
                    recommendations.append(f"Note: Tie for 2nd place among {', '.join(tied_second)} with score {second_score}")

            if len(top_bets) > 2:
                third_score = top_bets[2][1]
                tied_third = [name for name, score in top_bets if score == third_score]
                if len(tied_third) > 1:
                    recommendations.append(f"Note: Tie for 3rd place among {', '.join(tied_third)} with score {third_score}")
    else:
        recommendations.append("Best Even Money Bets: No hits yet.")

    # Top Pick 18 Numbers without Neighbours (same as top_pick_18_numbers_without_neighbours)
    recommendations.append("")  # Add a blank line for separation
    straight_up_df = pd.DataFrame(list(state.scores.items()), columns=["Number", "Score"])
    straight_up_df = straight_up_df[straight_up_df["Score"] > 0].sort_values(by="Score", ascending=False)

    if straight_up_df.empty or len(straight_up_df) < 18:
        recommendations.append("Top Pick 18 Numbers without Neighbours: Not enough numbers have hit yet (need at least 18).")
        return "\n".join(recommendations)

    top_18_df = straight_up_df.head(18)
    top_18_numbers = top_18_df["Number"].tolist()

    top_6 = top_18_numbers[:6]
    next_6 = top_18_numbers[6:12]
    last_6 = top_18_numbers[12:18]

    recommendations.append("Top Pick 18 Numbers without Neighbours:")
    recommendations.append("\nTop 6 Numbers (Yellow):")
    for i, num in enumerate(top_6, 1):
        score = top_18_df[top_18_df["Number"] == num]["Score"].iloc[0]
        recommendations.append(f"{i}. Number {num} (Score: {score})")

    recommendations.append("\nNext 6 Numbers (Blue):")
    for i, num in enumerate(next_6, 1):
        score = top_18_df[top_18_df["Number"] == num]["Score"].iloc[0]
        recommendations.append(f"{i}. Number {num} (Score: {score})")

    recommendations.append("\nLast 6 Numbers (Green):")
    for i, num in enumerate(last_6, 1):
        score = top_18_df[top_18_df["Number"] == num]["Score"].iloc[0]
        recommendations.append(f"{i}. Number {num} (Score: {score})")

    return "\n".join(recommendations)

def best_dozens_and_top_18():
    recommendations = []

    # Best Dozens (Top 2 with tie handling, same as best_dozens)
    sorted_dozens = sorted(state.dozen_scores.items(), key=lambda x: x[1], reverse=True)
    dozens_hits = [item for item in sorted_dozens if item[1] > 0]
    if dozens_hits:
        # Collect the top 2 dozens, including ties
        top_dozens = []
        scores_seen = set()
        for name, score in sorted_dozens:
            if len(top_dozens) < 2 or score in scores_seen:
                top_dozens.append((name, score))
                scores_seen.add(score)
            else:
                break

        # Display the top 2 dozens
        recommendations.append("Best Dozens (Top 2):")
        for i, (name, score) in enumerate(top_dozens[:2], 1):
            recommendations.append(f"{i}. {name}: {score}")

        # Check for ties among the top 2 positions
        if len(top_dozens) > 1:
            first_score = top_dozens[0][1]
            tied_first = [name for name, score in top_dozens if score == first_score]
            if len(tied_first) > 1:
                recommendations.append(f"Note: Tie for 1st place among {', '.join(tied_first)} with score {first_score}")

            if len(top_dozens) > 1:
                second_score = top_dozens[1][1]
                tied_second = [name for name, score in top_dozens if score == second_score]
                if len(tied_second) > 1:
                    recommendations.append(f"Note: Tie for 2nd place among {', '.join(tied_second)} with score {second_score}")
    else:
        recommendations.append("Best Dozens: No hits yet.")

    # Top Pick 18 Numbers without Neighbours (same as top_pick_18_numbers_without_neighbours)
    recommendations.append("")  # Add a blank line for separation
    straight_up_df = pd.DataFrame(list(state.scores.items()), columns=["Number", "Score"])
    straight_up_df = straight_up_df[straight_up_df["Score"] > 0].sort_values(by="Score", ascending=False)

    if straight_up_df.empty or len(straight_up_df) < 18:
        recommendations.append("Top Pick 18 Numbers without Neighbours: Not enough numbers have hit yet (need at least 18).")
        return "\n".join(recommendations)

    top_18_df = straight_up_df.head(18)
    top_18_numbers = top_18_df["Number"].tolist()

    top_6 = top_18_numbers[:6]
    next_6 = top_18_numbers[6:12]
    last_6 = top_18_numbers[12:18]

    recommendations.append("Top Pick 18 Numbers without Neighbours:")
    recommendations.append("\nTop 6 Numbers (Yellow):")
    for i, num in enumerate(top_6, 1):
        score = top_18_df[top_18_df["Number"] == num]["Score"].iloc[0]
        recommendations.append(f"{i}. Number {num} (Score: {score})")

    recommendations.append("\nNext 6 Numbers (Blue):")
    for i, num in enumerate(next_6, 1):
        score = top_18_df[top_18_df["Number"] == num]["Score"].iloc[0]
        recommendations.append(f"{i}. Number {num} (Score: {score})")

    recommendations.append("\nLast 6 Numbers (Green):")
    for i, num in enumerate(last_6, 1):
        score = top_18_df[top_18_df["Number"] == num]["Score"].iloc[0]
        recommendations.append(f"{i}. Number {num} (Score: {score})")

    return "\n".join(recommendations)

def best_columns_and_top_18():
    recommendations = []

    # Best Columns (Top 2 with tie handling, same as best_columns)
    sorted_columns = sorted(state.column_scores.items(), key=lambda x: x[1], reverse=True)
    columns_hits = [item for item in sorted_columns if item[1] > 0]
    if columns_hits:
        # Collect the top 2 columns, including ties
        top_columns = []
        scores_seen = set()
        for name, score in sorted_columns:
            if len(top_columns) < 2 or score in scores_seen:
                top_columns.append((name, score))
                scores_seen.add(score)
            else:
                break

        # Display the top 2 columns
        recommendations.append("Best Columns (Top 2):")
        for i, (name, score) in enumerate(top_columns[:2], 1):
            recommendations.append(f"{i}. {name}: {score}")

        # Check for ties among the top 2 positions
        if len(top_columns) > 1:
            first_score = top_columns[0][1]
            tied_first = [name for name, score in top_columns if score == first_score]
            if len(tied_first) > 1:
                recommendations.append(f"Note: Tie for 1st place among {', '.join(tied_first)} with score {first_score}")

            if len(top_columns) > 1:
                second_score = top_columns[1][1]
                tied_second = [name for name, score in top_columns if score == second_score]
                if len(tied_second) > 1:
                    recommendations.append(f"Note: Tie for 2nd place among {', '.join(tied_second)} with score {second_score}")
    else:
        recommendations.append("Best Columns: No hits yet.")

    # Top Pick 18 Numbers without Neighbours (same as top_pick_18_numbers_without_neighbours)
    recommendations.append("")  # Add a blank line for separation
    straight_up_df = pd.DataFrame(list(state.scores.items()), columns=["Number", "Score"])
    straight_up_df = straight_up_df[straight_up_df["Score"] > 0].sort_values(by="Score", ascending=False)

    if straight_up_df.empty or len(straight_up_df) < 18:
        recommendations.append("Top Pick 18 Numbers without Neighbours: Not enough numbers have hit yet (need at least 18).")
        return "\n".join(recommendations)

    top_18_df = straight_up_df.head(18)
    top_18_numbers = top_18_df["Number"].tolist()

    top_6 = top_18_numbers[:6]
    next_6 = top_18_numbers[6:12]
    last_6 = top_18_numbers[12:18]

    recommendations.append("Top Pick 18 Numbers without Neighbours:")
    recommendations.append("\nTop 6 Numbers (Yellow):")
    for i, num in enumerate(top_6, 1):
        score = top_18_df[top_18_df["Number"] == num]["Score"].iloc[0]
        recommendations.append(f"{i}. Number {num} (Score: {score})")

    recommendations.append("\nNext 6 Numbers (Blue):")
    for i, num in enumerate(next_6, 1):
        score = top_18_df[top_18_df["Number"] == num]["Score"].iloc[0]
        recommendations.append(f"{i}. Number {num} (Score: {score})")

    recommendations.append("\nLast 6 Numbers (Green):")
    for i, num in enumerate(last_6, 1):
        score = top_18_df[top_18_df["Number"] == num]["Score"].iloc[0]
        recommendations.append(f"{i}. Number {num} (Score: {score})")

    return "\n".join(recommendations)

def best_dozens_even_money_and_top_18():
    recommendations = []

    # Best Dozens (Top 2 with tie handling, same as best_dozens)
    sorted_dozens = sorted(state.dozen_scores.items(), key=lambda x: x[1], reverse=True)
    dozens_hits = [item for item in sorted_dozens if item[1] > 0]
    if dozens_hits:
        # Collect the top 2 dozens, including ties
        top_dozens = []
        scores_seen = set()
        for name, score in sorted_dozens:
            if len(top_dozens) < 2 or score in scores_seen:
                top_dozens.append((name, score))
                scores_seen.add(score)
            else:
                break

        # Display the top 2 dozens
        recommendations.append("Best Dozens (Top 2):")
        for i, (name, score) in enumerate(top_dozens[:2], 1):
            recommendations.append(f"{i}. {name}: {score}")

        # Check for ties among the top 2 positions
        if len(top_dozens) > 1:
            first_score = top_dozens[0][1]
            tied_first = [name for name, score in top_dozens if score == first_score]
            if len(tied_first) > 1:
                recommendations.append(f"Note: Tie for 1st place among {', '.join(tied_first)} with score {first_score}")

            if len(top_dozens) > 1:
                second_score = top_dozens[1][1]
                tied_second = [name for name, score in top_dozens if score == second_score]
                if len(tied_second) > 1:
                    recommendations.append(f"Note: Tie for 2nd place among {', '.join(tied_second)} with score {second_score}")
    else:
        recommendations.append("Best Dozens: No hits yet.")

    # Best Even Money Bets (Top 3 with tie handling, same as best_even_money_bets)
    recommendations.append("")  # Add a blank line for separation
    sorted_even_money = sorted(state.even_money_scores.items(), key=lambda x: x[1], reverse=True)
    even_money_hits = [item for item in sorted_even_money if item[1] > 0]
    
    if even_money_hits:
        # Collect the top 3 bets, including ties
        top_bets = []
        scores_seen = set()
        for name, score in sorted_even_money:
            if len(top_bets) < 3 or score in scores_seen:
                top_bets.append((name, score))
                scores_seen.add(score)
            else:
                break

        # Display the top 3 bets
        recommendations.append("Best Even Money Bets (Top 3):")
        for i, (name, score) in enumerate(top_bets[:3], 1):
            recommendations.append(f"{i}. {name}: {score}")

        # Check for ties among the top 3 positions
        if len(top_bets) > 1:
            first_score = top_bets[0][1]
            tied_first = [name for name, score in top_bets if score == first_score]
            if len(tied_first) > 1:
                recommendations.append(f"Note: Tie for 1st place among {', '.join(tied_first)} with score {first_score}")

            if len(top_bets) > 1:
                second_score = top_bets[1][1]
                tied_second = [name for name, score in top_bets if score == second_score]
                if len(tied_second) > 1:
                    recommendations.append(f"Note: Tie for 2nd place among {', '.join(tied_second)} with score {second_score}")

            if len(top_bets) > 2:
                third_score = top_bets[2][1]
                tied_third = [name for name, score in top_bets if score == third_score]
                if len(tied_third) > 1:
                    recommendations.append(f"Note: Tie for 3rd place among {', '.join(tied_third)} with score {third_score}")
    else:
        recommendations.append("Best Even Money Bets: No hits yet.")

    # Top Pick 18 Numbers without Neighbours (same as top_pick_18_numbers_without_neighbours)
    recommendations.append("")  # Add a blank line for separation
    straight_up_df = pd.DataFrame(list(state.scores.items()), columns=["Number", "Score"])
    straight_up_df = straight_up_df[straight_up_df["Score"] > 0].sort_values(by="Score", ascending=False)

    if straight_up_df.empty or len(straight_up_df) < 18:
        recommendations.append("Top Pick 18 Numbers without Neighbours: Not enough numbers have hit yet (need at least 18).")
        return "\n".join(recommendations)

    top_18_df = straight_up_df.head(18)
    top_18_numbers = top_18_df["Number"].tolist()

    top_6 = top_18_numbers[:6]
    next_6 = top_18_numbers[6:12]
    last_6 = top_18_numbers[12:18]

    recommendations.append("Top Pick 18 Numbers without Neighbours:")
    recommendations.append("\nTop 6 Numbers (Yellow):")
    for i, num in enumerate(top_6, 1):
        score = top_18_df[top_18_df["Number"] == num]["Score"].iloc[0]
        recommendations.append(f"{i}. Number {num} (Score: {score})")

    recommendations.append("\nNext 6 Numbers (Blue):")
    for i, num in enumerate(next_6, 1):
        score = top_18_df[top_18_df["Number"] == num]["Score"].iloc[0]
        recommendations.append(f"{i}. Number {num} (Score: {score})")

    recommendations.append("\nLast 6 Numbers (Green):")
    for i, num in enumerate(last_6, 1):
        score = top_18_df[top_18_df["Number"] == num]["Score"].iloc[0]
        recommendations.append(f"{i}. Number {num} (Score: {score})")

    return "\n".join(recommendations)

def best_columns_even_money_and_top_18():
    recommendations = []

    # Best Columns (Top 2 with tie handling, same as best_columns)
    sorted_columns = sorted(state.column_scores.items(), key=lambda x: x[1], reverse=True)
    columns_hits = [item for item in sorted_columns if item[1] > 0]
    if columns_hits:
        # Collect the top 2 columns, including ties
        top_columns = []
        scores_seen = set()
        for name, score in sorted_columns:
            if len(top_columns) < 2 or score in scores_seen:
                top_columns.append((name, score))
                scores_seen.add(score)
            else:
                break

        # Display the top 2 columns
        recommendations.append("Best Columns (Top 2):")
        for i, (name, score) in enumerate(top_columns[:2], 1):
            recommendations.append(f"{i}. {name}: {score}")

        # Check for ties among the top 2 positions
        if len(top_columns) > 1:
            first_score = top_columns[0][1]
            tied_first = [name for name, score in top_columns if score == first_score]
            if len(tied_first) > 1:
                recommendations.append(f"Note: Tie for 1st place among {', '.join(tied_first)} with score {first_score}")

            if len(top_columns) > 1:
                second_score = top_columns[1][1]
                tied_second = [name for name, score in top_columns if score == second_score]
                if len(tied_second) > 1:
                    recommendations.append(f"Note: Tie for 2nd place among {', '.join(tied_second)} with score {second_score}")
    else:
        recommendations.append("Best Columns: No hits yet.")

    # Best Even Money Bets (Top 3 with tie handling, same as best_even_money_bets)
    recommendations.append("")  # Add a blank line for separation
    sorted_even_money = sorted(state.even_money_scores.items(), key=lambda x: x[1], reverse=True)
    even_money_hits = [item for item in sorted_even_money if item[1] > 0]
    
    if even_money_hits:
        # Collect the top 3 bets, including ties
        top_bets = []
        scores_seen = set()
        for name, score in sorted_even_money:
            if len(top_bets) < 3 or score in scores_seen:
                top_bets.append((name, score))
                scores_seen.add(score)
            else:
                break

        # Display the top 3 bets
        recommendations.append("Best Even Money Bets (Top 3):")
        for i, (name, score) in enumerate(top_bets[:3], 1):
            recommendations.append(f"{i}. {name}: {score}")

        # Check for ties among the top 3 positions
        if len(top_bets) > 1:
            first_score = top_bets[0][1]
            tied_first = [name for name, score in top_bets if score == first_score]
            if len(tied_first) > 1:
                recommendations.append(f"Note: Tie for 1st place among {', '.join(tied_first)} with score {first_score}")

            if len(top_bets) > 1:
                second_score = top_bets[1][1]
                tied_second = [name for name, score in top_bets if score == second_score]
                if len(tied_second) > 1:
                    recommendations.append(f"Note: Tie for 2nd place among {', '.join(tied_second)} with score {second_score}")

            if len(top_bets) > 2:
                third_score = top_bets[2][1]
                tied_third = [name for name, score in top_bets if score == third_score]
                if len(tied_third) > 1:
                    recommendations.append(f"Note: Tie for 3rd place among {', '.join(tied_third)} with score {third_score}")
    else:
        recommendations.append("Best Even Money Bets: No hits yet.")

    # Top Pick 18 Numbers without Neighbours (same as top_pick_18_numbers_without_neighbours)
    recommendations.append("")  # Add a blank line for separation
    straight_up_df = pd.DataFrame(list(state.scores.items()), columns=["Number", "Score"])
    straight_up_df = straight_up_df[straight_up_df["Score"] > 0].sort_values(by="Score", ascending=False)

    if straight_up_df.empty or len(straight_up_df) < 18:
        recommendations.append("Top Pick 18 Numbers without Neighbours: Not enough numbers have hit yet (need at least 18).")
        return "\n".join(recommendations)

    top_18_df = straight_up_df.head(18)
    top_18_numbers = top_18_df["Number"].tolist()

    top_6 = top_18_numbers[:6]
    next_6 = top_18_numbers[6:12]
    last_6 = top_18_numbers[12:18]

    recommendations.append("Top Pick 18 Numbers without Neighbours:")
    recommendations.append("\nTop 6 Numbers (Yellow):")
    for i, num in enumerate(top_6, 1):
        score = top_18_df[top_18_df["Number"] == num]["Score"].iloc[0]
        recommendations.append(f"{i}. Number {num} (Score: {score})")

    recommendations.append("\nNext 6 Numbers (Blue):")
    for i, num in enumerate(next_6, 1):
        score = top_18_df[top_18_df["Number"] == num]["Score"].iloc[0]
        recommendations.append(f"{i}. Number {num} (Score: {score})")

    recommendations.append("\nLast 6 Numbers (Green):")
    for i, num in enumerate(last_6, 1):
        score = top_18_df[top_18_df["Number"] == num]["Score"].iloc[0]
        recommendations.append(f"{i}. Number {num} (Score: {score})")

    return "\n".join(recommendations)

def create_color_code_table():
    html = '''
    <div style="margin-top: 20px;">
        <h3 style="margin-bottom: 10px; font-family: Arial, sans-serif;">Color Code Key</h3>
        <table border="1" style="border-collapse: collapse; text-align: left; font-size: 14px; font-family: Arial, sans-serif; width: 100%; max-width: 600px; border-color: #333;">
            <thead>
                <tr style="background-color: #f2f2f2;">
                    <th style="padding: 8px; width: 20%;">Color</th>
                    <th style="padding: 8px;">Meaning</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td style="padding: 8px; background-color: rgba(255, 255, 0, 0.5); text-align: center;">Yellow (Top Tier)</td>
                    <td style="padding: 8px;">Indicates the hottest or top-ranked numbers/sections (e.g., top 3 or top 6 in most strategies). For Dozen Tracker, this highlights the most frequent Dozen when no strategy is selected. Can be changed via color pickers.</td>
                </tr>
                <tr>
                    <td style="padding: 8px; background-color: rgba(0, 255, 255, 0.5); text-align: center;">Cyan (Middle Tier)</td>
                    <td style="padding: 8px;">Represents the second tier of trending numbers/sections (e.g., ranks 4-6 or secondary picks). For Dozen Tracker, this highlights the second most frequent Dozen when no strategy is selected. Can be changed via color pickers.</td>
                </tr>
                <tr>
                    <td style="padding: 8px; background-color: rgba(0, 255, 0, 0.5); text-align: center;">Green (Lower Tier)</td>
                    <td style="padding: 8px;">Marks the third tier of strong numbers/sections (e.g., ranks 7-9 or lower priority). Can be changed via color pickers.</td>
                </tr>
                <tr>
                    <td style="padding: 8px; background-color: #D3D3D3; text-align: center;">Light Gray (Cold Top)</td>
                    <td style="padding: 8px;">Used in Cold Bet Strategy for the coldest top-tier sections (least hits). Fixed for this strategy.</td>
                </tr>
                <tr>
                    <td style="padding: 8px; background-color: #DDA0DD; text-align: center;">Plum (Cold Middle)</td>
                    <td style="padding: 8px;">Used in Cold Bet Strategy for middle-tier cold sections. Fixed for this strategy.</td>
                </tr>
                <tr>
                    <td style="padding: 8px; background-color: #E0FFFF; text-align: center;">Light Cyan (Cold Lower)</td>
                    <td style="padding: 8px;">Used in Cold Bet Strategy for lower-tier cold sections. Fixed for this strategy.</td>
                </tr>
                <tr>
                    <td style="padding: 8px; background-color: red; color: white; text-align: center;">Red</td>
                    <td style="padding: 8px;">Default color for red numbers on the roulette table.</td>
                </tr>
                <tr>
                    <td style="padding: 8px; background-color: black; color: white; text-align: center;">Black</td>
                    <td style="padding: 8px;">Default color for black numbers on the roulette table.</td>
                </tr>
                <tr>
                    <td style="padding: 8px; background-color: green; color: white; text-align: center;">Green</td>
                    <td style="padding: 8px;">Default color for zero (0) on the roulette table.</td>
                </tr>
                <tr>
                    <td style="padding: 8px; background-color: #FF6347; color: white; text-align: center;">Tomato Red</td>
                    <td style="padding: 8px;">Used in Dozen Tracker to represent the 1st Dozen.</td>
                </tr>
                <tr>
                    <td style="padding: 8px; background-color: #4682B4; color: white; text-align: center;">Steel Blue</td>
                    <td style="padding: 8px;">Used in Dozen Tracker to represent the 2nd Dozen.</td>
                </tr>
                <tr>
                    <td style="padding: 8px; background-color: #32CD32; color: white; text-align: center;">Lime Green</td>
                    <td style="padding: 8px;">Used in Dozen Tracker to represent the 3rd Dozen.</td>
                </tr>
                <tr>
                    <td style="padding: 8px; background-color: #808080; color: white; text-align: center;">Gray</td>
                    <td style="padding: 8px;">Used in Dozen Tracker to represent spins not in any Dozen (i.e., 0).</td>
                </tr>
            </tbody>
        </table>
    </div>
    '''
    return html
    
def update_spin_counter():
    """Return the current number of spins as formatted HTML with inline styling."""
    spin_count = len(state.last_spins)
    return f'<span style="font-size: 16px;">Total Spins: {spin_count}</span>'
    
def top_numbers_with_neighbours_tiered():
    recommendations = []
    straight_up_df = pd.DataFrame(list(state.scores.items()), columns=["Number", "Score"])
    straight_up_df = straight_up_df[straight_up_df["Score"] > 0].sort_values(by="Score", ascending=False)

    if straight_up_df.empty:
        return "<p>Top Numbers with Neighbours (Tiered): No numbers have hit yet.</p>"

    # Start with the HTML table for Strongest Numbers
    table_html = '<table border="1" style="border-collapse: collapse; text-align: center; font-family: Arial, sans-serif;">'
    table_html += "<tr><th>Hit</th><th>Left N.</th><th>Right N.</th></tr>"  # Table header
    for _, row in straight_up_df.iterrows():
        num = str(row["Number"])
        left, right = current_neighbors.get(row["Number"], ("", ""))
        left = str(left) if left is not None else ""
        right = str(right) if right is not None else ""
        table_html += f"<tr><td>{num}</td><td>{left}</td><td>{right}</td></tr>"
    table_html += "</table>"

    # Wrap the table in a div with a heading
    recommendations.append("<h3>Strongest Numbers:</h3>")
    recommendations.append(table_html)

    num_to_take = min(8, len(straight_up_df))
    top_numbers = straight_up_df["Number"].head(num_to_take).tolist()

    all_numbers = set()
    number_scores = {}
    for num in top_numbers:
        neighbors = current_neighbors.get(num, (None, None))
        left, right = neighbors
        all_numbers.add(num)
        number_scores[num] = state.scores[num]
        if left is not None:
            all_numbers.add(left)
        if right is not None:
            all_numbers.add(right)

    number_groups = []
    for num in top_numbers:
        left, right = current_neighbors.get(num, (None, None))
        group = [num]
        if left is not None:
            group.append(left)
        if right is not None:
            group.append(right)
        number_groups.append((state.scores[num], group))

    number_groups.sort(key=lambda x: x[0], reverse=True)
    ordered_numbers = []
    for _, group in number_groups:
        ordered_numbers.extend(group)

    ordered_numbers = ordered_numbers[:24]
    top_8 = ordered_numbers[:8]
    next_8 = ordered_numbers[8:16]
    last_8 = ordered_numbers[16:24]

    recommendations.append("<h3>Top Numbers with Neighbours (Tiered):</h3>")
    recommendations.append("<p><strong>Top Tier (Yellow):</strong></p>")
    for i, num in enumerate(top_8, 1):
        score = number_scores.get(num, "Neighbor")
        recommendations.append(f"<p>{i}. Number {num} (Score: {score})</p>")

    recommendations.append("<p><strong>Second Tier (Blue):</strong></p>")
    for i, num in enumerate(next_8, 1):
        score = number_scores.get(num, "Neighbor")
        recommendations.append(f"<p>{i}. Number {num} (Score: {score})</p>")

    recommendations.append("<p><strong>Third Tier (Green):</strong></p>")
    for i, num in enumerate(last_8, 1):
        score = number_scores.get(num, "Neighbor")
        recommendations.append(f"<p>{i}. Number {num} (Score: {score})</p>")

    return "\n".join(recommendations)

def neighbours_of_strong_number(neighbours_count, strong_numbers_count):
    """Recommend numbers and their neighbors based on hit frequency."""
    recommendations = []
    
    # Validate inputs
    try:
        neighbours_count = int(neighbours_count)
        strong_numbers_count = int(strong_numbers_count)
        if neighbours_count < 0 or strong_numbers_count < 0:
            raise ValueError("Neighbours count and strong numbers count must be non-negative.")
        if strong_numbers_count == 0:
            raise ValueError("Strong numbers count must be at least 1.")
    except (ValueError, TypeError) as e:
        return f"Error: Invalid input - {str(e)}. Please use positive integers for neighbours and strong numbers."

    # Check if current_neighbors is valid
    if not isinstance(current_neighbors, dict):
        return "Error: Neighbor data is not properly configured. Contact support."
    for key, value in current_neighbors.items():
        if not isinstance(key, int) or not isinstance(value, tuple) or len(value) != 2:
            return "Error: Neighbor data is malformed. Contact support."

    try:
        print(f"neighbours_of_strong_number: Starting with neighbours_count = {neighbours_count}, strong_numbers_count = {strong_numbers_count}")
        sorted_numbers = sorted(state.scores.items(), key=lambda x: (-x[1], x[0]))
        numbers_hits = [item for item in sorted_numbers if item[1] > 0]
        
        if not numbers_hits:
            recommendations.append("Neighbours of Strong Number: No numbers have hit yet.")
            return "\n".join(recommendations)

        # Limit strong_numbers_count to available hits
        strong_numbers_count = min(strong_numbers_count, len(numbers_hits))
        top_numbers = [item[0] for item in numbers_hits[:strong_numbers_count]]
        top_scores = {item[0]: item[1] for item in numbers_hits[:strong_numbers_count]}
        selected_numbers = set(top_numbers)
        neighbors_set = set()

        # Calculate neighbors for each strong number
        for strong_number in top_numbers:
            if strong_number not in current_neighbors:
                recommendations.append(f"Warning: No neighbor data for number {strong_number}. Skipping its neighbors.")
                continue
            current_number = strong_number
            # Left neighbors
            for i in range(neighbours_count):
                left, _ = current_neighbors.get(current_number, (None, None))
                if left is not None:
                    neighbors_set.add(left)
                    current_number = left
                else:
                    break
            # Right neighbors
            current_number = strong_number
            for i in range(neighbours_count):
                _, right = current_neighbors.get(current_number, (None, None))
                if right is not None:
                    neighbors_set.add(right)
                    current_number = right
                else:
                    break

        # Remove overlap (strong numbers take precedence)
        neighbors_set = neighbors_set - selected_numbers
        print(f"neighbours_of_strong_number: Strong numbers = {sorted(list(selected_numbers))}")
        print(f"neighbours_of_strong_number: Neighbors = {sorted(list(neighbors_set))}")

        # Format recommendations
        recommendations.append(f"Top {strong_numbers_count} Strongest Numbers and Their Neighbours:")
        recommendations.append("\nStrongest Numbers (Yellow):")
        for i, num in enumerate(sorted(top_numbers), 1):
            score = top_scores[num]
            recommendations.append(f"{i}. Number {num} (Score: {score})")
        
        if neighbors_set:
            recommendations.append(f"\nNeighbours ({neighbours_count} Left + {neighbours_count} Right, Cyan):")
            for i, num in enumerate(sorted(list(neighbors_set)), 1):
                recommendations.append(f"{i}. Number {num}")
        else:
            recommendations.append(f"\nNeighbours ({neighbours_count} Left + {neighbours_count} Right, Cyan): None")

        return "\n".join(recommendations)

    except Exception as e:
        print(f"neighbours_of_strong_number: Unexpected error: {str(e)}")
        return f"Error in Neighbours of Strong Number: Unexpected issue - {str(e)}. Please try again or contact support."

def dozen_tracker(num_spins_to_check, consecutive_hits_threshold, alert_enabled, sequence_length, follow_up_spins, sequence_alert_enabled):
    """Track and display the history of Dozen hits for the last N spins, with optional alerts for consecutive hits and sequence matching."""
    recommendations = []
    sequence_recommendations = []
    
    # Validate inputs
    try:
        num_spins_to_check = int(num_spins_to_check)
        consecutive_hits_threshold = int(consecutive_hits_threshold)
        sequence_length = int(sequence_length)
        follow_up_spins = int(follow_up_spins)
        if num_spins_to_check < 1:
            return "Error: Number of spins to check must be at least 1.", "<p>Error: Number of spins to check must be at least 1.</p>", "<p>Error: Number of spins to check must be at least 1.</p>"
        if consecutive_hits_threshold < 1:
            return "Error: Consecutive hits threshold must be at least 1.", "<p>Error: Consecutive hits threshold must be at least 1.</p>", "<p>Error: Consecutive hits threshold must be at least 1.</p>"
        if sequence_length < 1:
            return "Error: Sequence length must be at least 1.", "<p>Error: Sequence length must be at least 1.</p>", "<p>Error: Sequence length must be at least 1.</p>"
        if follow_up_spins < 1:
            return "Error: Follow-up spins must be at least 1.", "<p>Error: Follow-up spins must be at least 1.</p>", "<p>Error: Follow-up spins must be at least 1.</p>"
    except (ValueError, TypeError):
        return "Error: Invalid inputs. Please use positive integers.", "<p>Error: Invalid inputs. Please use positive integers.</p>", "<p>Error: Invalid inputs. Please use positive integers.</p>"

    # Add print statement here to debug the number of spins being tracked
    recent_spins = state.last_spins[-num_spins_to_check:] if len(state.last_spins) >= num_spins_to_check else state.last_spins
    print(f"dozen_tracker: Tracking {num_spins_to_check} spins, recent_spins length = {len(recent_spins)}")
    
    if not recent_spins:
        return "Dozen Tracker: No spins recorded yet.", "<p>Dozen Tracker: No spins recorded yet.</p>", "<p>Dozen Tracker: No spins recorded yet.</p>"
    
    # Get the last N spins
    recent_spins = state.last_spins[-num_spins_to_check:] if len(state.last_spins) >= num_spins_to_check else state.last_spins
    if not recent_spins:
        return "Dozen Tracker: No spins recorded yet.", "<p>Dozen Tracker: No spins recorded yet.</p>", "<p>Dozen Tracker: No spins recorded yet.</p>"

    # Map each spin to its Dozen
    dozen_pattern = []
    dozen_counts = {"1st Dozen": 0, "2nd Dozen": 0, "3rd Dozen": 0, "Not in Dozen": 0}
    for spin in recent_spins:
        spin_value = int(spin)
        if spin_value == 0:
            dozen_pattern.append("Not in Dozen")
            dozen_counts["Not in Dozen"] += 1
        else:
            found = False
            for name, numbers in DOZENS.items():
                if spin_value in numbers:
                    dozen_pattern.append(name)
                    dozen_counts[name] += 1
                    found = True
                    break
            if not found:
                dozen_pattern.append("Not in Dozen")
                dozen_counts["Not in Dozen"] += 1

    # Detect consecutive Dozen hits (only if alert is enabled)
    current_streak = 1
    current_dozen = None
    max_streak = 1
    max_streak_dozen = None
    if alert_enabled:
        for i in range(len(dozen_pattern)):
            dozen = dozen_pattern[i]
            if dozen == "Not in Dozen":  # 0 breaks the streak
                current_streak = 1
                current_dozen = None
                continue
            if current_dozen is None or dozen != current_dozen:
                current_dozen = dozen
                current_streak = 1
            else:
                current_streak += 1
                if current_streak >= consecutive_hits_threshold:
                    gr.Warning(f"Alert: {current_dozen} has hit {current_streak} times consecutively!")
                if current_streak > max_streak:
                    max_streak = current_streak
                    max_streak_dozen = current_dozen

    # Detect sequence matches (only if sequence alert is enabled)
    sequence_matches = []
    sequence_follow_ups = []
    if sequence_alert_enabled and len(dozen_pattern) >= sequence_length:
        # Collect all sequences of length X
        sequences = []
        for i in range(len(dozen_pattern) - sequence_length + 1):
            seq = tuple(dozen_pattern[i:i + sequence_length])
            sequences.append((i, seq))

        # Find matching sequences
        for i in range(len(sequences)):
            for j in range(i + 1, len(sequences)):
                if sequences[i][1] == sequences[j][1]:
                    start_idx = sequences[j][0]
                    sequence_matches.append((start_idx, sequences[j][1]))
                    # Get the next Y spins after the first occurrence
                    first_start_idx = sequences[i][0]
                    follow_up_start = first_start_idx + sequence_length
                    follow_up_end = follow_up_start + follow_up_spins
                    if follow_up_end <= len(dozen_pattern):
                        follow_up = dozen_pattern[follow_up_start:follow_up_end]
                        sequence_follow_ups.append((start_idx, sequences[j][1], follow_up))

        # If a match is found, provide betting recommendations
        if sequence_matches:
            latest_match = max(sequence_matches, key=lambda x: x[0])  # Latest match by start index
            latest_start_idx, matched_sequence = latest_match
            # Find the follow-up spins for the first occurrence of this sequence
            first_occurrence = min((seq for seq in sequences if seq[1] == matched_sequence), key=lambda x: x[0])[0]
            follow_up_start = first_occurrence + sequence_length
            follow_up_end = follow_up_start + follow_up_spins
            if follow_up_end <= len(dozen_pattern):
                follow_up = dozen_pattern[follow_up_start:follow_up_end]
                gr.Warning(f"Alert: Sequence {', '.join(matched_sequence)} has repeated at spins {latest_start_idx + 1} to {latest_start_idx + sequence_length}!")
                sequence_recommendations.append(f"Alert: Sequence {', '.join(matched_sequence)} has repeated at spins {latest_start_idx + 1} to {latest_start_idx + sequence_length}!")
                sequence_recommendations.append(f"Previous follow-up spins (next {follow_up_spins}): {', '.join(follow_up)}")
                sequence_recommendations.append("Betting Recommendations (Bet Against Historical Follow-Ups):")
                all_dozens = ["1st Dozen", "2nd Dozen", "3rd Dozen"]
                for idx, dozen in enumerate(follow_up):
                    if dozen == "Not in Dozen":
                        sequence_recommendations.append(f"Spin {idx + 1}: 0 (Not in Dozen) - No bet recommendation.")
                    else:
                        dozens_to_bet = [d for d in all_dozens if d != dozen]
                        sequence_recommendations.append(f"Spin {idx + 1}: Bet against {dozen} - Bet on {', '.join(dozens_to_bet)}")

    # Text summary for Dozen Tracker
    recommendations.append(f"Dozen Tracker (Last {len(recent_spins)} Spins):")
    recommendations.append("Dozen History: " + ", ".join(dozen_pattern))
    if alert_enabled and max_streak >= consecutive_hits_threshold:
        recommendations.append(f"\nAlert: {max_streak_dozen} hit {max_streak} times consecutively!")
    recommendations.append("\nSummary of Dozen Hits:")
    for name, count in dozen_counts.items():
        recommendations.append(f"{name}: {count} hits")

    # HTML representation for Dozen Tracker
    html_output = f'<h4>Dozen Tracker (Last {len(recent_spins)} Spins):</h4>'
    html_output += '<div style="display: flex; flex-wrap: wrap; gap: 5px; margin-bottom: 10px;">'
    for dozen in dozen_pattern:
        color = {
            "1st Dozen": "#FF6347",  # Tomato red
            "2nd Dozen": "#4682B4",  # Steel blue
            "3rd Dozen": "#32CD32",  # Lime green
            "Not in Dozen": "#808080"  # Gray for 0
        }.get(dozen, "#808080")
        html_output += f'<span style="background-color: {color}; color: white; padding: 2px 5px; border-radius: 3px; display: inline-block;">{dozen}</span>'
    html_output += '</div>'
    if alert_enabled and max_streak >= consecutive_hits_threshold:
        html_output += f'<p style="color: red; font-weight: bold;">Alert: {max_streak_dozen} hit {max_streak} times consecutively!</p>'
    html_output += '<h4>Summary of Dozen Hits:</h4>'
    html_output += '<ul style="list-style-type: none; padding-left: 0;">'
    for name, count in dozen_counts.items():
        html_output += f'<li>{name}: {count} hits</li>'
    html_output += '</ul>'

    # HTML representation for Sequence Matching
    sequence_html_output = "<h4>Sequence Matching Results:</h4>"
    if not sequence_alert_enabled:
        sequence_html_output += "<p>Sequence matching is disabled. Enable it to see results.</p>"
    elif len(dozen_pattern) < sequence_length:
        sequence_html_output += f"<p>Not enough spins to match a sequence of length {sequence_length}.</p>"
    elif not sequence_matches:
        sequence_html_output += "<p>No sequence matches found yet.</p>"
    else:
        sequence_html_output += "<ul style='list-style-type: none; padding-left: 0;'>"
        for start_idx, seq in sequence_matches:
            sequence_html_output += f"<li>Match found at spins {start_idx + 1} to {start_idx + sequence_length}: {', '.join(seq)}</li>"
        sequence_html_output += "</ul>"
        if sequence_recommendations:
            sequence_html_output += "<h4>Latest Match Details:</h4>"
            sequence_html_output += "<ul style='list-style-type: none; padding-left: 0;'>"
            for rec in sequence_recommendations:
                if "Alert:" in rec:
                    sequence_html_output += f"<li style='color: red; font-weight: bold;'>{rec}</li>"
                else:
                    sequence_html_output += f"<li>{rec}</li>"
            sequence_html_output += "</ul>"

    return "\n".join(recommendations), html_output, sequence_html_output

STRATEGIES = {
    "Hot Bet Strategy": {"function": hot_bet_strategy, "categories": ["even_money", "dozens", "columns", "streets", "corners", "six_lines", "splits", "sides", "numbers"]},
    "Cold Bet Strategy": {"function": cold_bet_strategy, "categories": ["even_money", "dozens", "columns", "streets", "corners", "six_lines", "splits", "sides", "numbers"]},
    "Best Even Money Bets": {"function": best_even_money_bets, "categories": ["even_money"]},
    "Best Even Money Bets + Top Pick 18 Numbers": {"function": best_even_money_and_top_18, "categories": ["even_money", "numbers"]},
    "Best Dozens": {"function": best_dozens, "categories": ["dozens"]},
    "Best Dozens + Top Pick 18 Numbers": {"function": best_dozens_and_top_18, "categories": ["dozens", "numbers"]},
    "Best Columns": {"function": best_columns, "categories": ["columns"]},
    "Best Columns + Top Pick 18 Numbers": {"function": best_columns_and_top_18, "categories": ["columns", "numbers"]},
    "Best Dozens + Best Even Money Bets + Top Pick 18 Numbers": {"function": best_dozens_even_money_and_top_18, "categories": ["dozens", "even_money", "numbers", "trends"]},
    "Best Columns + Best Even Money Bets + Top Pick 18 Numbers": {"function": best_columns_even_money_and_top_18, "categories": ["columns", "even_money", "numbers", "trends"]},
    "Fibonacci Strategy": {"function": fibonacci_strategy, "categories": ["dozens", "columns"]},
    "Best Streets": {"function": best_streets, "categories": ["streets"]},
    "Best Double Streets": {"function": best_double_streets, "categories": ["six_lines"]},
    "Best Corners": {"function": best_corners, "categories": ["corners"]},
    "Best Splits": {"function": best_splits, "categories": ["splits"]},
    "Best Dozens + Best Streets": {"function": best_dozens_and_streets, "categories": ["dozens", "streets"]},
    "Best Columns + Best Streets": {"function": best_columns_and_streets, "categories": ["columns", "streets"]},
    "Non-Overlapping Double Street Strategy": {"function": non_overlapping_double_street_strategy, "categories": ["six_lines"]},
    "Non-Overlapping Corner Strategy": {"function": non_overlapping_corner_strategy, "categories": ["corners"]},
    "Romanowksy Missing Dozen": {"function": romanowksy_missing_dozen_strategy, "categories": ["dozens", "numbers"]},
    "Fibonacci To Fortune": {"function": fibonacci_to_fortune_strategy, "categories": ["even_money", "dozens", "columns", "six_lines"]},
    "3-8-6 Rising Martingale": {"function": three_eight_six_rising_martingale, "categories": ["streets"]},
    "1 Dozen +1 Column Strategy": {"function": one_dozen_one_column_strategy, "categories": ["dozens", "columns"]},
    "Top Pick 18 Numbers without Neighbours": {"function": top_pick_18_numbers_without_neighbours, "categories": ["numbers"]},
    "Top Numbers with Neighbours (Tiered)": {"function": top_numbers_with_neighbours_tiered, "categories": ["numbers"]},
    "Neighbours of Strong Number": {"function": neighbours_of_strong_number, "categories": ["neighbours"]}
}

def show_strategy_recommendations(strategy_name, neighbours_count, strong_numbers_count, *args):
    try:
        print(f"show_strategy_recommendations: scores = {dict(state.scores)}")
        print(f"show_strategy_recommendations: even_money_scores = {dict(state.even_money_scores)}")
        print(f"show_strategy_recommendations: any_scores = {any(state.scores.values())}, any_even_money = {any(state.even_money_scores.values())}")
        print(f"show_strategy_recommendations: strategy_name = {strategy_name}, neighbours_count = {neighbours_count}, strong_numbers_count = {strong_numbers_count}, args = {args}")

        if strategy_name == "None":
            return "<p>No strategy selected. Please choose a strategy to see recommendations.</p>"
        
        # If no spins yet, provide a default for "Best Even Money Bets"
        if not any(state.scores.values()) and not any(state.even_money_scores.values()):
            if strategy_name == "Best Even Money Bets":
                return "<p>No spins yet. Default Even Money Bets to consider:<br>1. Red<br>2. Black<br>3. Even</p>"
            return "<p>Please analyze some spins first to generate scores.</p>"

        strategy_info = STRATEGIES[strategy_name]
        strategy_func = strategy_info["function"]

        if strategy_name == "Neighbours of Strong Number":
            try:
                neighbours_count = int(neighbours_count)
                strong_numbers_count = int(strong_numbers_count)
                print(f"show_strategy_recommendations: Using neighbours_count = {neighbours_count}, strong_numbers_count = {strong_numbers_count}")
            except (ValueError, TypeError) as e:
                print(f"show_strategy_recommendations: Error converting inputs: {str(e)}, defaulting to 2 and 1.")
                neighbours_count = 2
                strong_numbers_count = 1
            recommendations = strategy_func(neighbours_count, strong_numbers_count)
        else:
            recommendations = strategy_func()

        print(f"show_strategy_recommendations: Strategy {strategy_name} output = {recommendations}")

        # If the output is already HTML, return it as is
        if strategy_name == "Top Numbers with Neighbours (Tiered)":
            return recommendations
        # Otherwise, convert plain text to HTML
        else:
            lines = recommendations.split("\n")
            html_lines = [f"<p>{line}</p>" for line in lines if line.strip()]
            return "".join(html_lines)
    except Exception as e:
        print(f"show_strategy_recommendations: Error: {str(e)}")
        return f"<p>Error generating strategy recommendations: {str(e)}</p>"

def clear_outputs():
    return "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""

def toggle_checkboxes(strategy_name):
    return (gr.update(visible=strategy_name == "Kitchen Martingale"),
            gr.update(visible=strategy_name == "S.T.Y.W: Victory Vortex"))
def reset_colors():
    """Reset color pickers to default values and update the dynamic table."""
    default_top = "rgba(255, 255, 0, 0.5)"  # Yellow
    default_middle = "rgba(0, 255, 255, 0.5)"  # Cyan
    default_lower = "rgba(0, 255, 0, 0.5)"  # Green
    return default_top, default_middle, default_lower
def clear_last_spins_display():
    """Clear the Last Spins HTML display without affecting spins data."""
    return "<h4>Last Spins</h4><p>Display cleared. Add spins to see them here.</p>", update_spin_counter()

# Build the Gradio interface
with gr.Blocks() as demo:
    # Define state and components used across sections at the top
    spins_display = gr.State(value="")
    spins_textbox = gr.Textbox(
        label="Selected Spins (Edit manually with commas, e.g., 5, 12, 0)",
        value="",
        interactive=True,
        elem_id="selected-spins"
    )
    last_spin_display = gr.HTML(
        label="Last Spins",
        value="",
        elem_classes=["last-spins-container"]
    )
    last_spin_count = gr.Slider(
        label="Show Last Spins",
        minimum=1,
        maximum=36,
        step=1,
        value=36,
        interactive=True,
        elem_classes="long-slider"
    )
    spin_counter = gr.HTML(
        value='<span style="font-size: 16px;">Total Spins: 0</span>',
        label="Total Spins",
        elem_classes=["spin-counter"]
    )
    # Define wheel_balance_html early to avoid NameError
    wheel_balance_html = gr.HTML(
        label="Wheel Section Balance",
        value="<h4>Wheel Section Balance</h4><p>No spins yet to compare left and right sides.</p>",
        elem_classes="compact-visual",
        visible=False  # Hide until placed in UI
    )

    # Define strategy categories and choices
    strategy_categories = {
        "Trends": ["Cold Bet Strategy", "Hot Bet Strategy", "Best Dozens + Best Even Money Bets + Top Pick 18 Numbers", "Best Columns + Best Even Money Bets + Top Pick 18 Numbers"],
        "Even Money Strategies": ["Best Even Money Bets", "Best Even Money Bets + Top Pick 18 Numbers", "Fibonacci To Fortune"],
        "Dozen Strategies": ["1 Dozen +1 Column Strategy", "Best Dozens", "Best Dozens + Top Pick 18 Numbers", "Best Dozens + Best Even Money Bets + Top Pick 18 Numbers", "Best Dozens + Best Streets", "Fibonacci Strategy", "Romanowksy Missing Dozen"],
        "Column Strategies": ["1 Dozen +1 Column Strategy", "Best Columns", "Best Columns + Top Pick 18 Numbers", "Best Columns + Best Even Money Bets + Top Pick 18 Numbers", "Best Columns + Best Streets"],
        "Street Strategies": ["3-8-6 Rising Martingale", "Best Streets", "Best Columns + Best Streets", "Best Dozens + Best Streets"],
        "Double Street Strategies": ["Best Double Streets", "Non-Overlapping Double Street Strategy"],
        "Corner Strategies": ["Best Corners", "Non-Overlapping Corner Strategy"],
        "Split Strategies": ["Best Splits"],
        "Number Strategies": ["Top Numbers with Neighbours (Tiered)", "Top Pick 18 Numbers without Neighbours"],
        "Neighbours Strategies": ["Neighbours of Strong Number"]
    }
    category_choices = ["None"] + sorted(strategy_categories.keys())

    # 1. Row 1: Header
    with gr.Row(elem_id="header-row"):
        with gr.Column(scale=1):
            gr.Markdown(
                "# Roulette Spin Analyzer with Strategies (European Table)",
                elem_classes="header-title"
            )
            gr.HTML(
                '''
                <button id="start-tour-btn" onclick="startTour()" style="padding: 8px 15px; background-color: #ff9800; color: white; border: none; border-radius: 5px; cursor: pointer; font-weight: bold;">🚀 Take the Tour!</button>
                '''
            )


    # 2. Row 2: European Roulette Table
    with gr.Group():
        gr.Markdown("### European Roulette Table")
        table_layout = [
            ["", "3", "6", "9", "12", "15", "18", "21", "24", "27", "30", "33", "36"],
            ["0", "2", "5", "8", "11", "14", "17", "20", "23", "26", "29", "32", "35"],
            ["", "1", "4", "7", "10", "13", "16", "19", "22", "25", "28", "31", "34"]
        ]
        with gr.Column(elem_classes="roulette-table"):
            for row in table_layout:
                with gr.Row(elem_classes="table-row"):
                    for num in row:
                        if num == "":
                            gr.Button(value=" ", interactive=False, min_width=40, elem_classes="empty-button")
                        else:
                            color = colors.get(str(num), "black")
                            is_selected = int(num) in state.selected_numbers
                            btn_classes = [f"roulette-button", color]
                            if is_selected:
                                btn_classes.append("selected")
                            btn = gr.Button(
                                value=num,
                                min_width=40,
                                elem_classes=btn_classes
                            )
                            btn.click(
                                fn=add_spin,
                                inputs=[gr.State(value=num), spins_display, last_spin_count],
                                outputs=[spins_display, spins_textbox, last_spin_display, spin_counter, wheel_balance_html]
                            )

    # 3. Row 3: Last Spins Display and Show Last Spins Slider
    with gr.Row():
        with gr.Column():
            last_spin_display
            last_spin_count

    # 4. Row 4: Spin Controls
    with gr.Row():
        with gr.Column(scale=2):
            clear_last_spins_button = gr.Button("Clear Last Spins Display", elem_classes=["action-button"])
        with gr.Column(scale=1):
            undo_button = gr.Button("Undo Spins", elem_classes=["action-button"], elem_id="undo-spins-btn")
        with gr.Column(scale=1):
            generate_spins_button = gr.Button("Generate Random Spins", elem_classes=["action-button"])
    
    # 5. Row 5: Selected Spins Textbox and Spin Counter
    with gr.Row(elem_id="selected-spins-row"):
        with gr.Column(scale=4, min_width=600):
            spins_textbox
        with gr.Column(scale=1, min_width=200):
            spin_counter  # Restore side-by-side layout with styling
    
    # 6. Row 6: Analyze Spins, Clear Spins, and Clear All Buttons
    with gr.Row():
        with gr.Column(scale=2):
            analyze_button = gr.Button("Analyze Spins", elem_classes=["action-button", "green-btn"], interactive=True)
        with gr.Column(scale=1):
            clear_spins_button = gr.Button("Clear Spins", elem_classes=["clear-spins-btn", "small-btn"])
        with gr.Column(scale=1):
            clear_all_button = gr.Button("Clear All", elem_classes=["clear-spins-btn", "small-btn"])

    # 7. Row 7: Dynamic Roulette Table, Strategy Recommendations, and Strategy Selection
    with gr.Row():  # Dynamic Table Row
        with gr.Column(scale=3):
            gr.Markdown("### Dynamic Roulette Table", elem_id="dynamic-table-heading")
            dynamic_table_output = gr.HTML(
                label="Dynamic Table",
                value=create_dynamic_table(strategy_name="Best Even Money Bets")
            )
        with gr.Column(scale=1):
            gr.Markdown("### Strategy Recommendations")
            strategy_output = gr.HTML(
                label="Strategy Recommendations",
                value=show_strategy_recommendations("Best Even Money Bets", 2, 1)
            )
            with gr.Accordion("Casino Data Insights", open=False, elem_id="casino-data-insights"):
                spins_count_dropdown = gr.Dropdown(
                    label="Past Spins Count",
                    choices=["30", "50", "100", "200", "300", "500"],
                    value="100",
                    interactive=True
                )
                with gr.Row():
                    even_percent = gr.Dropdown(
                        label="Even %",
                        choices=[f"{i:02d}" for i in range(100)],
                        value="00",
                        interactive=True
                    )
                    odd_percent = gr.Dropdown(
                        label="Odd %",
                        choices=[f"{i:02d}" for i in range(100)],
                        value="00",
                        interactive=True
                    )
                with gr.Row():
                    red_percent = gr.Dropdown(
                        label="Red %",
                        choices=[f"{i:02d}" for i in range(100)],
                        value="00",
                        interactive=True
                    )
                    black_percent = gr.Dropdown(
                        label="Black %",
                        choices=[f"{i:02d}" for i in range(100)],
                        value="00",
                        interactive=True
                    )
                with gr.Row():
                    low_percent = gr.Dropdown(
                        label="Low %",
                        choices=[f"{i:02d}" for i in range(100)],
                        value="00",
                        interactive=True
                    )
                    high_percent = gr.Dropdown(
                        label="High %",
                        choices=[f"{i:02d}" for i in range(100)],
                        value="00",
                        interactive=True
                    )
                with gr.Row():
                    dozen1_percent = gr.Dropdown(
                        label="1st Dozen %",
                        choices=[f"{i:02d}" for i in range(100)],
                        value="00",
                        interactive=True
                    )
                    dozen2_percent = gr.Dropdown(
                        label="2nd Dozen %",
                        choices=[f"{i:02d}" for i in range(100)],
                        value="00",
                        interactive=True
                    )
                    dozen3_percent = gr.Dropdown(
                        label="3rd Dozen %",
                        choices=[f"{i:02d}" for i in range(100)],
                        value="00",
                        interactive=True
                    )
                with gr.Row():
                    col1_percent = gr.Dropdown(
                        label="1st Column %",
                        choices=[f"{i:02d}" for i in range(100)],
                        value="00",
                        interactive=True
                    )
                    col2_percent = gr.Dropdown(
                        label="2nd Column %",
                        choices=[f"{i:02d}" for i in range(100)],
                        value="00",
                        interactive=True
                    )
                    col3_percent = gr.Dropdown(
                        label="3rd Column %",
                        choices=[f"{i:02d}" for i in range(100)],
                        value="00",
                        interactive=True
                    )
                use_winners_checkbox = gr.Checkbox(
                    label="Highlight Casino Winners",
                    value=False,
                    interactive=True
                )
                reset_casino_data_button = gr.Button(
                    "Reset Casino Data",
                    elem_classes=["action-button"]
                )
                casino_data_output = gr.HTML(
                    label="Casino Data Insights",
                    value="<p>No casino data entered yet.</p>"
                )

    # New Row: Wheel Section Balance (moved from previous position)
    with gr.Row():
        with gr.Column(scale=3):
            with gr.Accordion("Wheel Section Balance", open=True, elem_id="wheel-balance"):
                wheel_balance_html
        with gr.Column(scale=2):
            pass  # Empty column to maintain layout balance

# Line 3 (end of updated section)
    # 7.1. Row 7.1: Dozen Tracker
    with gr.Row():  # Dozen Tracker Row
        with gr.Column(scale=3):
            with gr.Accordion("Dozen Tracker", open=False, elem_id="dozen-tracker"):
                dozen_tracker_spins_dropdown = gr.Dropdown(
                    label="Number of Spins to Track",
                    choices=["3", "4", "5", "6", "10", "15", "20", "25", "30", "40", "50", "75", "100", "150", "200"],
                    value="5",
                    interactive=True
                )
                dozen_tracker_consecutive_hits_dropdown = gr.Dropdown(
                    label="Alert on Consecutive Dozen Hits",
                    choices=["3", "4", "5"],
                    value="3",
                    interactive=True
                )
                dozen_tracker_alert_checkbox = gr.Checkbox(
                    label="Enable Consecutive Dozen Hits Alert",
                    value=False,
                    interactive=True
                )
                dozen_tracker_sequence_length_dropdown = gr.Dropdown(
                    label="Sequence Length to Match (X)",
                    choices=["3", "4", "5"],
                    value="4",
                    interactive=True
                )
                dozen_tracker_follow_up_spins_dropdown = gr.Dropdown(
                    label="Follow-Up Spins to Track (Y)",
                    choices=["3", "4", "5", "6", "7", "8", "9", "10"],
                    value="5",
                    interactive=True
                )
                dozen_tracker_sequence_alert_checkbox = gr.Checkbox(
                    label="Enable Sequence Matching Alert",
                    value=False,
                    interactive=True
                )
                dozen_tracker_output = gr.HTML(
                    label="Dozen Tracker",
                    value="<p>Select the number of spins to track and analyze spins to see the Dozen history.</p>"
                )
                dozen_tracker_sequence_output = gr.HTML(
                    label="Sequence Matching Results",
                    value="<p>Enable sequence matching to see results here.</p>"
                )
        with gr.Column(scale=2):
            pass  # Empty column to maintain layout balance

    # 8. Row 8: Betting Progression Tracker
    with gr.Row():
        with gr.Accordion("Betting Progression Tracker", open=False, elem_classes=["betting-progression"]):
            with gr.Row():
                bankroll_input = gr.Number(label="Bankroll", value=1000)
                base_unit_input = gr.Number(label="Base Unit", value=10)
                stop_loss_input = gr.Number(label="Stop Loss", value=-500)
                stop_win_input = gr.Number(label="Stop Win", value=200)
            with gr.Row():
                bet_type_dropdown = gr.Dropdown(
                    label="Bet Type",
                    choices=["Even Money", "Dozens", "Columns", "Straight Bets"],
                    value="Even Money"
                )
                progression_dropdown = gr.Dropdown(
                    label="Progression",
                    choices=["Martingale", "Fibonacci", "Triple Martingale", "Oscar’s Grind", "Labouchere", "Ladder", "D’Alembert", "Double After a Win", "+1 Win / -1 Loss", "+2 Win / -1 Loss"],
                    value="Martingale"
                )
                labouchere_sequence = gr.Textbox(
                    label="Labouchere Sequence (comma-separated)",
                    value="1, 2, 3, 4",
                    visible=False
                )
            with gr.Row():
                win_button = gr.Button("Win")
                lose_button = gr.Button("Lose")
                reset_progression_button = gr.Button("Reset Progression")
            with gr.Row():
                bankroll_output = gr.Textbox(label="Current Bankroll", value="1000", interactive=False)
                current_bet_output = gr.Textbox(label="Current Bet", value="10", interactive=False)
                next_bet_output = gr.Textbox(label="Next Bet", value="10", interactive=False)
            with gr.Row():
                message_output = gr.Textbox(label="Message", value="Start with base bet of 10 on Even Money (Martingale)", interactive=False)
                status_output = gr.HTML(label="Status", value='<div style="background-color: white; padding: 5px; border-radius: 3px;">Active</div>')

    # 9. Row 9: Color Code Key (Collapsible, with Color Pickers Inside)
    with gr.Accordion("Color Code Key", open=False, elem_id="color-code-key"):
        with gr.Row():
            top_color_picker = gr.ColorPicker(
                label="Top Tier Color",
                value="rgba(255, 255, 0, 0.5)",
                interactive=True,
                elem_id="top-color-picker"
            )
            middle_color_picker = gr.ColorPicker(
                label="Middle Tier Color",
                value="rgba(0, 255, 255, 0.5)",
                interactive=True
            )
            lower_color_picker = gr.ColorPicker(
                label="Lower Tier Color",
                value="rgba(0, 255, 0, 0.5)",
                interactive=True
            )
            reset_colors_button = gr.Button("Reset Colors", elem_classes=["action-button"])
        color_code_output = gr.HTML(label="Color Code Key")

    # 10. Row 10: Analysis Outputs (Collapsible, Renumbered)
    with gr.Accordion("Spin Logic Reactor 🧠", open=False, elem_id="spin-analysis"):
        spin_analysis_output = gr.Textbox(
            label="",
            value="",
            interactive=False,
            lines=5
        )

    with gr.Accordion("Strongest Numbers Tables", open=False, elem_id="strongest-numbers-table"):
        with gr.Row():
            with gr.Column():
                straight_up_html = gr.HTML(label="Strongest Numbers", elem_classes="scrollable-table")
            with gr.Column():
                top_18_html = gr.HTML(label="Top 18 Strongest Numbers (Sorted Lowest to Highest)", elem_classes="scrollable-table")
        with gr.Row():
            strongest_numbers_dropdown = gr.Dropdown(
                label="Select Number of Strongest Numbers",
                choices=["3", "6", "9", "12", "15", "18", "21", "24", "27", "30", "33"],
                value="3",
                allow_custom_value=False,
                interactive=True,
                elem_id="strongest-numbers-dropdown",
                visible=False  # Hide the dropdown
            )
            strongest_numbers_output = gr.Textbox(
                label="Strongest Numbers (Sorted Lowest to Highest)",
                value="",
                lines=2,
                visible=False  # Hide the textbox
            )

    with gr.Accordion("Aggregated Scores", open=False, elem_id="aggregated-scores"):
        with gr.Row():
            with gr.Column():
                with gr.Accordion("Even Money Bets", open=False):
                    even_money_output = gr.Textbox(label="Even Money Bets", lines=10, max_lines=50)
            with gr.Column():
                with gr.Accordion("Dozens", open=False):
                    dozens_output = gr.Textbox(label="Dozens", lines=10, max_lines=50)
        with gr.Row():
            with gr.Column():
                with gr.Accordion("Columns", open=False):
                    columns_output = gr.Textbox(label="Columns", lines=10, max_lines=50)
            with gr.Column():
                with gr.Accordion("Streets", open=False):
                    streets_output = gr.Textbox(label="Streets", lines=10, max_lines=50)
        with gr.Row():
            with gr.Column():
                with gr.Accordion("Corners", open=False):
                    corners_output = gr.Textbox(label="Corners", lines=10, max_lines=50)
            with gr.Column():
                with gr.Accordion("Double Streets", open=False):
                    six_lines_output = gr.Textbox(label="Double Streets", lines=10, max_lines=50)
        with gr.Row():
            with gr.Column():
                with gr.Accordion("Splits", open=False):
                    splits_output = gr.Textbox(label="Splits", lines=10, max_lines=50)
            with gr.Column():
                with gr.Accordion("Sides of Zero", open=False):
                    sides_output = gr.Textbox(label="Sides of Zero", lines=10, max_lines=50)

    # 11. Row 11: Save/Load Session (Collapsible, Renumbered)
    with gr.Accordion("Save/Load Session", open=False, elem_id="save-load-session"):
        with gr.Row():
            save_button = gr.Button("Save Session", elem_id="save-session-btn")
            load_input = gr.File(label="Upload Session")
        save_output = gr.File(label="Download Session")


        
    # CSS and Event Handlers
    gr.HTML("""
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/shepherd.js@10.0.1/dist/css/shepherd.css">
    <script src="https://cdn.jsdelivr.net/npm/shepherd.js@10.0.1/dist/js/shepherd.min.js"></script>
    <style>
      /* General Layout */
      .gr-row { margin: 0 !important; padding: 5px 0 !important; }
      .gr-column { margin: 0 !important; padding: 5px !important; }
      .gr-box { border-radius: 5px !important; }

      /* Compact Visual for Wheel Balance */
      .compact-visual {
          max-width: 300px !important;
          margin: 10px auto !important;
          padding: 5px !important;
          background-color: #f5f5f5 !important;
          border-radius: 5px !important;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1) !important;
      }
      .compact-visual:hover {
          transform: scale(1.02) !important;
          transition: transform 0.2s ease !important;
      }
      
      /* Ensure Header Stays at the Top */
      #header-row {
          position: fixed !important;
          top: 0 !important;
          left: 0 !important;
          right: 0 !important;
          z-index: 1000 !important;
          background-color: white !important;
          padding: 10px 0 !important;
          margin: 0 !important;
          display: flex !important;
          align-items: center !important;
          justify-content: center !important;
          flex-wrap: wrap !important;
      }
    
      /* Add padding to the body to account for the fixed header */
      body {
          padding-top: 120px !important; /* Increased to account for taller header */
      }
    
      /* Ensure content below header is not overlapped */
      .roulette-table {
          margin-top: 120px !important; /* Match body padding-top */
      }
    
      /* Header Styling */
      .header-title { text-align: center !important; font-size: 2.5em !important; margin-bottom: 5px !important; color: #333 !important; }
    
      /* Fix Selected Spins Label Cutoff */
      #selected-spins-row {
          width: 100% !important;
          max-width: none !important;
          overflow: visible !important;
      }
        #selected-spins label {
            white-space: normal !important;
            width: 100% !important;
            height: auto !important;
            overflow: visible !important;
            display: block !important;
            background-color: #87CEEB;
            color: black;
            padding: 10px 5px !important; /* Increased top/bottom padding */
            border-radius: 3px;
            line-height: 1.5em !important; /* Increased for better spacing */
            font-size: 14px !important; /* Reduced font size */
            margin-top: 5px !important; /* Added to shift text downward */
        }
      #selected-spins {
          width: 100% !important;
          min-width: 800px !important;
      }
    
      /* Roulette Table */
      .roulette-button.green { background-color: green !important; color: white !important; border: 1px solid white !important; text-align: center !important; font-weight: bold !important; }
      .roulette-button.red { background-color: red !important; color: white !important; border: 1px solid white !important; text-align: center !important; font-weight: bold !important; }
      .roulette-button.black { background-color: black !important; color: white !important; border: 1px solid white !important; text-align: center !important; font-weight: bold !important; }
      .roulette-button:hover { opacity: 0.8; }
      .roulette-button.selected { border: 3px solid yellow !important; opacity: 0.9; }
      .roulette-button { margin: 0 !important; padding: 0 !important; width: 40px !important; height: 40px !important; font-size: 14px !important; display: flex !important; align-items: center !important; justify-content: center !important; border: 1px solid white !important; box-sizing: border-box !important; }
      .empty-button { margin: 0 !important; padding: 0 !important; width: 40px !important; height: 40px !important; border: 1px solid white !important; box-sizing: border-box !important; }
      .roulette-table { display: flex !important; flex-direction: column !important; gap: 0 !important; margin: 0 !important; padding: 0 !important; }
      .table-row { display: flex !important; gap: 0 !important; margin: 0 !important; padding: 0 !important; flex-wrap: nowrap !important; line-height: 0 !important; }
    
      /* Buttons */
      button.clear-spins-btn { background-color: #ff4444 !important; color: white !important; border: 1px solid #000 !important; }
      button.clear-spins-btn:hover { background-color: #cc0000 !important; }
      button.generate-spins-btn { background-color: #007bff !important; color: white !important; border: 1px solid #000 !important; }
      button.generate-spins-btn:hover { background-color: #0056b3 !important; }
      .action-button { min-width: 120px !important; padding: 5px 10px !important; font-size: 14px !important; width: 100% !important; box-sizing: border-box !important; }
      button.green-btn { background-color: #28a745 !important; color: white !important; border: 1px solid #000 !important; }
      button.green-btn:hover { background-color: #218838 !important; }
      /* Ensure columns have appropriate spacing */
      .gr-column { margin: 0 !important; padding: 5px !important; display: flex !important; flex-direction: column !important; align-items: stretch !important; }
    
      /* Compact Components */
      .long-slider { width: 100% !important; margin: 0 !important; padding: 0 !important; }
      .long-slider .gr-box { width: 100% !important; }
      /* Target the Accordion and its children */
      .gr-accordion { background-color: #ffffff !important; }
      .gr-accordion * { background-color: #ffffff !important; }
      .gr-accordion .gr-column { background-color: #ffffff !important; }
      .gr-accordion .gr-row { background-color: #ffffff !important; }
    
      /* Section Labels */
      #selected-spins label { background-color: #87CEEB; color: black; padding: 5px; border-radius: 3px; }
      #spin-analysis label { background-color: #90EE90 !important; color: black !important; padding: 5px; border-radius: 3px; }
      #strongest-numbers-table label { background-color: #E6E6FA !important; color: black !important; padding: 5px; border-radius: 3px; }
      #number-of-random-spins label { background-color: #FFDAB9 !important; color: black !important; padding: 5px; border-radius: 3px; }
      #aggregated-scores label { background-color: #FFB6C1 !important; color: black !important; padding: 5px; border-radius: 3px; }
      #select-category label { background-color: #FFFFE0 !important; color: black !important; padding: 5px; border-radius: 3px; }
      
      /* Scrollable Tables */
      .scrollable-table { max-height: 300px; overflow-y: auto; display: block; width: 100%; }
    
      /* Spin Counter Styling */
      .spin-counter {
          font-size: 16px !important;
          font-weight: bold !important;
          color: #ffffff !important;
          background: linear-gradient(135deg, #87CEEB, #5DADE2) !important; /* Soft blue gradient */
          padding: 8px 12px !important;
          border: 2px solid #3498DB !important; /* Darker blue border */
          border-radius: 8px !important;
          margin-top: 0 !important; /* Align with textbox */
          display: flex !important;
          align-items: center !important;
          justify-content: center !important;
          box-shadow: 0 2px 6px rgba(0,0,0,0.2) !important; /* Slightly stronger shadow */
          transition: transform 0.2s ease, box-shadow 0.2s ease !important; /* Smooth hover effect */
      }
      .spin-counter:hover {
          transform: scale(1.05) !important; /* Slight zoom on hover */
          box-shadow: 0 4px 8px rgba(0,0,0,0.3) !important; /* Enhanced shadow on hover */
      }
    
      /* Last Spins Container */
      .last-spins-container {
          background-color: #f5f5f5 !important; /* Light gray background */
          border: 1px solid #d3d3d3 !important; /* Subtle gray border */
          padding: 10px !important;
          border-radius: 5px !important;
          margin-top: 10px !important;
          box-shadow: 0 1px 3px rgba(0,0,0,0.1) !important; /* Very light shadow */
      }
    
      /* Responsive Design */
      @media (max-width: 600px) {
          .roulette-button { min-width: 30px; font-size: 12px; padding: 5px; }
          td, th { padding: 5px; font-size: 12px; }
          .gr-textbox { font-size: 12px; }
          .scrollable-table { max-height: 200px; }
          .long-slider { width: 100% !important; }
          .header-title { font-size: 1.8em !important; }
      }
    
      #strongest-numbers-dropdown select {
          -webkit-appearance: menulist !important;
          -moz-appearance: menulist !important;
          appearance: menulist !important;
      }
      #strategy-dropdown select {
          font-size: 14px;
          padding: 5px;
          background-color: #f9f9f9;
          border: 1px solid #ccc;
          border-radius: 3px;
      }
      #strategy-dropdown select option:checked {
          font-weight: bold;
          background-color: #e0e0ff; /* Light blue to indicate selection */
          color: #000;
      }
      .betting-progression .gr-textbox { width: 100%; margin: 5px 0; }
      .betting-progression .gr-button { width: 100px; margin: 5px; }
      .betting-progression .gr-row { display: flex; flex-wrap: wrap; gap: 10px; }
    
      /* Shepherd.js Tweaks */
      .shepherd-modal-overlay-container { opacity: 0.5; z-index: 999; } /* Ensure overlay is below fullscreen */
      .shepherd-button { background-color: #007bff; color: white; padding: 5px 10px; border-radius: 3px; }
      .shepherd-button:hover { background-color: #0056b3; }
    </style>
    """)
    print("CSS Updated")

    # Lines 4888-4920 (Updated Section with `toggle_labouchere` and Fixed Indentation)
    def toggle_labouchere(progression):
        return gr.update(visible=progression == "Labouchere")

    def validate_spins_input(spins_input):
        if not spins_input or not spins_input.strip():
            return None, "<h4>Last Spins</h4><p>No spins yet.</p>"
        
        raw_spins = [spin.strip() for spin in spins_input.split(",") if spin.strip()]
        errors = []
        valid_spins = []
        
        for spin in raw_spins:
            try:
                num = int(spin)
                if not (0 <= num <= 36):
                    errors.append(f"'{spin}' is out of range (0-36)")
                else:
                    valid_spins.append(spin)
            except ValueError:
                errors.append(f"'{spin}' is not a number")
        
        if errors:
            error_msg = "Invalid inputs:\n- " + "\n- ".join(errors)
            gr.Warning(error_msg)
            return spins_input, f"<h4>Last Spins</h4><p>{error_msg}</p>"
        
        return ", ".join(valid_spins), format_spins_as_html(", ".join(valid_spins), last_spin_count.value)

    spins_textbox.change(
        fn=validate_spins_input,
        inputs=spins_textbox,
        outputs=[spins_display, last_spin_display]
    )
    spins_display.change(
        fn=update_spin_counter,
        inputs=[],
        outputs=[spin_counter]
    ).then(
        fn=format_spins_as_html,
        inputs=[spins_display, last_spin_count],
        outputs=[last_spin_display]
    )

    clear_spins_button.click(
        fn=clear_spins,
        inputs=[],
        outputs=[spins_display, spins_textbox, spin_analysis_output, last_spin_display, spin_counter]
    )

    clear_all_button.click(
        fn=clear_all,
        inputs=[],
        outputs=[
            spins_display, spins_textbox, spin_analysis_output, last_spin_display,
            even_money_output, dozens_output, columns_output, streets_output,
            corners_output, six_lines_output, splits_output, sides_output,
            straight_up_html, top_18_html, strongest_numbers_output, spin_counter
        ]
    ).then(
        fn=clear_outputs,
        inputs=[],
        outputs=[
            spin_analysis_output, even_money_output, dozens_output, columns_output,
            streets_output, corners_output, six_lines_output, splits_output,
            sides_output, straight_up_html, top_18_html, strongest_numbers_output,
            dynamic_table_output, strategy_output, color_code_output
        ]
    ).then(
        fn=dozen_tracker,
        inputs=[dozen_tracker_spins_dropdown, dozen_tracker_consecutive_hits_dropdown, dozen_tracker_alert_checkbox, dozen_tracker_sequence_length_dropdown, dozen_tracker_follow_up_spins_dropdown, dozen_tracker_sequence_alert_checkbox],
        outputs=[gr.State(), dozen_tracker_output, dozen_tracker_sequence_output]
    )

    generate_spins_button.click(
        fn=generate_random_spins,
        inputs=[gr.State(value="5"), spins_display, last_spin_count],
        outputs=[spins_display, spins_textbox, spin_analysis_output, spin_counter]
    ).then(
        fn=format_spins_as_html,
        inputs=[spins_display, last_spin_count],
        outputs=[last_spin_display]
    )

    last_spin_count.change(
        fn=format_spins_as_html,
        inputs=[spins_display, last_spin_count],
        outputs=[last_spin_display]
    )

    def update_strategy_dropdown(category):
        if category == "None":
            return gr.update(choices=["None"], value="None")
        return gr.update(choices=strategy_categories[category], value=strategy_categories[category][0])

    category_dropdown.change(
        fn=update_strategy_dropdown,
        inputs=category_dropdown,
        outputs=strategy_dropdown
    )

    reset_strategy_button.click(
        fn=reset_strategy_dropdowns,
        inputs=[],
        outputs=[category_dropdown, strategy_dropdown, strategy_dropdown]
    ).then(
        fn=lambda category: gr.update(choices=strategy_categories[category], value=strategy_categories[category][0]),
        inputs=[category_dropdown],
        outputs=[strategy_dropdown]
    )

    def toggle_neighbours_slider(strategy_name):
        is_visible = strategy_name == "Neighbours of Strong Number"
        return (
            gr.update(visible=is_visible),
            gr.update(visible=is_visible)
        )

    strategy_dropdown.change(
        fn=toggle_neighbours_slider,
        inputs=[strategy_dropdown],
        outputs=[neighbours_count_slider, strong_numbers_count_slider]
    ).then(
        fn=show_strategy_recommendations,
        inputs=[strategy_dropdown, neighbours_count_slider, strong_numbers_count_slider],
        outputs=[strategy_output]
    ).then(
        fn=lambda strategy, neighbours_count, strong_numbers_count, dozen_tracker_spins, top_color, middle_color, lower_color: (print(f"Updating Dynamic Table with Strategy: {strategy}, Neighbours Count: {neighbours_count}, Strong Numbers Count: {strong_numbers_count}, Dozen Tracker Spins: {dozen_tracker_spins}, Colors: {top_color}, {middle_color}, {lower_color}"), create_dynamic_table(strategy if strategy != "None" else None, neighbours_count, strong_numbers_count, dozen_tracker_spins, top_color, middle_color, lower_color))[-1],
        inputs=[strategy_dropdown, neighbours_count_slider, strong_numbers_count_slider, dozen_tracker_spins_dropdown, top_color_picker, middle_color_picker, lower_color_picker],
        outputs=[dynamic_table_output]
    )

    analyze_button.click(
        fn=analyze_spins,
        inputs=[spins_display, reset_scores_checkbox, strategy_dropdown, neighbours_count_slider, strong_numbers_count_slider],
        outputs=[
            spin_analysis_output, even_money_output, dozens_output, columns_output,
            streets_output, corners_output, six_lines_output, splits_output,
            sides_output, straight_up_html, top_18_html, strongest_numbers_output,
            dynamic_table_output, strategy_output, wheel_balance_html
        ]
    ).then(
        fn=lambda strategy, neighbours_count, strong_numbers_count, dozen_tracker_spins, top_color, middle_color, lower_color: create_dynamic_table(strategy if strategy != "None" else None, neighbours_count, strong_numbers_count, dozen_tracker_spins, top_color, middle_color, lower_color),
        inputs=[strategy_dropdown, neighbours_count_slider, strong_numbers_count_slider, dozen_tracker_spins_dropdown, top_color_picker, middle_color_picker, lower_color_picker],
        outputs=[dynamic_table_output]
    ).then(
        fn=create_color_code_table,
        inputs=[],
        outputs=[color_code_output]
    ).then(
        fn=dozen_tracker,
        inputs=[dozen_tracker_spins_dropdown, dozen_tracker_consecutive_hits_dropdown, dozen_tracker_alert_checkbox, dozen_tracker_sequence_length_dropdown, dozen_tracker_follow_up_spins_dropdown, dozen_tracker_sequence_alert_checkbox],
        outputs=[gr.State(), dozen_tracker_output, dozen_tracker_sequence_output]
    )

    save_button.click(
        fn=save_session,
        inputs=[],
        outputs=[save_output]
    )

    load_input.change(
        fn=load_session,
        inputs=[load_input, strategy_dropdown, neighbours_count_slider, strong_numbers_count_slider],
        outputs=[
            spins_display, spins_textbox, spin_analysis_output, even_money_output, dozens_output, columns_output,
            streets_output, corners_output, six_lines_output, splits_output, sides_output,
            straight_up_html, top_18_html, strongest_numbers_output, dynamic_table_output, strategy_output
        ]
    ).then(
        fn=lambda strategy, neighbours_count, strong_numbers_count, dozen_tracker_spins, top_color, middle_color, lower_color: create_dynamic_table(strategy if strategy != "None" else None, neighbours_count, strong_numbers_count, dozen_tracker_spins, top_color, middle_color, lower_color),
        inputs=[strategy_dropdown, neighbours_count_slider, strong_numbers_count_slider, dozen_tracker_spins_dropdown, top_color_picker, middle_color_picker, lower_color_picker],
        outputs=[dynamic_table_output]
    ).then(
        fn=format_spins_as_html,
        inputs=[spins_display, last_spin_count],
        outputs=[last_spin_display]
    ).then(
        fn=create_color_code_table,
        inputs=[],
        outputs=[color_code_output]
    ).then(
        fn=dozen_tracker,
        inputs=[dozen_tracker_spins_dropdown, dozen_tracker_consecutive_hits_dropdown, dozen_tracker_alert_checkbox, dozen_tracker_sequence_length_dropdown, dozen_tracker_follow_up_spins_dropdown, dozen_tracker_sequence_alert_checkbox],
        outputs=[gr.State(), dozen_tracker_output, dozen_tracker_sequence_output]
    )

    undo_button.click(
        fn=undo_last_spin,
        inputs=[spins_display, gr.State(value=1), strategy_dropdown, neighbours_count_slider, strong_numbers_count_slider],
        outputs=[
            spin_analysis_output, even_money_output, dozens_output, columns_output,
            streets_output, corners_output, six_lines_output, splits_output,
            sides_output, straight_up_html, top_18_html, strongest_numbers_output,
            spins_textbox, spins_display, dynamic_table_output, strategy_output,
            color_code_output, spin_counter
        ]
    ).then(
        fn=lambda strategy, neighbours_count, strong_numbers_count, dozen_tracker_spins, top_color, middle_color, lower_color: create_dynamic_table(strategy if strategy != "None" else None, neighbours_count, strong_numbers_count, dozen_tracker_spins, top_color, middle_color, lower_color),
        inputs=[strategy_dropdown, neighbours_count_slider, strong_numbers_count_slider, dozen_tracker_spins_dropdown, top_color_picker, middle_color_picker, lower_color_picker],
        outputs=[dynamic_table_output]
    ).then(
        fn=dozen_tracker,
        inputs=[dozen_tracker_spins_dropdown, dozen_tracker_consecutive_hits_dropdown, dozen_tracker_alert_checkbox, dozen_tracker_sequence_length_dropdown, dozen_tracker_follow_up_spins_dropdown, dozen_tracker_sequence_alert_checkbox],
        outputs=[gr.State(), dozen_tracker_output, dozen_tracker_sequence_output]
    )

    neighbours_count_slider.change(
        fn=lambda strategy, neighbours_count, strong_numbers_count, dozen_tracker_spins, top_color, middle_color, lower_color: create_dynamic_table(strategy if strategy != "None" else None, neighbours_count, strong_numbers_count, dozen_tracker_spins, top_color, middle_color, lower_color),
        inputs=[strategy_dropdown, neighbours_count_slider, strong_numbers_count_slider, dozen_tracker_spins_dropdown, top_color_picker, middle_color_picker, lower_color_picker],
        outputs=[dynamic_table_output]
    ).then(
        fn=show_strategy_recommendations,
        inputs=[strategy_dropdown, neighbours_count_slider, strong_numbers_count_slider],
        outputs=[strategy_output]
    )

    strong_numbers_count_slider.change(
        fn=lambda strategy, neighbours_count, strong_numbers_count, dozen_tracker_spins, top_color, middle_color, lower_color: create_dynamic_table(strategy if strategy != "None" else None, neighbours_count, strong_numbers_count, dozen_tracker_spins, top_color, middle_color, lower_color),
        inputs=[strategy_dropdown, neighbours_count_slider, strong_numbers_count_slider, dozen_tracker_spins_dropdown, top_color_picker, middle_color_picker, lower_color_picker],
        outputs=[dynamic_table_output]
    ).then(
        fn=show_strategy_recommendations,
        inputs=[strategy_dropdown, neighbours_count_slider, strong_numbers_count_slider],
        outputs=[strategy_output]
    )

    reset_colors_button.click(
        fn=reset_colors,
        inputs=[],
        outputs=[top_color_picker, middle_color_picker, lower_color_picker]
    ).then(
        fn=lambda strategy, neighbours_count, strong_numbers_count, dozen_tracker_spins, top_color, middle_color, lower_color: create_dynamic_table(strategy if strategy != "None" else None, neighbours_count, strong_numbers_count, dozen_tracker_spins, top_color, middle_color, lower_color),
        inputs=[strategy_dropdown, neighbours_count_slider, strong_numbers_count_slider, dozen_tracker_spins_dropdown, top_color_picker, middle_color_picker, lower_color_picker],
        outputs=[dynamic_table_output]
    )

    clear_last_spins_button.click(
        fn=clear_last_spins_display,
        inputs=[],
        outputs=[last_spin_display, spin_counter]
    )

    top_color_picker.change(
        fn=lambda strategy, neighbours_count, strong_numbers_count, dozen_tracker_spins, top_color, middle_color, lower_color: create_dynamic_table(strategy if strategy != "None" else None, neighbours_count, strong_numbers_count, dozen_tracker_spins, top_color, middle_color, lower_color),
        inputs=[strategy_dropdown, neighbours_count_slider, strong_numbers_count_slider, dozen_tracker_spins_dropdown, top_color_picker, middle_color_picker, lower_color_picker],
        outputs=[dynamic_table_output]
    )

    middle_color_picker.change(
        fn=lambda strategy, neighbours_count, strong_numbers_count, dozen_tracker_spins, top_color, middle_color, lower_color: create_dynamic_table(strategy if strategy != "None" else None, neighbours_count, strong_numbers_count, dozen_tracker_spins, top_color, middle_color, lower_color),
        inputs=[strategy_dropdown, neighbours_count_slider, strong_numbers_count_slider, dozen_tracker_spins_dropdown, top_color_picker, middle_color_picker, lower_color_picker],
        outputs=[dynamic_table_output]
    )

    lower_color_picker.change(
        fn=lambda strategy, neighbours_count, strong_numbers_count, dozen_tracker_spins, top_color, middle_color, lower_color: create_dynamic_table(strategy if strategy != "None" else None, neighbours_count, strong_numbers_count, dozen_tracker_spins, top_color, middle_color, lower_color),
        inputs=[strategy_dropdown, neighbours_count_slider, strong_numbers_count_slider, dozen_tracker_spins_dropdown, top_color_picker, middle_color_picker, lower_color_picker],
        outputs=[dynamic_table_output]
    )

    # Dozen Tracker Event Handler
    dozen_tracker_spins_dropdown.change(
        fn=dozen_tracker,
        inputs=[dozen_tracker_spins_dropdown, dozen_tracker_consecutive_hits_dropdown, dozen_tracker_alert_checkbox, dozen_tracker_sequence_length_dropdown, dozen_tracker_follow_up_spins_dropdown, dozen_tracker_sequence_alert_checkbox],
        outputs=[gr.State(), dozen_tracker_output, dozen_tracker_sequence_output]
    ).then(
        fn=lambda strategy, neighbours_count, strong_numbers_count, dozen_tracker_spins, top_color, middle_color, lower_color: create_dynamic_table(strategy if strategy != "None" else None, neighbours_count, strong_numbers_count, dozen_tracker_spins, top_color, middle_color, lower_color),
        inputs=[strategy_dropdown, neighbours_count_slider, strong_numbers_count_slider, dozen_tracker_spins_dropdown, top_color_picker, middle_color_picker, lower_color_picker],
        outputs=[dynamic_table_output]
    )

    # Dozen Tracker Consecutive Hits Event Handler
    dozen_tracker_consecutive_hits_dropdown.change(
        fn=dozen_tracker,
        inputs=[dozen_tracker_spins_dropdown, dozen_tracker_consecutive_hits_dropdown, dozen_tracker_alert_checkbox, dozen_tracker_sequence_length_dropdown, dozen_tracker_follow_up_spins_dropdown, dozen_tracker_sequence_alert_checkbox],
        outputs=[gr.State(), dozen_tracker_output, dozen_tracker_sequence_output]
    ).then(
        fn=lambda strategy, neighbours_count, strong_numbers_count, dozen_tracker_spins, top_color, middle_color, lower_color: create_dynamic_table(strategy if strategy != "None" else None, neighbours_count, strong_numbers_count, dozen_tracker_spins, top_color, middle_color, lower_color),
        inputs=[strategy_dropdown, neighbours_count_slider, strong_numbers_count_slider, dozen_tracker_spins_dropdown, top_color_picker, middle_color_picker, lower_color_picker],
        outputs=[dynamic_table_output]
    )

    # Dozen Tracker Alert Checkbox Event Handler
    dozen_tracker_alert_checkbox.change(
        fn=dozen_tracker,
        inputs=[dozen_tracker_spins_dropdown, dozen_tracker_consecutive_hits_dropdown, dozen_tracker_alert_checkbox, dozen_tracker_sequence_length_dropdown, dozen_tracker_follow_up_spins_dropdown, dozen_tracker_sequence_alert_checkbox],
        outputs=[gr.State(), dozen_tracker_output, dozen_tracker_sequence_output]
    ).then(
        fn=lambda strategy, neighbours_count, strong_numbers_count, dozen_tracker_spins, top_color, middle_color, lower_color: create_dynamic_table(strategy if strategy != "None" else None, neighbours_count, strong_numbers_count, dozen_tracker_spins, top_color, middle_color, lower_color),
        inputs=[strategy_dropdown, neighbours_count_slider, strong_numbers_count_slider, dozen_tracker_spins_dropdown, top_color_picker, middle_color_picker, lower_color_picker],
        outputs=[dynamic_table_output]
    )

    # Dozen Tracker Sequence Length Event Handler
    dozen_tracker_sequence_length_dropdown.change(
        fn=dozen_tracker,
        inputs=[dozen_tracker_spins_dropdown, dozen_tracker_consecutive_hits_dropdown, dozen_tracker_alert_checkbox, dozen_tracker_sequence_length_dropdown, dozen_tracker_follow_up_spins_dropdown, dozen_tracker_sequence_alert_checkbox],
        outputs=[gr.State(), dozen_tracker_output, dozen_tracker_sequence_output]
    ).then(
        fn=lambda strategy, neighbours_count, strong_numbers_count, dozen_tracker_spins, top_color, middle_color, lower_color: create_dynamic_table(strategy if strategy != "None" else None, neighbours_count, strong_numbers_count, dozen_tracker_spins, top_color, middle_color, lower_color),
        inputs=[strategy_dropdown, neighbours_count_slider, strong_numbers_count_slider, dozen_tracker_spins_dropdown, top_color_picker, middle_color_picker, lower_color_picker],
        outputs=[dynamic_table_output]
    )

    # Dozen Tracker Follow-Up Spins Event Handler
    dozen_tracker_follow_up_spins_dropdown.change(
        fn=dozen_tracker,
        inputs=[dozen_tracker_spins_dropdown, dozen_tracker_consecutive_hits_dropdown, dozen_tracker_alert_checkbox, dozen_tracker_sequence_length_dropdown, dozen_tracker_follow_up_spins_dropdown, dozen_tracker_sequence_alert_checkbox],
        outputs=[gr.State(), dozen_tracker_output, dozen_tracker_sequence_output]
    ).then(
        fn=lambda strategy, neighbours_count, strong_numbers_count, dozen_tracker_spins, top_color, middle_color, lower_color: create_dynamic_table(strategy if strategy != "None" else None, neighbours_count, strong_numbers_count, dozen_tracker_spins, top_color, middle_color, lower_color),
        inputs=[strategy_dropdown, neighbours_count_slider, strong_numbers_count_slider, dozen_tracker_spins_dropdown, top_color_picker, middle_color_picker, lower_color_picker],
        outputs=[dynamic_table_output]
    )

    # Dozen Tracker Sequence Alert Checkbox Event Handler
    dozen_tracker_sequence_alert_checkbox.change(
        fn=dozen_tracker,
        inputs=[dozen_tracker_spins_dropdown, dozen_tracker_consecutive_hits_dropdown, dozen_tracker_alert_checkbox, dozen_tracker_sequence_length_dropdown, dozen_tracker_follow_up_spins_dropdown, dozen_tracker_sequence_alert_checkbox],
        outputs=[gr.State(), dozen_tracker_output, dozen_tracker_sequence_output]
    ).then(
        fn=lambda strategy, neighbours_count, strong_numbers_count, dozen_tracker_spins, top_color, middle_color, lower_color: create_dynamic_table(strategy if strategy != "None" else None, neighbours_count, strong_numbers_count, dozen_tracker_spins, top_color, middle_color, lower_color),
        inputs=[strategy_dropdown, neighbours_count_slider, strong_numbers_count_slider, dozen_tracker_spins_dropdown, top_color_picker, middle_color_picker, lower_color_picker],
        outputs=[dynamic_table_output]
    )

    # Casino data event handlers
    inputs_list = [
        spins_count_dropdown, even_percent, odd_percent, red_percent, black_percent,
        low_percent, high_percent, dozen1_percent, dozen2_percent, dozen3_percent,
        col1_percent, col2_percent, col3_percent, use_winners_checkbox
    ]
    spins_count_dropdown.change(
        fn=update_casino_data,
        inputs=inputs_list,
        outputs=[casino_data_output]
    )
    even_percent.change(
        fn=update_casino_data,
        inputs=inputs_list,
        outputs=[casino_data_output]
    )
    odd_percent.change(
        fn=update_casino_data,
        inputs=inputs_list,
        outputs=[casino_data_output]
    )
    red_percent.change(
        fn=update_casino_data,
        inputs=inputs_list,
        outputs=[casino_data_output]
    )
    black_percent.change(
        fn=update_casino_data,
        inputs=inputs_list,
        outputs=[casino_data_output]
    )
    low_percent.change(
        fn=update_casino_data,
        inputs=inputs_list,
        outputs=[casino_data_output]
    )
    high_percent.change(
        fn=update_casino_data,
        inputs=inputs_list,
        outputs=[casino_data_output]
    )
    dozen1_percent.change(
        fn=update_casino_data,
        inputs=inputs_list,
        outputs=[casino_data_output]
    )
    dozen2_percent.change(
        fn=update_casino_data,
        inputs=inputs_list,
        outputs=[casino_data_output]
    )
    dozen3_percent.change(
        fn=update_casino_data,
        inputs=inputs_list,
        outputs=[casino_data_output]
    )
    col1_percent.change(
        fn=update_casino_data,
        inputs=inputs_list,
        outputs=[casino_data_output]
    )
    col2_percent.change(
        fn=update_casino_data,
        inputs=inputs_list,
        outputs=[casino_data_output]
    )
    col3_percent.change(
        fn=update_casino_data,
        inputs=inputs_list,
        outputs=[casino_data_output]
    )
    use_winners_checkbox.change(
        fn=update_casino_data,
        inputs=inputs_list,
        outputs=[casino_data_output]
    ).then(
        fn=lambda strategy, neighbours_count, strong_numbers_count, dozen_tracker_spins, top_color, middle_color, lower_color: create_dynamic_table(strategy if strategy != "None" else None, neighbours_count, strong_numbers_count, dozen_tracker_spins, top_color, middle_color, lower_color),
        inputs=[strategy_dropdown, neighbours_count_slider, strong_numbers_count_slider, dozen_tracker_spins_dropdown, top_color_picker, middle_color_picker, lower_color_picker],
        outputs=[dynamic_table_output]
    )
    reset_casino_data_button.click(
        fn=lambda: (
            "100", "00", "00", "00", "00", "00", "00", "00", "00", "00", "00", "00", "00", False,
            "<p>Casino data reset to defaults.</p>"
        ),
        inputs=[],
        outputs=[
            spins_count_dropdown, even_percent, odd_percent, red_percent, black_percent,
            low_percent, high_percent, dozen1_percent, dozen2_percent, dozen3_percent,
            col1_percent, col2_percent, col3_percent, use_winners_checkbox, casino_data_output
        ]
    ).then(
        fn=create_dynamic_table,
        inputs=[strategy_dropdown, neighbours_count_slider, strong_numbers_count_slider, dozen_tracker_spins_dropdown, top_color_picker, middle_color_picker, lower_color_picker],
        outputs=[dynamic_table_output]
    )

    # Betting progression event handlers
    def update_config(bankroll, base_unit, stop_loss, stop_win, bet_type, progression, sequence):
        state.bankroll = bankroll
        state.initial_bankroll = bankroll
        state.base_unit = base_unit
        state.stop_loss = stop_loss
        state.stop_win = stop_win
        state.bet_type = bet_type
        state.progression = progression
        if progression == "Labouchere":
            try:
                state.progression_state = [int(x.strip()) for x in sequence.split(",")]
            except ValueError:
                state.progression_state = [1, 2, 3, 4]
                return bankroll, base_unit, base_unit, "Invalid sequence, using default [1, 2, 3, 4]", '<div style="background-color: white; padding: 5px; border-radius: 3px;">Active</div>'
        state.reset_progression()
        return state.bankroll, state.current_bet, state.next_bet, state.message, f'<div style="background-color: {state.status_color}; padding: 5px; border-radius: 3px;">{state.status}</div>'

    bankroll_input.change(
        fn=update_config,
        inputs=[bankroll_input, base_unit_input, stop_loss_input, stop_win_input, bet_type_dropdown, progression_dropdown, labouchere_sequence],
        outputs=[bankroll_output, current_bet_output, next_bet_output, message_output, status_output]
    )
    base_unit_input.change(
        fn=update_config,
        inputs=[bankroll_input, base_unit_input, stop_loss_input, stop_win_input, bet_type_dropdown, progression_dropdown, labouchere_sequence],
        outputs=[bankroll_output, current_bet_output, next_bet_output, message_output, status_output]
    )
    stop_loss_input.change(
        fn=update_config,
        inputs=[bankroll_input, base_unit_input, stop_loss_input, stop_win_input, bet_type_dropdown, progression_dropdown, labouchere_sequence],
        outputs=[bankroll_output, current_bet_output, next_bet_output, message_output, status_output]
    )
    stop_win_input.change(
        fn=update_config,
        inputs=[bankroll_input, base_unit_input, stop_loss_input, stop_win_input, bet_type_dropdown, progression_dropdown, labouchere_sequence],
        outputs=[bankroll_output, current_bet_output, next_bet_output, message_output, status_output]
    )
    bet_type_dropdown.change(
        fn=update_config,
        inputs=[bankroll_input, base_unit_input, stop_loss_input, stop_win_input, bet_type_dropdown, progression_dropdown, labouchere_sequence],
        outputs=[bankroll_output, current_bet_output, next_bet_output, message_output, status_output]
    )
    progression_dropdown.change(
        fn=update_config,
        inputs=[bankroll_input, base_unit_input, stop_loss_input, stop_win_input, bet_type_dropdown, progression_dropdown, labouchere_sequence],
        outputs=[bankroll_output, current_bet_output, next_bet_output, message_output, status_output]
    ).then(
        fn=toggle_labouchere,
        inputs=[progression_dropdown],
        outputs=[labouchere_sequence]
    )
    labouchere_sequence.change(
        fn=update_config,
        inputs=[bankroll_input, base_unit_input, stop_loss_input, stop_win_input, bet_type_dropdown, progression_dropdown, labouchere_sequence],
        outputs=[bankroll_output, current_bet_output, next_bet_output, message_output, status_output]
    )
    win_button.click(
        fn=lambda: state.update_progression(True),
        inputs=[],
        outputs=[bankroll_output, current_bet_output, next_bet_output, message_output, status_output]
    )
    lose_button.click(
        fn=lambda: state.update_progression(False),
        inputs=[],
        outputs=[bankroll_output, current_bet_output, next_bet_output, message_output, status_output]
    )
    reset_progression_button.click(
        fn=lambda: state.reset_progression(),
        inputs=[],
        outputs=[bankroll_output, current_bet_output, next_bet_output, message_output, status_output]
    )

    # Add the Shepherd.js tour script here
    gr.HTML("""
<script>
  const tour = new Shepherd.Tour({
    defaultStepOptions: {
      cancelIcon: { enabled: true },
      scrollTo: { behavior: 'smooth', block: 'center' },
      classes: 'shepherd-theme-arrows',
    },
    useModalOverlay: true
  });

  // Debug function to log step transitions
  function logStep(stepId, nextStepId) {
    return () => {
      console.log(`Attempting move from ${stepId} to ${nextStepId}`);
      tour.next();
    };
  }

  // Force accordion open with direct DOM manipulation and Promise
  function forceAccordionOpen(accordionId) {
    console.log(`Checking accordion: ${accordionId}`);
    return new Promise(resolve => {
      const accordion = document.querySelector(accordionId);
      if (!accordion) {
        console.error(`Accordion ${accordionId} not found`);
        resolve();
        return;
      }
      const content = accordion.querySelector('.gr-box') || accordion.nextElementSibling;
      if (content && window.getComputedStyle(content).display === 'none') {
        console.log(`Forcing ${accordionId} open`);
        content.style.display = 'block';
        accordion.setAttribute('open', '');
        setTimeout(() => {
          if (window.getComputedStyle(content).display === 'none') {
            console.warn(`Fallback: Forcing visibility for ${accordionId}`);
            content.style.display = 'block';
          }
          resolve();
        }, 500);
      } else {
        console.log(`${accordionId} already open or no content found`);
        resolve();
      }
    });
  }

  // Part 1–7 (Assumed working)
  tour.addStep({
    id: 'part1',
    title: 'Your Roulette Adventure Begins!',
    text: 'Hey there!<br><iframe width="280" height="158" src="https://www.youtube.com/embed/H7TLQr1HnY0?fs=0" frameborder="0"></iframe>',
    attachTo: { element: '#header-row', on: 'bottom' },
    buttons: [
      { text: 'Next', action: logStep('Part 1', 'Part 2') },
      { text: 'Skip', action: tour.cancel }
    ]
  });

  tour.addStep({
    id: 'part2',
    title: 'Spin the Wheel, Start the Thrill!',
    text: 'Click numbers!<br><iframe width="280" height="158" src="https://www.youtube.com/embed/ja454kZwndo?fs=0" frameborder="0"></iframe>',
    attachTo: { element: '.roulette-table', on: 'right' },
    buttons: [
      { text: 'Back', action: tour.back },
      { text: 'Next', action: logStep('Part 2', 'Part 3') },
      { text: 'Skip', action: tour.cancel }
    ]
  });

  tour.addStep({
    id: 'part3',
    title: 'Peek at Your Spin Streak!',
    text: 'See spins!<br><iframe width="280" height="158" src="https://www.youtube.com/embed/a9brOFMy9sA?fs=0" frameborder="0"></iframe>',
    attachTo: { element: '.last-spins-container', on: 'bottom' },
    buttons: [
      { text: 'Back', action: tour.back },
      { text: 'Next', action: logStep('Part 3', 'Part 4') },
      { text: 'Skip', action: tour.cancel }
    ]
  });

  tour.addStep({
    id: 'part4',
    title: 'Master Your Spin Moves!',
    text: 'Control spins!<br><iframe width="280" height="158" src="https://www.youtube.com/embed/xG8z1S4HJK4?fs=0" frameborder="0"></iframe>',
    attachTo: { element: '#undo-spins-btn', on: 'bottom' },
    buttons: [
      { text: 'Back', action: tour.back },
      { text: 'Next', action: logStep('Part 4', 'Part 5') },
      { text: 'Skip', action: tour.cancel }
    ]
  });

  tour.addStep({
    id: 'part5',
    title: 'Jot Spins, Count Wins!',
    text: 'Type spins!<br><iframe width="280" height="158" src="https://www.youtube.com/embed/2-k1EyKUM8U?fs=0" frameborder="0"></iframe>',
    attachTo: { element: '#selected-spins', on: 'bottom' },
    buttons: [
      { text: 'Back', action: tour.back },
      { text: 'Next', action: logStep('Part 5', 'Part 6') },
      { text: 'Skip', action: tour.cancel }
    ]
  });

  tour.addStep({
    id: 'part6',
    title: 'Analyze and Reset Like a Pro!',
    text: 'Analyze!<br><iframe width="280" height="158" src="https://www.youtube.com/embed/8plHP2RIR3o?fs=0" frameborder="0"></iframe>',
    attachTo: { element: '.green-btn', on: 'bottom' },
    buttons: [
      { text: 'Back', action: tour.back },
      { text: 'Next', action: logStep('Part 6', 'Part 7') },
      { text: 'Skip', action: tour.cancel }
    ]
  });

  tour.addStep({
    id: 'part7',
    title: 'Light Up Your Lucky Spots!',
    text: 'Dynamic table!<br><iframe width="280" height="158" src="https://www.youtube.com/embed/zT9d06sn07E?fs=0" frameborder="0"></iframe>',
    attachTo: { element: '#dynamic-table-heading', on: 'bottom' },
    buttons: [
      { text: 'Back', action: tour.back },
      { text: 'Next', action: logStep('Part 7', 'Part 8') },
      { text: 'Skip', action: tour.cancel }
    ]
  });

  // Part 8: Bet Smart, Track the Art!
  tour.addStep({
    id: 'part8',
    title: 'Bet Smart, Track the Art!',
    text: 'Track bets!<br><iframe width="280" height="158" src="https://www.youtube.com/embed/jkE-w2MOJ0o?fs=0" frameborder="0"></iframe>',
    attachTo: { element: '.betting-progression', on: 'top' },
    beforeShowPromise: function() {
      return forceAccordionOpen('.betting-progression');
    },
    buttons: [
      { text: 'Back', action: tour.back },
      { text: 'Next', action: logStep('Part 8', 'Part 9') },
      { text: 'Skip', action: tour.cancel }
    ]
  });

  // Part 9: Paint Your Winning Hue!
  tour.addStep({
    id: 'part9',
    title: 'Paint Your Winning Hue!',
    text: 'Make your table pop!<br><iframe width="280" height="158" src="https://www.youtube.com/embed/pUtW2HnWVL8?fs=0" frameborder="0"></iframe>',
    attachTo: { element: '#color-code-key', on: 'top' },
    beforeShowPromise: function() {
      return forceAccordionOpen('#color-code-key');
    },
    buttons: [
      { text: 'Back', action: tour.back },
      { text: 'Next', action: logStep('Part 9', 'Part 10') },
      { text: 'Skip', action: tour.cancel }
    ]
  });

  // Part 10: Decode the Color Clue!
  tour.addStep({
    id: 'part10',
    title: 'Decode the Color Clue!',
    text: 'Confused by colors?<br><iframe width="280" height="158" src="https://www.youtube.com/embed/PGBEoOOh9Gk?fs=0" frameborder="0"></iframe>',
    attachTo: { element: '#color-code-key', on: 'top' },
    beforeShowPromise: function() {
      return forceAccordionOpen('#color-code-key');
    },
    buttons: [
      { text: 'Back', action: tour.back },
      { text: 'Next', action: logStep('Part 10', 'Part 11') },
      { text: 'Skip', action: tour.cancel }
    ]
  });

  // Part 11: Unleash the Spin Secrets!
  tour.addStep({
    id: 'part11',
    title: 'Unleash the Spin Secrets!',
    text: 'Deep dive!<br><iframe width="280" height="158" src="https://www.youtube.com/embed/MpcuwWnMdrg?fs=0" frameborder="0"></iframe>',
    attachTo: { element: '#spin-analysis', on: 'top' },
    beforeShowPromise: function() {
      return forceAccordionOpen('#spin-analysis');
    },
    buttons: [
      { text: 'Back', action: tour.back },
      { text: 'Next', action: logStep('Part 11', 'Part 12') },
      { text: 'Skip', action: tour.cancel }
    ]
  });

  // Part 12: Save Your Spin Glory!
  tour.addStep({
    id: 'part12',
    title: 'Save Your Spin Glory!',
    text: 'Save/load here!<br><iframe width="280" height="158" src="https://www.youtube.com/embed/pHLEa2I0jjE?fs=0" frameborder="0"></iframe>',
    attachTo: { element: '#save-load-session', on: 'top' },
    beforeShowPromise: function() {
      return forceAccordionOpen('#save-load-session');
    },
    buttons: [
      { text: 'Back', action: tour.back },
      { text: 'Next', action: logStep('Part 12', 'Part 13') },
      { text: 'Skip', action: tour.cancel }
    ]
  });

  // Part 13: Pick Your Strategy Groove!
  tour.addStep({
    id: 'part13',
    title: 'Pick Your Strategy Groove!',
    text: 'Choose your flow!<br><iframe width="280" height="158" src="https://www.youtube.com/embed/iuGEltUVbqc?fs=0" frameborder="0"></iframe>',
    attachTo: { element: '#select-category', on: 'left' },
    buttons: [
      { text: 'Back', action: tour.back },
      { text: 'Next', action: logStep('Part 13', 'Part 14') },
      { text: 'Skip', action: tour.cancel }
    ]
  });

  // Part 14: Boost Wins with Casino Intel!
  tour.addStep({
    id: 'part14',
    title: 'Boost Wins with Casino Intel!',
    text: 'Add casino stats!<br><iframe width="280" height="158" src="https://www.youtube.com/embed/FJIczwv9_Ss?fs=0" frameborder="0"></iframe>',
    attachTo: { element: '#casino-data-insights', on: 'top' },
    beforeShowPromise: function() {
      return forceAccordionOpen('#casino-data-insights');
    },
    buttons: [
      { text: 'Back', action: tour.back },
      { text: 'Finish', action: () => { console.log('Tour completed'); tour.complete(); } }
    ]
  });

  function startTour() {
    console.log('Tour starting...');
    setTimeout(() => {
      if (document.querySelector('#header-row')) {
        console.log('DOM ready, starting tour');
        tour.start();
      } else {
        console.error('Header row not found, tour aborted');
      }
    }, 500);
  }

  document.addEventListener("DOMContentLoaded", () => {
    console.log("DOM Loaded, #header-row exists:", !!document.querySelector("#header-row"));
  });
</script>
    """)
    
    # Launch the interface
    demo.launch()