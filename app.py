import gradio as gr
import pandas as pd
import json
from itertools import combinations
import random
from roulette_data import *

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
        self.selected_numbers = set()
        self.last_spins = []

# Create an instance of RouletteState
state = RouletteState()

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

# Define betting progression for Victory Vortex (16 steps)
betting_progression_vv = [
    ("(Bankroll: $1.00)", "1ST BET", "$1.00"),
    ("(Bankroll: $9.00)", "2ND BET", "$8.00"),
    ("(Bankroll: $20.00)", "3RD BET", "$11.00"),
    ("(Bankroll: $36.00)", "4TH BET", "$16.00"),
    ("(Bankroll: $60.00)", "5TH BET", "$24.00"),
    ("(Bankroll: $95.00)", "6TH BET", "$35.00"),
    ("(Bankroll: $147.00)", "7TH BET", "$52.00"),
    ("(Bankroll: $225.00)", "8TH BET", "$78.00"),
    ("(Bankroll: $341.00)", "9TH BET", "$116.00"),
    ("(Bankroll: $515.00)", "10TH BET", "$174.00"),
    ("(Bankroll: $775.00)", "11TH BET", "$260.00"),
    ("(Bankroll: $1,165.00)", "12TH BET", "$390.00"),
    ("(Bankroll: $1,749.00)", "13TH BET", "$584.00"),
    ("(Bankroll: $2,625.00)", "14TH BET", "$876.00"),
    ("(Bankroll: $3,938.00)", "15TH BET", "$1,313.00"),
    ("(Bankroll: $5,907.00)", "16TH BET", "$1,969.00")
]

def format_spins_as_html(spins, num_to_show):
    if not spins:
        return ""
    
    # Split the spins string into a list and reverse to get the most recent first
    spin_list = spins.split(", ") if spins else []
    spin_list = spin_list[-int(num_to_show):] if spin_list else []  # Take the last N spins
    
    if not spin_list:
        return ""
    
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
        html_spins.append(f'<span style="background-color: {color}; color: white; padding: 2px 5px; margin-right: 5px; border-radius: 3px;">{spin}</span>')
    
    return "".join(html_spins)

def add_spin(number, current_spins, num_to_show):
    spins = current_spins.split(", ") if current_spins else []
    if spins == [""]:
        spins = []
    try:
        num = int(number.strip())  # Remove any whitespace
        if not (0 <= num <= 36):
            return current_spins, current_spins, f"Error: '{number}' is out of range. Please use numbers between 0 and 36."
        spins.append(str(num))
        state.selected_numbers.add(num)
        new_spins = ", ".join(spins)
        return new_spins, new_spins, format_spins_as_html(new_spins, num_to_show)
    except ValueError:
        return current_spins, current_spins, f"Error: '{number}' is not a valid number. Please enter a whole number between 0 and 36."
    except Exception as e:
        return current_spins, current_spins, f"Unexpected error: {str(e)}. Please try again or contact support."

# Function to clear spins
def clear_spins():
    state.selected_numbers.clear()
    state.last_spins = []
    return "", "", "Spins cleared successfully!", ""

# Function to save the session
def save_session():
    session_data = {
        "spins": state.last_spins,
        "scores": state.scores,
        "even_money_scores": state.even_money_scores,
        "dozen_scores": state.dozen_scores,
        "column_scores": state.column_scores,
        "street_scores": state.street_scores,
        "corner_scores": state.corner_scores,
        "six_line_scores": state.six_line_scores,
        "split_scores": state.split_scores,
        "side_scores": state.side_scores
    }
    with open("session.json", "w") as f:
        json.dump(session_data, f)
    return "session.json"

# Function to load the session
def load_session(file):
    try:
        if file is None:
            return "", "Please upload a session file to load."
        with open(file.name, "r") as f:
            session_data = json.load(f)
        state.last_spins = session_data.get("spins", [])
        state.scores = session_data.get("scores", {n: 0 for n in range(37)})
        state.even_money_scores = session_data.get("even_money_scores", {name: 0 for name in EVEN_MONEY.keys()})
        state.dozen_scores = session_data.get("dozen_scores", {name: 0 for name in DOZENS.keys()})
        state.column_scores = session_data.get("column_scores", {name: 0 for name in COLUMNS.keys()})
        state.street_scores = session_data.get("street_scores", {name: 0 for name in STREETS.keys()})
        state.corner_scores = session_data.get("corner_scores", {name: 0 for name in CORNERS.keys()})
        state.six_line_scores = session_data.get("six_line_scores", {name: 0 for name in SIX_LINES.keys()})
        state.split_scores = session_data.get("split_scores", {name: 0 for name in SPLITS.keys()})
        state.side_scores = session_data.get("side_scores", {"Left Side of Zero": 0, "Right Side of Zero": 0})
        new_spins = ", ".join(state.last_spins)
        return new_spins, f"Session loaded successfully with {len(state.last_spins)} spins."
    except FileNotFoundError:
        return "", f"Error: The file '{file.name if file else 'unknown'}' was not found."
    except json.JSONDecodeError:
        return "", "Error: The session file is corrupted or not valid JSON. Please upload a valid file."
    except Exception as e:
        return "", f"Unexpected error loading session: {str(e)}. Please try again or check the file."

# Function to calculate statistical insights
def statistical_insights():
    global last_spins, scores
    if not last_spins:
        return "No spins to analyze yet—click some numbers first!"
    total_spins = len(last_spins)
    number_freq = {num: scores[num] for num in scores if scores[num] > 0}
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

# Function to create the dynamic roulette table with highlighted trending sections
def create_dynamic_table(strategy_name=None):
    print(f"create_dynamic_table called with strategy: {strategy_name}")
    table_layout = [
        ["", "3", "6", "9", "12", "15", "18", "21", "24", "27", "30", "33", "36"],
        ["0", "2", "5", "8", "11", "14", "17", "20", "23", "26", "29", "32", "35"],
        ["", "1", "4", "7", "10", "13", "16", "19", "22", "25", "28", "31", "34"]
    ]

    if not any(state.scores.values()) and not any(state.even_money_scores.values()):
        return "<p>Please analyze some spins first to see highlights on the dynamic table.</p>"

    trending_even_money = None
    second_even_money = None
    trending_dozen = None
    second_dozen = None
    trending_column = None
    second_column = None
    number_highlights = {}

    sorted_even_money = sorted(state.even_money_scores.items(), key=lambda x: x[1], reverse=True)
    sorted_dozens = sorted(state.dozen_scores.items(), key=lambda x: x[1], reverse=True)
    sorted_columns = sorted(state.column_scores.items(), key=lambda x: x[1], reverse=True)
    sorted_streets = sorted(state.street_scores.items(), key=lambda x: x[1], reverse=True)
    sorted_six_lines = sorted(state.six_line_scores.items(), key=lambda x: x[1], reverse=True)
    sorted_corners = sorted(state.corner_scores.items(), key=lambda x: x[1], reverse=True)
    sorted_splits = sorted(state.split_scores.items(), key=lambda x: x[1], reverse=True)

    # Define colors based on strategy
    if strategy_name == "Cold Bet Strategy":
        # Cold colors for Cold Bet Strategy
        top_color = "#D3D3D3"  # Light Gray (Cold Top)
        middle_color = "#DDA0DD"  # Plum (Cold Middle)
        lower_color = "#E0FFFF"  # Light Cyan (Cold Lower)
    else:
        # Hot colors for all other strategies
        top_color = "rgba(255, 255, 0, 0.5)"  # Yellow
        middle_color = "rgba(0, 255, 255, 0.5)"  # Cyan
        lower_color = "rgba(0, 255, 0, 0.5)"  # Green

    if strategy_name and strategy_name in STRATEGIES:
        strategy_info = STRATEGIES[strategy_name]
        categories = strategy_info["categories"]
        strategy_output = strategy_info["function"]()
        lines = strategy_output.split("\n")

        if strategy_name == "Top Numbers with Neighbours (Tiered)":
            straight_up_df = pd.DataFrame(list(state.scores.items()), columns=["Number", "Score"])
            straight_up_df = straight_up_df[straight_up_df["Score"] > 0].sort_values(by="Score", ascending=False)
            if not straight_up_df.empty:
                num_to_take = min(8, len(straight_up_df))
                top_numbers = set(straight_up_df["Number"].head(num_to_take).tolist())
                neighbor_numbers = set()
                # Track which numbers are neighbors to others
                neighbor_to = {}
                for num in top_numbers:
                    left, right = current_neighbors.get(num, (None, None))
                    if left is not None:
                        neighbor_numbers.add(left)
                        neighbor_to[left] = neighbor_to.get(left, set()) | {num}
                    if right is not None:
                        neighbor_numbers.add(right)
                        neighbor_to[right] = neighbor_to.get(right, set()) | {num}

                # Sort numbers by score of their "parent" number
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

                for num in top_8:
                    number_highlights[str(num)] = "rgba(255, 255, 0, 0.5)"  # Yellow
                for num in next_8:
                    number_highlights[str(num)] = "rgba(0, 255, 255, 0.5)"  # Blue
                for num in last_8:
                    number_highlights[str(num)] = "rgba(0, 255, 0, 0.5)"  # Green

        elif strategy_name == "Hot Bet Strategy":
            trending_even_money = sorted_even_money[0][0] if sorted_even_money else None
            second_even_money = sorted_even_money[1][0] if len(sorted_even_money) > 1 else None
            trending_dozen = sorted_dozens[0][0] if sorted_dozens else None
            second_dozen = sorted_dozens[1][0] if len(sorted_dozens) > 1 else None
            trending_column = sorted_columns[0][0] if sorted_columns else None
            second_column = sorted_columns[1][0] if len(sorted_columns) > 1 else None
            top_streets = sorted_streets[:9]
            for i, (street_name, _) in enumerate(top_streets):
                numbers = STREETS[street_name]
                color = "rgba(255, 255, 0, 0.5)" if i < 3 else ("rgba(0, 255, 255, 0.5)" if 3 <= i < 6 else "rgba(0, 255, 0, 0.5)")
                for num in numbers:
                    number_highlights[str(num)] = color
            top_corners = sorted_corners[:9]
            for i, (corner_name, _) in enumerate(top_corners):
                numbers = CORNERS[corner_name]
                color = "rgba(255, 255, 0, 0.5)" if i < 3 else ("rgba(0, 255, 255, 0.5)" if 3 <= i < 6 else "rgba(0, 255, 0, 0.5)")
                for num in numbers:
                    number_highlights[str(num)] = color
            top_splits = sorted_splits[:9]
            for i, (split_name, _) in enumerate(top_splits):
                numbers = SPLITS[split_name]
                color = "rgba(255, 255, 0, 0.5)" if i < 3 else ("rgba(0, 255, 255, 0.5)" if 3 <= i < 6 else "rgba(0, 255, 0, 0.5)")
                for num in numbers:
                    number_highlights[str(num)] = color

        elif strategy_name == "Cold Bet Strategy":
            sorted_even_money_cold = sorted(state.even_money_scores.items(), key=lambda x: x[1])
            sorted_dozens_cold = sorted(state.dozen_scores.items(), key=lambda x: x[1])
            sorted_columns_cold = sorted(state.column_scores.items(), key=lambda x: x[1])
            sorted_streets_cold = sorted(state.street_scores.items(), key=lambda x: x[1])
            sorted_corners_cold = sorted(state.corner_scores.items(), key=lambda x: x[1])
            sorted_splits_cold = sorted(state.split_scores.items(), key=lambda x: x[1])
            trending_even_money = sorted_even_money_cold[0][0] if sorted_even_money_cold else None
            second_even_money = sorted_even_money_cold[1][0] if len(sorted_even_money_cold) > 1 else None
            trending_dozen = sorted_dozens_cold[0][0] if sorted_dozens_cold else None
            second_dozen = sorted_dozens_cold[1][0] if len(sorted_dozens_cold) > 1 else None
            trending_column = sorted_columns_cold[0][0] if sorted_columns_cold else None
            second_column = sorted_columns_cold[1][0] if len(sorted_columns_cold) > 1 else None
            top_streets = sorted_streets_cold[:9]
            for i, (street_name, _) in enumerate(top_streets):
                numbers = STREETS[street_name]
                color = "#D3D3D3" if i < 3 else ("#DDA0DD" if 3 <= i < 6 else "#E0FFFF")
                for num in numbers:
                    number_highlights[str(num)] = color
            top_corners = sorted_corners_cold[:9]
            for i, (corner_name, _) in enumerate(top_corners):
                numbers = CORNERS[corner_name]
                color = "#D3D3D3" if i < 3 else ("#DDA0DD" if 3 <= i < 6 else "#E0FFFF")
                for num in numbers:
                    number_highlights[str(num)] = color
            top_splits = sorted_splits_cold[:9]
            for i, (split_name, _) in enumerate(top_splits):
                numbers = SPLITS[split_name]
                color = "#D3D3D3" if i < 3 else ("#DDA0DD" if 3 <= i < 6 else "#E0FFFF")
                for num in numbers:
                    number_highlights[str(num)] = color

        elif strategy_name == "Best Even Money Bets":
            trending_even_money = sorted_even_money[0][0] if sorted_even_money else None
            second_even_money = sorted_even_money[1][0] if len(sorted_even_money) > 1 else None

        elif strategy_name == "Best Dozens":
            trending_dozen = sorted_dozens[0][0] if sorted_dozens else None
            second_dozen = sorted_dozens[1][0] if len(sorted_dozens) > 1 else None

        elif strategy_name == "Best Columns":
            trending_column = sorted_columns[0][0] if sorted_columns else None
            second_column = sorted_columns[1][0] if len(sorted_columns) > 1 else None

        elif strategy_name == "Fibonacci Strategy":
            best_dozen_score = sorted_dozens[0][1] if sorted_dozens else 0
            best_column_score = sorted_columns[0][1] if sorted_columns else 0
            if best_dozen_score > best_column_score:
                trending_dozen = sorted_dozens[0][0]
            elif best_column_score > best_dozen_score:
                trending_column = sorted_columns[0][0]
            else:
                trending_dozen = sorted_dozens[0][0]
                trending_column = sorted_columns[0][0]

        elif strategy_name == "Best Streets":
            top_streets = sorted_streets[:9]
            for i, (street_name, _) in enumerate(top_streets):
                numbers = STREETS[street_name]
                color = "rgba(255, 255, 0, 0.5)" if i < 3 else ("rgba(0, 255, 255, 0.5)" if 3 <= i < 6 else "rgba(0, 255, 0, 0.5)")
                for num in numbers:
                    number_highlights[str(num)] = color

        elif strategy_name == "Best Double Streets":
            top_six_lines = sorted_six_lines[:9]
            for i, (six_line_name, _) in enumerate(top_six_lines):
                numbers = SIX_LINES[six_line_name]
                color = "rgba(255, 255, 0, 0.5)" if i < 3 else ("rgba(0, 255, 255, 0.5)" if 3 <= i < 6 else "rgba(0, 255, 0, 0.5)")
                for num in numbers:
                    number_highlights[str(num)] = color

        elif strategy_name == "Best Corners":
            top_corners = sorted_corners[:9]
            for i, (corner_name, _) in enumerate(top_corners):
                numbers = CORNERS[corner_name]
                color = "rgba(255, 255, 0, 0.5)" if i < 3 else ("rgba(0, 255, 255, 0.5)" if 3 <= i < 6 else "rgba(0, 255, 0, 0.5)")
                for num in numbers:
                    number_highlights[str(num)] = color

        elif strategy_name == "Best Splits":
            top_splits = sorted_splits[:9]
            for i, (split_name, _) in enumerate(top_splits):
                numbers = SPLITS[split_name]
                color = "rgba(255, 255, 0, 0.5)" if i < 3 else ("rgba(0, 255, 255, 0.5)" if 3 <= i < 6 else "rgba(0, 255, 0, 0.5)")
                for num in numbers:
                    number_highlights[str(num)] = color

        elif strategy_name == "Best Dozens + Best Streets":
            trending_dozen = sorted_dozens[0][0] if sorted_dozens else None
            second_dozen = sorted_dozens[1][0] if len(sorted_dozens) > 1 else None
            top_streets = sorted_streets[:9]
            for i, (street_name, _) in enumerate(top_streets):
                numbers = STREETS[street_name]
                color = "rgba(255, 255, 0, 0.5)" if i < 3 else ("rgba(0, 255, 255, 0.5)" if 3 <= i < 6 else "rgba(0, 255, 0, 0.5)")
                for num in numbers:
                    number_highlights[str(num)] = color

        elif strategy_name == "Best Columns + Best Streets":
            trending_column = sorted_columns[0][0] if sorted_columns else None
            second_column = sorted_columns[1][0] if len(sorted_columns) > 1 else None
            top_streets = sorted_streets[:9]
            for i, (street_name, _) in enumerate(top_streets):
                numbers = STREETS[street_name]
                color = "rgba(255, 255, 0, 0.5)" if i < 3 else ("rgba(0, 255, 255, 0.5)" if 3 <= i < 6 else "rgba(0, 255, 0, 0.5)")
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
            best_set_streets = best_set[2]
            sorted_best_set = sorted(best_set_streets, key=lambda name: state.six_line_scores.get(name, 0), reverse=True)[:9]
            for i, double_street_name in enumerate(sorted_best_set):
                numbers = SIX_LINES[double_street_name]
                color = "rgba(255, 255, 0, 0.5)" if i < 3 else ("rgba(0, 255, 255, 0.5)" if 3 <= i < 6 else "rgba(0, 255, 0, 0.5)")
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
                color = "rgba(255, 255, 0, 0.5)" if i < 3 else ("rgba(0, 255, 255, 0.5)" if 3 <= i < 6 else "rgba(0, 255, 0, 0.5)")
                for num in numbers:
                    number_highlights[str(num)] = color

        elif strategy_name == "Romanowksy Missing Dozen":
            trending_dozen = sorted_dozens[0][0] if sorted_dozens and sorted_dozens[0][1] > 0 else None
            second_dozen = sorted_dozens[1][0] if len(sorted_dozens) > 1 and sorted_dozens[1][1] > 0 else None
            weakest_dozen = min(state.dozen_scores.items(), key=lambda x: x[1], default=("1st Dozen", 0))[0]
            straight_up_df = pd.DataFrame(list(state.scores.items()), columns=["Number", "Score"])
            straight_up_df = straight_up_df[straight_up_df["Score"] > 0].sort_values(by="Score", ascending=False)
            weak_numbers = [row["Number"] for _, row in straight_up_df.iterrows() if row["Number"] in DOZENS[weakest_dozen]][:8]
            for num in weak_numbers:
                number_highlights[str(num)] = "rgba(255, 255, 0, 0.5)"

        elif strategy_name == "Fibonacci To Fortune":
            best_dozen_score = sorted_dozens[0][1] if sorted_dozens else 0
            best_column_score = sorted_columns[0][1] if sorted_columns else 0
            if best_dozen_score > best_column_score:
                trending_dozen = sorted_dozens[0][0]
            elif best_column_score > best_dozen_score:
                trending_column = sorted_columns[0][0]
            else:
                trending_dozen = sorted_dozens[0][0]
                trending_column = sorted_columns[0][0]
            trending_even_money = sorted_even_money[0][0] if sorted_even_money else None
            second_dozen = sorted_dozens[1][0] if len(sorted_dozens) > 1 else None
            weakest_dozen = min(state.dozen_scores.items(), key=lambda x: x[1], default=("1st Dozen", 0))[0]
            double_streets_in_weakest = [(name, state.six_line_scores.get(name, 0)) for name, numbers in SIX_LINES.items() if set(numbers).issubset(DOZENS[weakest_dozen])]
            if double_streets_in_weakest:
                top_double_street = max(double_streets_in_weakest, key=lambda x: x[1])[0]
                for num in SIX_LINES[top_double_street]:
                    number_highlights[str(num)] = "rgba(255, 255, 0, 0.5)"

        elif strategy_name == "3-8-6 Rising Martingale":
            top_streets = sorted_streets[:8]
            for i, (street_name, _) in enumerate(top_streets):
                numbers = STREETS[street_name]
                if i < 3:  # Top 3 streets (1st to 3rd)
                    color = "rgba(255, 255, 0, 0.5)"  # Yellow
                elif i < 6:  # Middle 3 streets (4th to 6th)
                    color = "rgba(0, 255, 255, 0.5)"  # Cyan
                else:  # Bottom 2 streets (7th to 8th)
                    color = "rgba(0, 255, 0, 0.5)"  # Green
                for num in numbers:
                    number_highlights[str(num)] = color
            trending_even_money = sorted_even_money[0][0] if sorted_even_money else None
            trending_dozen = sorted_dozens[0][0] if sorted_dozens else None
            second_dozen = sorted_dozens[1][0] if len(sorted_dozens) > 1 else None

        elif strategy_name == "1 Dozen +1 Column Strategy":
            trending_dozen = sorted_dozens[0][0] if sorted_dozens and sorted_dozens[0][1] > 0 else None
            trending_column = sorted_columns[0][0] if sorted_columns and sorted_columns[0][1] > 0 else None

        elif strategy_name == "Top Pick 18 Numbers without Neighbours":
            straight_up_df = pd.DataFrame(list(state.scores.items()), columns=["Number", "Score"])
            straight_up_df = straight_up_df[straight_up_df["Score"] > 0].sort_values(by="Score", ascending=False)
            if len(straight_up_df) >= 18:
                top_18_df = straight_up_df.head(18)
                top_18_numbers = top_18_df["Number"].tolist()
                top_6 = top_18_numbers[:6]
                next_6 = top_18_numbers[6:12]
                last_6 = top_18_numbers[12:18]
                for num in top_6:
                    number_highlights[str(num)] = "rgba(255, 255, 0, 0.5)"
                for num in next_6:
                    number_highlights[str(num)] = "rgba(0, 255, 255, 0.5)"
                for num in last_6:
                    number_highlights[str(num)] = "rgba(0, 255, 0, 0.5)"

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
                border_style = "2px solid black"
                if strategy_name == "Top Numbers with Neighbours (Tiered)":
                    num_int = int(num)
                    straight_up_df = pd.DataFrame(list(state.scores.items()), columns=["Number", "Score"])
                    straight_up_df = straight_up_df[straight_up_df["Score"] > 0].sort_values(by="Score", ascending=False)
                    num_to_take = min(8, len(straight_up_df))
                    top_numbers = set(straight_up_df["Number"].head(num_to_take).tolist())
                    neighbor_numbers = set()
                    neighbor_to = {}
                    for n in top_numbers:
                        left, right = current_neighbors.get(n, (None, None))
                        if left is not None:
                            neighbor_numbers.add(left)
                            neighbor_to[left] = neighbor_to.get(left, set()) | {n}
                        if right is not None:
                            neighbor_numbers.add(right)
                            neighbor_to[right] = neighbor_to.get(right, set()) | {n}
                    if num_int in neighbor_numbers:
                        border_style = "4px solid green"
                        if num_int not in top_numbers:
                            highlight_color = colors.get(num, "black")
                html += f'<td style="height: 40px; background-color: {highlight_color}; color: white; border: {border_style}; padding: 0; vertical-align: middle; box-sizing: border-box; text-align: center;">{num}</td>'
        if row_idx == 0:
            bg_color = top_color if trending_column == "3rd Column" else (middle_color if second_column == "3rd Column" else "white")
            html += f'<td style="background-color: {bg_color}; border-color: black; padding: 0; font-size: 10px; vertical-align: middle; box-sizing: border-box; height: 40px; text-align: center;">3rd Column</td>'
        elif row_idx == 1:
            bg_color = top_color if trending_column == "2nd Column" else (middle_color if second_column == "2nd Column" else "white")
            html += f'<td style="background-color: {bg_color}; border-color: black; padding: 0; font-size: 10px; vertical-align: middle; box-sizing: border-box; height: 40px; text-align: center;">2nd Column</td>'
        elif row_idx == 2:
            bg_color = top_color if trending_column == "1st Column" else (middle_color if second_column == "1st Column" else "white")
            html += f'<td style="background-color: {bg_color}; border-color: black; padding: 0; font-size: 10px; vertical-align: middle; box-sizing: border-box; height: 40px; text-align: center;">1st Column</td>'
        html += "</tr>"

    html += "<tr>"
    html += '<td style="height: 40px; border-color: black; box-sizing: border-box;"></td>'
    bg_color = top_color if trending_even_money == "Low" else (middle_color if second_even_money == "Low" else "white")
    html += f'<td colspan="6" style="background-color: {bg_color}; color: black; border-color: black; padding: 0; font-size: 10px; vertical-align: middle; box-sizing: border-box; height: 40px; text-align: center;">Low (1 to 18)</td>'
    bg_color = top_color if trending_even_money == "High" else (middle_color if second_even_money == "High" else "white")
    html += f'<td colspan="6" style="background-color: {bg_color}; color: black; border-color: black; padding: 0; font-size: 10px; vertical-align: middle; box-sizing: border-box; height: 40px; text-align: center;">High (19 to 36)</td>'
    html += '<td style="border-color: black; box-sizing: border-box;"></td>'
    html += "</tr>"

    html += "<tr>"
    html += '<td style="height: 40px; border-color: black; box-sizing: border-box;"></td>'
    bg_color = top_color if trending_dozen == "1st Dozen" else (middle_color if second_dozen == "1st Dozen" else "white")
    html += f'<td colspan="4" style="background-color: {bg_color}; color: black; border-color: black; padding: 0; font-size: 10px; vertical-align: middle; box-sizing: border-box; height: 40px; text-align: center;">1st Dozen</td>'
    bg_color = top_color if trending_dozen == "2nd Dozen" else (middle_color if second_dozen == "2nd Dozen" else "white")
    html += f'<td colspan="4" style="background-color: {bg_color}; color: black; border-color: black; padding: 0; font-size: 10px; vertical-align: middle; box-sizing: border-box; height: 40px; text-align: center;">2nd Dozen</td>'
    bg_color = top_color if trending_dozen == "3rd Dozen" else (middle_color if second_dozen == "3rd Dozen" else "white")
    html += f'<td colspan="4" style="background-color: {bg_color}; color: black; border-color: black; padding: 0; font-size: 10px; vertical-align: middle; box-sizing: border-box; height: 40px; text-align: center;">3rd Dozen</td>'
    html += '<td style="border-color: black; box-sizing: border-box;"></td>'
    html += "</tr>"

    html += "<tr>"
    html += '<td style="height: 40px; border-color: black; box-sizing: border-box;"></td>'
    bg_color = top_color if trending_even_money == "Odd" else (middle_color if second_even_money == "Odd" else "white")
    html += f'<td colspan="4" style="border-color: black; box-sizing: border-box;"></td>'
    html += f'<td style="background-color: {bg_color}; color: black; border-color: black; padding: 0; font-size: 10px; vertical-align: middle; box-sizing: border-box; height: 40px; text-align: center;">ODD</td>'
    bg_color = top_color if trending_even_money == "Red" else (middle_color if second_even_money == "Red" else "white")
    html += f'<td style="background-color: {bg_color}; color: black; border-color: black; padding: 0; font-size: 10px; vertical-align: middle; box-sizing: border-box; height: 40px; text-align: center;">RED</td>'
    bg_color = top_color if trending_even_money == "Black" else (middle_color if second_even_money == "Black" else "white")
    html += f'<td style="background-color: {bg_color}; color: black; border-color: black; padding: 0; font-size: 10px; vertical-align: middle; box-sizing: border-box; height: 40px; text-align: center;">BLACK</td>'
    bg_color = top_color if trending_even_money == "Even" else (middle_color if second_even_money == "Even" else "white")
    html += f'<td style="background-color: {bg_color}; color: black; border-color: black; padding: 0; font-size: 10px; vertical-align: middle; box-sizing: border-box; height: 40px; text-align: center;">EVEN</td>'
    html += f'<td colspan="4" style="border-color: black; box-sizing: border-box;"></td>'
    html += '<td style="border-color: black; box-sizing: border-box;"></td>'
    html += "</tr>"

    html += "</table>"
    return html

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

# Function to analyze spins
# Continuing from analyze_spins function
def analyze_spins(spins_input, reset_scores, strategy_name, *checkbox_args):
    try:
        if not spins_input or not spins_input.strip():
            return "Please enter at least one number (e.g., 5, 12, 0).", "", "", "", "", "", "", "", "", "", "", "", "", ""

        raw_spins = [spin.strip() for spin in spins_input.split(",") if spin.strip()]
        spins = []

        for spin in raw_spins:
            try:
                num = int(spin)
                if not (0 <= num <= 36):
                    return f"Error: '{spin}' is out of range. Use numbers between 0 and 36.", "", "", "", "", "", "", "", "", "", "", "", "", ""
                spins.append(str(num))
            except ValueError:
                return f"Error: '{spin}' is not a valid number. Use whole numbers (e.g., 5, 12, 0).", "", "", "", "", "", "", "", "", "", "", "", "", ""

        if not spins:
            return "No valid numbers found. Please enter numbers like '5, 12, 0'.", "", "", "", "", "", "", "", "", "", "", "", "", ""

        if reset_scores:
            state.reset()

        state.last_spins.extend(spins)
        spin_results = []
        for spin in spins:
            hit_sections = []
            spin_value = int(spin)

            for name, numbers in EVEN_MONEY.items():
                if int(spin) in numbers:
                    hit_sections.append(name)
                    state.even_money_scores[name] += 1

            for name, numbers in DOZENS.items():
                if int(spin) in numbers:
                    hit_sections.append(name)
                    state.dozen_scores[name] += 1

            for name, numbers in COLUMNS.items():
                if int(spin) in numbers:
                    hit_sections.append(name)
                    state.column_scores[name] += 1

            for name, numbers in STREETS.items():
                if int(spin) in numbers:
                    hit_sections.append(name)
                    state.street_scores[name] += 1

            for name, numbers in CORNERS.items():
                if int(spin) in numbers:
                    hit_sections.append(name)
                    state.corner_scores[name] += 1

            for name, numbers in SIX_LINES.items():
                if int(spin) in numbers:
                    hit_sections.append(name)
                    state.six_line_scores[name] += 1

            for name, numbers in SPLITS.items():
                if int(spin) in numbers:
                    hit_sections.append(name)
                    state.split_scores[name] += 1

            if spin != "0":
                state.scores[int(spin)] += 1
                hit_sections.append(f"Straight Up {spin}")
            elif spin == "0":
                state.scores[0] += 1
                hit_sections.append(f"Straight Up {spin}")

            if str(spin) in [str(x) for x in current_left_of_zero]:
                hit_sections.append("Left Side of Zero")
                state.side_scores["Left Side of Zero"] += 1
            if str(spin) in [str(x) for x in current_right_of_zero]:
                hit_sections.append("Right Side of Zero")
                state.side_scores["Right Side of Zero"] += 1

            if int(spin) in current_neighbors:
                left, right = current_neighbors[int(spin)]
                hit_sections.append(f"Left Neighbor: {left}")
                hit_sections.append(f"Right Neighbor: {right}")

            spin_results.append(f"Spin {spin} hits: {', '.join(hit_sections)}\nTotal sections hit: {len(hit_sections)}")

        spin_analysis_output = "\n".join(spin_results)
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
        dynamic_table_html = create_dynamic_table(strategy_name)

        strategy_output = show_strategy_recommendations(strategy_name, *checkbox_args)
        print(f"analyze_spins: Strategy output = {strategy_output}")

        return (spin_analysis_output, even_money_output, dozens_output, columns_output,
                streets_output, corners_output, six_lines_output, splits_output, sides_output,
                straight_up_html, top_18_html, strongest_numbers_output, dynamic_table_html, strategy_output)
    except Exception as e:
        return f"Unexpected error while analyzing spins: {str(e)}. Please try again.", "", "", "", "", "", "", "", "", "", "", "", "", ""

# Function to reset scores
def reset_scores():
    state.reset()
    return "Scores reset!"

def undo_last_spin(current_spins_display, strategy_name, *checkbox_args):
    if not state.last_spins:
        return ("No spins to undo.", "", "", "", "", "", "", "", "", "", "", "", current_spins_display, current_spins_display, "", "", create_color_code_table())

    last_spin = state.last_spins.pop()
    spin_value = int(last_spin)

    if spin_value in state.scores:
        state.scores[spin_value] -= 1

    for name, numbers in EVEN_MONEY.items():
        if spin_value in numbers:
            state.even_money_scores[name] -= 1

    for name, numbers in DOZENS.items():
        if spin_value in numbers:
            state.dozen_scores[name] -= 1

    for name, numbers in COLUMNS.items():
        if spin_value in numbers:
            state.column_scores[name] -= 1

    for name, numbers in STREETS.items():
        if spin_value in numbers:
            state.street_scores[name] -= 1

    for name, numbers in CORNERS.items():
        if spin_value in numbers:
            state.corner_scores[name] -= 1

    for name, numbers in SIX_LINES.items():
        if spin_value in numbers:
            state.six_line_scores[name] -= 1

    for name, numbers in SPLITS.items():
        if spin_value in numbers:
            state.split_scores[name] -= 1

    if str(spin_value) in [str(x) for x in current_left_of_zero]:
        state.side_scores["Left Side of Zero"] -= 1
    if str(spin_value) in [str(x) for x in current_right_of_zero]:
        state.side_scores["Right Side of Zero"] -= 1

    spins_input = ", ".join(state.last_spins) if state.last_spins else ""

    spin_analysis_output = f"Undo successful: Removed spin {last_spin}"
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
    dynamic_table_html = create_dynamic_table(strategy_name)

    print(f"undo_last_spin: Generating strategy recommendations for {strategy_name}")
    strategy_output = show_strategy_recommendations(strategy_name, *checkbox_args)

    return (spin_analysis_output, even_money_output, dozens_output, columns_output,
            streets_output, corners_output, six_lines_output, splits_output, sides_output,
            straight_up_html, top_18_html, strongest_numbers_output, spins_input, spins_input,
            dynamic_table_html, strategy_output, create_color_code_table())

def clear_all():
    # Clear spins
    state.selected_numbers.clear()
    state.last_spins = []
    # Reset scores
    state.reset()
    # Clear all outputs
    return "", "", "All spins and scores cleared successfully!", "", "", "", "", "", "", "", "", "", "", "", ""

def reset_strategy_dropdowns():
    default_category = "Even Money Strategies"
    default_strategy = "Best Even Money Bets"
    strategy_choices = strategy_categories[default_category]
    return default_category, default_strategy, strategy_choices

def generate_random_spins(num_spins, current_spins_display, num_to_show):
    num_spins = int(num_spins)
    if num_spins <= 0:
        return current_spins_display, current_spins_display, "Please enter a positive number of spins to generate."

    new_spins = [str(random.randint(0, 36)) for _ in range(num_spins)]
    if current_spins_display:
        updated_spins = current_spins_display + ", " + ", ".join(new_spins)
    else:
        updated_spins = ", ".join(new_spins)
    return updated_spins, updated_spins, f"Generated {num_spins} random spins: {', '.join(new_spins)}"

# Strategy functions
def best_even_money_bets():
    recommendations = []
    sorted_even_money = sorted(state.even_money_scores.items(), key=lambda x: x[1], reverse=True)
    even_money_hits = [item for item in sorted_even_money if item[1] > 0]
    if even_money_hits:
        recommendations.append("Best Even Money Bets (Top 2):")
        for i, (name, score) in enumerate(even_money_hits[:2], 1):
            recommendations.append(f"{i}. {name}: {score}")
    else:
        recommendations.append("Best Even Money Bets: No hits yet.")
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

def cold_bet_strategy():
    recommendations = []
    sorted_even_money = sorted(even_money_scores.items(), key=lambda x: x[1])
    even_money_non_hits = [item for item in sorted_even_money if item[1] == 0]
    even_money_hits = [item for item in sorted_even_money if item[1] > 0]
    if even_money_non_hits:
        recommendations.append("Even Money (Not Hit):")
        recommendations.append(", ".join(item[0] for item in even_money_non_hits))
    if even_money_hits:
        recommendations.append("\nEven Money (Lowest Scores):")
        for i, (name, score) in enumerate(even_money_hits[:2], 1):
            recommendations.append(f"{i}. {name}: {score}")

    sorted_dozens = sorted(dozen_scores.items(), key=lambda x: x[1])
    dozens_non_hits = [item for item in sorted_dozens if item[1] == 0]
    dozens_hits = [item for item in sorted_dozens if item[1] > 0]
    if dozens_non_hits:
        recommendations.append("\nDozens (Not Hit):")
        recommendations.append(", ".join(item[0] for item in dozens_non_hits))
    if dozens_hits:
        recommendations.append("\nDozens (Lowest Scores):")
        for i, (name, score) in enumerate(dozens_hits[:2], 1):
            recommendations.append(f"{i}. {name}: {score}")

    sorted_columns = sorted(column_scores.items(), key=lambda x: x[1])
    columns_non_hits = [item for item in sorted_columns if item[1] == 0]
    columns_hits = [item for item in sorted_columns if item[1] > 0]
    if columns_non_hits:
        recommendations.append("\nColumns (Not Hit):")
        recommendations.append(", ".join(item[0] for item in columns_non_hits))
    if columns_hits:
        recommendations.append("\nColumns (Lowest Scores):")
        for i, (name, score) in enumerate(columns_hits[:2], 1):
            recommendations.append(f"{i}. {name}: {score}")

    sorted_streets = sorted(street_scores.items(), key=lambda x: x[1])
    streets_non_hits = [item for item in sorted_streets if item[1] == 0]
    streets_hits = [item for item in sorted_streets if item[1] > 0]
    if streets_non_hits:
        recommendations.append("\nStreets (Not Hit):")
        recommendations.append(", ".join(item[0] for item in streets_non_hits))
    if streets_hits:
        recommendations.append("\nStreets (Lowest Scores):")
        for i, (name, score) in enumerate(streets_hits[:3], 1):
            recommendations.append(f"{i}. {name}: {score}")

    sorted_corners = sorted(corner_scores.items(), key=lambda x: x[1])
    corners_non_hits = [item for item in sorted_corners if item[1] == 0]
    corners_hits = [item for item in sorted_corners if item[1] > 0]
    if corners_non_hits:
        recommendations.append("\nCorners (Not Hit):")
        recommendations.append(", ".join(item[0] for item in corners_non_hits))
    if corners_hits:
        recommendations.append("\nCorners (Lowest Scores):")
        for i, (name, score) in enumerate(corners_hits[:3], 1):
            recommendations.append(f"{i}. {name}: {score}")

    sorted_six_lines = sorted(six_line_scores.items(), key=lambda x: x[1])
    six_lines_non_hits = [item for item in sorted_six_lines if item[1] == 0]
    six_lines_hits = [item for item in sorted_six_lines if item[1] > 0]
    if six_lines_non_hits:
        recommendations.append("\nDouble Streets (Not Hit):")
        recommendations.append(", ".join(item[0] for item in six_lines_non_hits))
    if six_lines_hits:
        recommendations.append("\nDouble Streets (Lowest Scores):")
        for i, (name, score) in enumerate(six_lines_hits[:3], 1):
            recommendations.append(f"{i}. {name}: {score}")

    sorted_splits = sorted(split_scores.items(), key=lambda x: x[1])
    splits_non_hits = [item for item in sorted_splits if item[1] == 0]
    splits_hits = [item for item in sorted_splits if item[1] > 0]
    if splits_non_hits:
        recommendations.append("\nSplits (Not Hit):")
        recommendations.append(", ".join(item[0] for item in splits_non_hits))
    if splits_hits:
        recommendations.append("\nSplits (Lowest Scores):")
        for i, (name, score) in enumerate(splits_hits[:3], 1):
            recommendations.append(f"{i}. {name}: {score}")

    sorted_sides = sorted(side_scores.items(), key=lambda x: x[1])
    sides_non_hits = [item for item in sorted_sides if item[1] == 0]
    sides_hits = [item for item in sorted_sides if item[1] > 0]
    if sides_non_hits:
        recommendations.append("\nSides of Zero (Not Hit):")
        recommendations.append(", ".join(item[0] for item in sides_non_hits))
    if sides_hits:
        recommendations.append("\nSides of Zero (Lowest Score):")
        recommendations.append(f"1. {sides_hits[0][0]}: {sides_hits[0][1]}")

    sorted_numbers = sorted(scores.items(), key=lambda x: x[1])
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

def kitchen_martingale_output(*checkboxes):
    sorted_even_money = sorted(state.even_money_scores.items(), key=lambda x: x[1], reverse=True)
    even_money_hits = [item for item in sorted_even_money if item[1] > 0]

    recommendations = []
    if even_money_hits:
        best_bet = even_money_hits[0][0]
        recommendations.append(f"Best Even Money Bet: {best_bet}")
    else:
        recommendations.append("Best Even Money Bet: No hits yet.")

    betting_progression_km = [
        ("(Bankroll: $1.00)", "1ST BET", "$1.00"),
        ("(Bankroll: $3.00)", "2ND BET", "$2.00"),
        ("(Bankroll: $6.00)", "3RD BET", "$3.00"),
        ("(Bankroll: $9.00)", "4TH BET", "$3.00"),
        ("(Bankroll: $12.00)", "5TH BET", "$3.00"),
        ("(Bankroll: $16.00)", "6TH BET", "$4.00"),
        ("(Bankroll: $20.00)", "7TH BET", "$4.00"),
        ("(Bankroll: $25.00)", "8TH BET", "$5.00"),
        ("(Bankroll: $30.00)", "9TH BET", "$5.00"),
        ("(Bankroll: $36.00)", "10TH BET", "$6.00"),
        ("(Bankroll: $42.00)", "11TH BET", "$6.00"),
        ("(Bankroll: $49.00)", "12TH BET", "$7.00"),
        ("(Bankroll: $56.00)", "13TH BET", "$7.00"),
        ("(Bankroll: $64.00)", "14TH BET", "$8.00"),
        ("(Bankroll: $72.00)", "15TH BET", "$8.00"),
        ("(Bankroll: $81.00)", "16TH BET", "$9.00"),
        ("(Bankroll: $90.00)", "17TH BET", "$9.00"),
        ("(Bankroll: $100.00)", "18TH BET", "$10.00"),
        ("(Bankroll: $110.00)", "19TH BET", "$10.00")
    ]

    checkbox_counts = [0, 1, 1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2]
    total_checkboxes = sum(checkbox_counts)
    assert total_checkboxes == 34, f"Expected 34 checkboxes, got {total_checkboxes}"

    flat_progression = []
    for (bankroll, bet_label, bet_amount), count in zip(betting_progression_km, checkbox_counts):
        for _ in range(count):
            flat_progression.append((bankroll, bet_label, bet_amount))

    recommendations.append("\nBetting Progression (Check to track losses):")
    for i, (bankroll, bet_label, bet_amount) in enumerate(flat_progression, 1):
        checked = checkboxes[i-1]
        checkmark = "☑" if checked else "☐"
        line = f"{i}. {bankroll}\t{bet_label}\t{bet_amount}\t{checkmark}"
        recommendations.append(line)

    return "\n".join(recommendations)

def victory_vortex_strategy(*checkboxes):
    recommendations = []
    fib_recommendations = fibonacci_strategy()
    recommendations.append("Fibonacci Strategy:")
    recommendations.append(fib_recommendations)

    dozens_sorted = sorted(state.dozen_scores.items(), key=lambda x: x[1], reverse=True)
    dozens_hits = [item for item in dozens_sorted if item[1] > 0]
    if dozens_hits:
        recommendations.append("\nBest Two Dozens:")
        for i, (name, score) in enumerate(dozens_hits[:2], 1):
            recommendations.append(f"{i}. {name}: {score}")
    else:
        recommendations.append("\nBest Two Dozens: No hits yet.")

    columns_sorted = sorted(state.column_scores.items(), key=lambda x: x[1], reverse=True)
    columns_hits = [item for item in columns_sorted if item[1] > 0]
    if columns_hits:
        recommendations.append("\nBest Two Columns:")
        for i, (name, score) in enumerate(columns_hits[:2], 1):
            recommendations.append(f"{i}. {name}: {score}")
    else:
        recommendations.append("\nBest Two Columns: No hits yet.")

    recommendations.append("\nBetting Progression (Check to track losses):")
    for i, (bankroll, bet_label, bet_amount) in enumerate(betting_progression_vv, 1):
        checked = checkboxes[i-1]
        checkmark = "☑" if checked else "☐"
        line = f"{i}. {bankroll}\t{bet_label}\t{bet_amount}\t{checkmark}"
        recommendations.append(line)

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
                    <td style="padding: 8px;">Indicates the hottest or top-ranked numbers/sections (e.g., top 3 or top 6 in most strategies).</td>
                </tr>
                <tr>
                    <td style="padding: 8px; background-color: rgba(0, 255, 255, 0.5); text-align: center;">Cyan (Middle Tier)</td>
                    <td style="padding: 8px;">Represents the second tier of trending numbers/sections (e.g., ranks 4-6 or secondary picks).</td>
                </tr>
                <tr>
                    <td style="padding: 8px; background-color: rgba(0, 255, 0, 0.5); text-align: center;">Green (Lower Tier)</td>
                    <td style="padding: 8px;">Marks the third tier of strong numbers/sections (e.g., ranks 7-9 or lower priority).</td>
                </tr>
                <tr>
                    <td style="padding: 8px; background-color: #D3D3D3; text-align: center;">Light Gray (Cold Top)</td>
                    <td style="padding: 8px;">Used in Cold Bet Strategy for the coldest top-tier sections (least hits).</td>
                </tr>
                <tr>
                    <td style="padding: 8px; background-color: #DDA0DD; text-align: center;">Plum (Cold Middle)</td>
                    <td style="padding: 8px;">Used in Cold Bet Strategy for middle-tier cold sections.</td>
                </tr>
                <tr>
                    <td style="padding: 8px; background-color: #E0FFFF; text-align: center;">Light Cyan (Cold Lower)</td>
                    <td style="padding: 8px;">Used in Cold Bet Strategy for lower-tier cold sections.</td>
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
            </tbody>
        </table>
    </div>
    '''
    return html

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

STRATEGIES = {
    "Hot Bet Strategy": {"function": hot_bet_strategy, "categories": ["even_money", "dozens", "columns", "streets", "corners", "six_lines", "splits", "sides", "numbers"]},
    "Cold Bet Strategy": {"function": cold_bet_strategy, "categories": ["even_money", "dozens", "columns", "streets", "corners", "six_lines", "splits", "sides", "numbers"]},
    "Best Even Money Bets": {"function": best_even_money_bets, "categories": ["even_money"]},
    "Best Dozens": {"function": best_dozens, "categories": ["dozens"]},
    "Best Columns": {"function": best_columns, "categories": ["columns"]},
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
    "Top Numbers with Neighbours (Tiered)": {"function": top_numbers_with_neighbours_tiered, "categories": ["numbers"]}
}

def show_strategy_recommendations(strategy_name, *args):
    print(f"show_strategy_recommendations: scores = {dict(state.scores)}")
    print(f"show_strategy_recommendations: even_money_scores = {dict(state.even_money_scores)}")
    print(f"show_strategy_recommendations: any_scores = {any(state.scores.values())}, any_even_money = {any(state.even_money_scores.values())}")
    
    if not any(state.scores.values()) and not any(state.even_money_scores.values()):
        return "<p>Please analyze some spins first to generate scores.</p>"

    strategy_info = STRATEGIES[strategy_name]
    strategy_func = strategy_info["function"]

    if strategy_name == "Kitchen Martingale":
        recommendations = strategy_func(*args[:34])
    elif strategy_name == "S.T.Y.W: Victory Vortex":
        recommendations = strategy_func(*args[34:50])
    else:
        recommendations = strategy_func()

    print(f"show_strategy_recommendations: Strategy {strategy_name} output = {recommendations}")

    # If the output is already HTML (e.g., from top_numbers_with_neighbours_tiered), return it as is
    if strategy_name == "Top Numbers with Neighbours (Tiered)":
        return recommendations
    # Otherwise, convert plain text to HTML by replacing newlines with <br> tags
    else:
        # Split the plain text by newlines and wrap each line in a <p> tag
        lines = recommendations.split("\n")
        html_lines = [f"<p>{line}</p>" for line in lines if line.strip()]
        return "".join(html_lines)

def clear_outputs():
    return "", "", "", "", "", "", "", "", "", "", "", False, False, False, False, False, False, False, False

def toggle_checkboxes(strategy_name):
    return (gr.update(visible=strategy_name == "Kitchen Martingale"),
            gr.update(visible=strategy_name == "S.T.Y.W: Victory Vortex"))

# Build the Gradio interface
with gr.Blocks() as demo:
    gr.Markdown("# Roulette Spin Analyzer with Strategies (European Table)")
    
    # Add a link to the PDF using the corrected absolute URL
    gr.HTML(
        '<a href="https://drive.google.com/file/d/1o9H8Lakx1i4_OnDrvHRj_6-KHsOWufjF/view?usp=sharing" target="_blank" style="font-size: 16px; color: #007bff; text-decoration: underline;">📄 View Instructions1 PDF (Opens in Google Drive)</a>'
    )

    spins_display = gr.State(value="")
    spins_textbox = gr.Textbox(
        label="Selected Spins (Edit manually with commas, e.g., 5, 12, 0)",
        value="",
        interactive=True,
        elem_id="selected-spins"
    )
    with gr.Row():
        last_spin_display = gr.HTML(
            label="Last Spin",
            value=""
        )
        last_spin_count = gr.Slider(
            label="Show Last Spins",
            minimum=1,
            maximum=36,
            step=1,
            value=5,
            interactive=True
        )
    with gr.Accordion("Spin Analysis", open=False, elem_id="spin-analysis"):
        spin_analysis_output = gr.Textbox(
            label="",
            value="",
            interactive=False,
            lines=5
        )

    with gr.Group():
        gr.Markdown("### European Roulette Table")
        table_layout = [
            ["", "3", "6", "9", "12", "15", "18", "21", "24", "27", "30", "33", "36"],
            ["0", "2", "5", "8", "11", "14", "17", "20", "23", "26", "29", "32", "35"],
            ["", "1", "4", "7", "10", "13", "16", "19", "22", "25", "28", "31", "34"]
        ]

    # Create the table with elem_classes
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
                            outputs=[spins_display, spins_textbox, last_spin_display]
                        )

    # New accordion for Strongest Numbers tables, placed here
    with gr.Accordion("Strongest Numbers Tables", open=False, elem_id="strongest-numbers-table"):
        with gr.Row():
            with gr.Column():
                straight_up_table = gr.HTML(label="Strongest Numbers", elem_classes="scrollable-table")
            with gr.Column():
                top_18_table = gr.HTML(label="Top 18 Strongest Numbers (Sorted Lowest to Highest)", elem_classes="scrollable-table")
        with gr.Row():
            strongest_numbers_dropdown = gr.Dropdown(
                label="Select Number of Strongest Numbers",
                choices=["3", "6", "9", "12", "15", "18", "21", "24", "27", "30", "33"],
                value="3"
            )
            strongest_numbers_output = gr.Textbox(
                label="Strongest Numbers (Sorted Lowest to Highest)",
                value="",
                lines=2
            )

    with gr.Row(elem_classes="white-row"):
        num_spins_input = gr.Dropdown(
            label="Number of Random Spins",
            choices=["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"],
            value="5",
            elem_classes="num-spins-dropdown",
            elem_id="number-of-random-spins"
        )
        generate_spins_button = gr.Button("Generate Random Spins", elem_classes=["generate-spins-btn", "action-button"])
        analyze_button = gr.Button("Analyze Spins", elem_classes=["action-button", "green-btn"], interactive=True)
        undo_button = gr.Button("Undo Last Spin", elem_classes="action-button")

    strategy_categories = {
        "Trends": ["Cold Bet Strategy", "Hot Bet Strategy"],
        "Even Money Strategies": ["Best Even Money Bets", "Fibonacci To Fortune"],
        "Dozen Strategies": ["1 Dozen +1 Column Strategy", "Best Dozens", "Best Dozens + Best Streets", "Fibonacci Strategy", "Romanowksy Missing Dozen"],
        "Column Strategies": ["1 Dozen +1 Column Strategy", "Best Columns", "Best Columns + Best Streets"],
        "Street Strategies": ["3-8-6 Rising Martingale", "Best Streets", "Best Columns + Best Streets", "Best Dozens + Best Streets"],
        "Double Street Strategies": ["Best Double Streets", "Non-Overlapping Double Street Strategy"],
        "Corner Strategies": ["Best Corners", "Non-Overlapping Corner Strategy"],
        "Split Strategies": ["Best Splits"],
        "Number Strategies": ["Top Numbers with Neighbours (Tiered)", "Top Pick 18 Numbers without Neighbours"]
    }

    # Category dropdown choices
    category_choices = ["None"] + sorted(strategy_categories.keys())

    # State to store the current strategy
    selected_strategy = gr.State(value="Best Even Money Bets")

    with gr.Row():
        category_dropdown = gr.Dropdown(
            label="Select Category",
            choices=category_choices,
            value="Even Money Strategies",
            allow_custom_value=False,
            elem_id="select-category"
        )
        strategy_dropdown = gr.Dropdown(
            label="Select Strategy",
            choices=strategy_categories["Even Money Strategies"],
            value="Best Even Money Bets",
            allow_custom_value=False
        )
        reset_strategy_button = gr.Button("Reset Category & Strategy", elem_classes="action-button")

    with gr.Row(elem_classes="white-row"):
        reset_scores_checkbox = gr.Checkbox(label="Reset Scores on Analysis", value=True)
        reset_button = gr.Button("Reset Scores", elem_classes="action-button", visible=False)
        clear_button = gr.Button("Clear Outputs", elem_classes="action-button", visible=False)

    with gr.Row():
        clear_spins_button = gr.Button("Clear Spins", elem_classes="clear-spins-btn small-btn")
        clear_all_button = gr.Button("Clear All", elem_classes="clear-spins-btn small-btn")
        print("Button Class Set")

    with gr.Row():
        with gr.Column():
            gr.Markdown("### Dynamic Roulette Table")
            dynamic_table_output = gr.HTML(label="Dynamic Table")
            color_code_output = gr.HTML(label="Color Code Key")
        with gr.Column():
            gr.Markdown("### Strategy Recommendations")
            strategy_output = gr.HTML(label="Strategy Recommendations")
            with gr.Column(visible=False) as kitchen_martingale_checkboxes:
                gr.Markdown("### Kitchen Martingale Checkboxes")
                kitchen_martingale_checkboxes_list = []
                betting_progression_km = [
                    ("(Bankroll: $1.00)", "1ST BET", "$1.00"),
                    ("(Bankroll: $3.00)", "2ND BET", "$2.00"),
                    ("(Bankroll: $6.00)", "3RD BET", "$3.00"),
                    ("(Bankroll: $9.00)", "4TH BET", "$3.00"),
                    ("(Bankroll: $12.00)", "5TH BET", "$3.00"),
                    ("(Bankroll: $16.00)", "6TH BET", "$4.00"),
                    ("(Bankroll: $20.00)", "7TH BET", "$4.00"),
                    ("(Bankroll: $25.00)", "8TH BET", "$5.00"),
                    ("(Bankroll: $30.00)", "9TH BET", "$5.00"),
                    ("(Bankroll: $36.00)", "10TH BET", "$6.00"),
                    ("(Bankroll: $42.00)", "11TH BET", "$6.00"),
                    ("(Bankroll: $49.00)", "12TH BET", "$7.00"),
                    ("(Bankroll: $56.00)", "13TH BET", "$7.00"),
                    ("(Bankroll: $64.00)", "14TH BET", "$8.00"),
                    ("(Bankroll: $72.00)", "15TH BET", "$8.00"),
                    ("(Bankroll: $81.00)", "16TH BET", "$9.00"),
                    ("(Bankroll: $90.00)", "17TH BET", "$9.00"),
                    ("(Bankroll: $100.00)", "18TH BET", "$10.00"),
                    ("(Bankroll: $110.00)", "19TH BET", "$10.00")
                ]
                checkbox_counts = [0, 1, 1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2]
                flat_progression_km = []
                for (bankroll, bet_label, bet_amount), count in zip(betting_progression_km, checkbox_counts):
                    for _ in range(count):
                        flat_progression_km.append((bankroll, bet_label, bet_amount))

                for i, (bankroll, bet_label, bet_amount) in enumerate(flat_progression_km, 1):
                    checkbox = gr.Checkbox(label=f"{i}. {bankroll} {bet_label} {bet_amount}", value=False)
                    kitchen_martingale_checkboxes_list.append(checkbox)

            with gr.Column(visible=False) as victory_vortex_checkboxes:
                gr.Markdown("### Victory Vortex Checkboxes")
                victory_vortex_checkboxes_list = []
                for i, (bankroll, bet_label, bet_amount) in enumerate(betting_progression_vv, 1):
                    checkbox = gr.Checkbox(label=f"{i}. {bankroll} {bet_label} {bet_amount}", value=False)
                    victory_vortex_checkboxes_list.append(checkbox)

    gr.HTML("""
    <style>
      .roulette-button.green { background-color: green !important; color: white !important; border: 1px solid white !important; text-align: center !important; font-weight: bold !important; }
      .roulette-button.red { background-color: red !important; color: white !important; border: 1px solid white !important; text-align: center !important; font-weight: bold !important; }
      .roulette-button.black { background-color: black !important; color: white !important; border: 1px solid white !important; text-align: center !important; font-weight: bold !important; }
      .roulette-button:hover { opacity: 0.8; }
      table { border-collapse: collapse; text-align: center; }
      td, th { border: 1px solid #333; padding: 8px; font-family: Arial, sans-serif; }
      .roulette-button.selected { border: 3px solid yellow !important; opacity: 0.9; }
      .roulette-button { margin: 0 !important; padding: 0 !important; width: 40px !important; height: 40px !important; font-size: 14px !important; display: flex !important; align-items: center !important; justify-content: center !important; border: 1px solid white !important; box-sizing: border-box !important; }
      .empty-button { margin: 0 !important; padding: 0 !important; width: 40px !important; height: 40px !important; border: 1px solid white !important; box-sizing: border-box !important; }
      .roulette-table { display: flex !important; flex-direction: column !important; gap: 0 !important; margin: 0 !important; padding: 0 !important; }
      .table-row { display: flex !important; gap: 0 !important; margin: 0 !important; padding: 0 !important; flex-wrap: nowrap !important; line-height: 0 !important; }
      button.clear-spins-btn { background-color: #ff4444 !important; color: white !important; border: 1px solid #000 !important; }
      button.clear-spins-btn:hover { background-color: #cc0000 !important; }
      button.small-btn { padding: 5px 10px !important; font-size: 12px !important; min-width: 80px !important; }
      button.generate-spins-btn { background-color: #007bff !important; color: white !important; border: 1px solid #000 !important; }
      button.generate-spins-btn:hover { background-color: #0056b3 !important; }
      .num-spins-input { margin-right: 5px !important; }
      .white-row { background-color: white !important; }
      .num-spins-dropdown { width: 100px !important; margin-right: 5px !important; }
      .action-button { min-width: 120px !important; padding: 5px 10px !important; font-size: 14px !important; }
      button.green-btn { background-color: #28a745 !important; color: white !important; border: 1px solid #000 !important; }
      button.green-btn:hover { background-color: #218838 !important; }
      .scrollable-table { max-height: 300px; overflow-y: auto; display: block; width: 100%; }
      /* Style for section labels */
      #selected-spins label { background-color: #87CEEB; color: black; padding: 5px; border-radius: 3px; }
      #spin-analysis label { background-color: #90EE90 !important; color: black !important; padding: 5px; border-radius: 3px; }
      #strongest-numbers-table label { background-color: #E6E6FA !important; color: black !important; padding: 5px; border-radius: 3px; }
      #number-of-random-spins label { background-color: #FFDAB9 !important; color: black !important; padding: 5px; border-radius: 3px; }
      #aggregated-scores label { background-color: #FFB6C1 !important; color: black !important; padding: 5px; border-radius: 3px; }
      #select-category label { background-color: #FFFFE0 !important; color: black !important; padding: 5px; border-radius: 3px; }
      @media (max-width: 600px) {
          .roulette-button { min-width: 30px; font-size: 12px; padding: 5px; }
          td, th { padding: 5px; font-size: 12px; }
          .gr-textbox { font-size: 12px; }
          .scrollable-table { max-height: 200px; }
      }
    </style>
    """)
    print("CSS Updated")

    with gr.Accordion("Aggregated Scores", open=False, elem_id="aggregated-scores"):
        with gr.Row():
            with gr.Column():
                with gr.Accordion("Even Money Bets", open=True):
                    even_money_output = gr.Textbox(label="Even Money Bets", lines=10, max_lines=50)
            with gr.Column():
                with gr.Accordion("Dozens", open=True):
                    dozens_output = gr.Textbox(label="Dozens", lines=10, max_lines=50)
        with gr.Row():
            with gr.Column():
                with gr.Accordion("Columns", open=True):
                    columns_output = gr.Textbox(label="Columns", lines=10, max_lines=50)
            with gr.Column():
                with gr.Accordion("Streets", open=True):
                    streets_output = gr.Textbox(label="Streets", lines=10, max_lines=50)
        with gr.Row():
            with gr.Column():
                with gr.Accordion("Corners", open=True):
                    corners_output = gr.Textbox(label="Corners", lines=10, max_lines=50)
            with gr.Column():
                with gr.Accordion("Double Streets", open=True):
                    six_lines_output = gr.Textbox(label="Double Streets", lines=10, max_lines=50)
        with gr.Row():
            with gr.Column():
                with gr.Accordion("Splits", open=True):
                    splits_output = gr.Textbox(label="Splits", lines=10, max_lines=50)
            with gr.Column():
                with gr.Accordion("Sides of Zero", open=True):
                    sides_output = gr.Textbox(label="Sides of Zero", lines=10, max_lines=50)

    with gr.Row():
        save_button = gr.Button("Save Session")
        load_input = gr.File(label="Upload Session")
    save_output = gr.File(label="Download Session")

    # Event Handlers
    spins_textbox.change(
        fn=lambda x: x,
        inputs=spins_textbox,
        outputs=spins_display
    )

    clear_spins_button.click(
        fn=clear_spins,
        inputs=[],
        outputs=[spins_display, spins_textbox, spin_analysis_output, last_spin_display]
    )

    clear_all_button.click(
        fn=clear_all,
        inputs=[],
        outputs=[
            spins_display, spins_textbox, spin_analysis_output, last_spin_display,
            even_money_output, dozens_output, columns_output, streets_output,
            corners_output, six_lines_output, splits_output, sides_output,
            straight_up_table, top_18_table, strongest_numbers_output
        ]
    ).then(
        fn=clear_outputs,
        inputs=[],
        outputs=[
            spin_analysis_output, even_money_output, dozens_output, columns_output,
            streets_output, corners_output, six_lines_output, splits_output,
            sides_output, straight_up_table, top_18_table, strongest_numbers_output,
            dynamic_table_output, strategy_output, color_code_output
        ]
    )

    generate_spins_button.click(
        fn=generate_random_spins,
        inputs=[num_spins_input, spins_display, last_spin_count],
        outputs=[spins_display, spins_textbox, spin_analysis_output]
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
    
    analyze_button.click(
        fn=analyze_spins,
        inputs=[spins_display, reset_scores_checkbox, strategy_dropdown] + kitchen_martingale_checkboxes_list + victory_vortex_checkboxes_list,
        outputs=[
            spin_analysis_output, even_money_output, dozens_output, columns_output,
            streets_output, corners_output, six_lines_output, splits_output,
            sides_output, straight_up_table, top_18_table, strongest_numbers_output,
            dynamic_table_output, strategy_output
        ]
    ).then(
        fn=create_color_code_table,
        inputs=[],
        outputs=[color_code_output]
    )

    reset_button.click(
        fn=reset_scores,
        inputs=[],
        outputs=[spin_analysis_output]
    )

    clear_button.click(
        fn=clear_outputs,
        inputs=[],
        outputs=[
            spin_analysis_output, even_money_output, dozens_output, columns_output,
            streets_output, corners_output, six_lines_output, splits_output,
            sides_output, straight_up_table, top_18_table, strongest_numbers_output,
            dynamic_table_output, strategy_output, color_code_output
        ]
    )

    save_button.click(
        fn=save_session,
        inputs=[],
        outputs=[save_output]
    )

    load_input.change(
        fn=load_session,
        inputs=[load_input],
        outputs=[spins_display, spins_textbox]
    )

    undo_button.click(
        fn=undo_last_spin,
        inputs=[spins_display, strategy_dropdown] + kitchen_martingale_checkboxes_list + victory_vortex_checkboxes_list,
        outputs=[
            spin_analysis_output, even_money_output, dozens_output, columns_output,
            streets_output, corners_output, six_lines_output, splits_output,
            sides_output, straight_up_table, top_18_table, strongest_numbers_output,
            spins_textbox, spins_display, dynamic_table_output, strategy_output,
            color_code_output
        ]
    )

    # Update both the dynamic table and strategy recommendations when the strategy changes
    strategy_dropdown.change(
        fn=toggle_checkboxes,
        inputs=[strategy_dropdown],
        outputs=[kitchen_martingale_checkboxes, victory_vortex_checkboxes]
    ).then(
        fn=show_strategy_recommendations,
        inputs=[strategy_dropdown] + kitchen_martingale_checkboxes_list + victory_vortex_checkboxes_list,
        outputs=[strategy_output]
    ).then(
        fn=lambda strategy: (print(f"Updating Dynamic Table with Strategy: {strategy}"), create_dynamic_table(strategy if strategy != "None" else None))[-1],
        inputs=[strategy_dropdown],
        outputs=[dynamic_table_output]
    )

    strongest_numbers_dropdown.change(
        fn=get_strongest_numbers_with_neighbors,
        inputs=[strongest_numbers_dropdown],
        outputs=[strongest_numbers_output]
    )

# Launch the interface
demo.launch()