import openai, requests, json, time, os
from espn_api.basketball import League
from nba_api.stats.endpoints import teamvsplayer
from nba_api.stats.static import teams
from datetime import datetime
from cachetools import TTLCache
from dotenv import load_dotenv

load_dotenv()
# ESPN League Configuration
LEAGUE_ID = 2018697524
SEASON_YEAR = 2025
ESPN_S2 = os.getenv("ESPN_S2")
SWID = os.getenv("SWID")

# OpenAI Configuration
openai.api_key = os.getenv("OPENAI_API_KEY")
GPT_MODEL = "gpt-4o"

# Caching and Rate Limiting
CACHE_TTL = 3600
REQUEST_DELAY = 1.5
api_cache = TTLCache(maxsize=100, ttl=CACHE_TTL)

# Scoring Rules
SCORING_RULES = {
    "Field Goals Missed (FGMI)": -0.5,
    "Free Throws Missed (FTMI)": -0.5,
    "Three Pointers Made (3PM)": 1,
    "Rebounds (REB)": 1,
    "Assists (AST)": 1,
    "Steals (STL)": 3,
    "Blocks (BLK)": 3,
    "Turnovers (TO)": -1,
    "Double Doubles (DD)": 5,
    "Triple Doubles (TD)": 15,
    "Quadruple Doubles (QD)": 50,
    "Points (PTS)": 1,
}

# Map the incorrect team tricode to the correct one
pro_team_to_tricode = {
    "ATL": "ATL",
    "BOS": "BOS",
    "BKN": "BKN",
    "CHA": "CHA",
    "CHI": "CHI",
    "CLE": "CLE",
    "DAL": "DAL",
    "DEN": "DEN",
    "DET": "DET",
    "GS": "GSW",      # Golden State Warriors
    "HOU": "HOU",
    "IND": "IND",
    "LAC": "LAC",
    "LAL": "LAL",
    "MEM": "MEM",
    "MIA": "MIA",
    "MIL": "MIL",
    "MIN": "MIN",
    "NO": "NOP",      # New Orleans Pelicans
    "NY": "NYK",      # New York Knicks
    "OKC": "OKC",
    "ORL": "ORL",
    "PHL": "PHI",     # Philadelphia Sixers
    "PHO": "PHX",     # Phoenix Suns
    "POR": "POR",
    "SAC": "SAC",
    "SA": "SAS",      # San Antonio Spurs
    "TOR": "TOR",
    "UTA": "UTA",     # Utah Jazz
    "WAS": "WAS"
}

# Initialize League and Team
league = League(league_id=LEAGUE_ID, year=SEASON_YEAR, espn_s2=ESPN_S2, swid=SWID, debug=True)
my_team = league.teams[2]  # Replace with the correct index for your team

# Helper Functions
def fetch_data_with_retries(url, params, max_retries=3):
    """Fetch data with retries to handle rate limits and transient errors."""
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                print("Rate limit exceeded. Retrying...")
                time.sleep(REQUEST_DELAY)
            else:
                print(f"HTTP Error {response.status_code}: {response.text}")
        except requests.RequestException as e:
            print(f"Request failed: {e}")
        time.sleep(REQUEST_DELAY)
    return None

def fetch_nba_schedule():
    """Fetch NBA schedule JSON."""
    url = "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2.json"
    return fetch_data_with_retries(url, {})

def get_team_id(team_tricode):
    """Retrieve NBA team ID based on tricode."""
    team_data = next((t for t in teams.get_teams() if t["abbreviation"] == team_tricode), None)
    return team_data["id"] if team_data else None

def get_week_schedule(schedule_data, current_week):
    """Extract the schedule for the specified week."""
    week_schedule = []
    weeks = schedule_data.get("leagueSchedule", {}).get("weeks", [])
    game_dates = schedule_data.get("leagueSchedule", {}).get("gameDates", [])
    current_week_data = next((w for w in weeks if w["weekNumber"] == current_week), None)
    if not current_week_data:
        return []

    start_date = datetime.strptime(current_week_data["startDate"], "%Y-%m-%dT%H:%M:%SZ").date()
    end_date = datetime.strptime(current_week_data["endDate"], "%Y-%m-%dT%H:%M:%SZ").date()

    for game_date in game_dates:
        game_date_str = game_date.get("gameDate")
        if not game_date_str:
            continue
        game_date_obj = datetime.strptime(game_date_str.split()[0], "%m/%d/%Y").date()
        if start_date <= game_date_obj <= end_date:
            for game in game_date.get("games", []):
                week_schedule.append({
                    "date": game_date_obj,
                    "home_team": game.get("homeTeam", {}).get("teamTricode", "Unknown"),
                    "away_team": game.get("awayTeam", {}).get("teamTricode", "Unknown"),
                })
    return week_schedule

def get_player_schedules(roster, week_schedule, team_to_tricode_map):
    """
    Get schedules for players, along with performance data for PerGame and Per100Possessions.
    Args:
        roster (list): List of player objects.
        week_schedule (list): Weekly schedule with game details.
        team_to_tricode_map (dict): Mapping of ESPN team names to NBA tricodes.
    Returns:
        dict: Player schedules with performance data.
    """
    player_schedules = {}
    for player in roster:
        # Map player's pro team to tricode
        team_tricode = team_to_tricode_map.get(player.proTeam, player.proTeam)
        print(f"Finding schedule for {player.name} ({team_tricode}):")

        # Filter the schedule for games involving the player's team
        team_schedule = [
            {
                "date": game["date"],
                "home_team": game["home_team"],
                "away_team": game["away_team"],
                "opponent_team": game["away_team"] if game["home_team"] == team_tricode else game["home_team"],  # Add opponent team
                "team_tricode": team_tricode,
            }
            for game in week_schedule
            if game["home_team"] == team_tricode or game["away_team"] == team_tricode
        ]

        player_schedules[player.name] = []

        for game in team_schedule:
            opponent_team = game["opponent_team"]
            opponent_team_id = get_team_id(opponent_team)

            try:
                # Fetch performance data using TeamVsPlayer
                print(f"Fetching performance data for Player ID {player.playerId} vs Team ID {opponent_team_id}...")
                performance_data = {}

                for measure_type in ["Per100Possessions"]:
                    tvp = teamvsplayer.TeamVsPlayer(
                        team_id=opponent_team_id,
                        vs_player_id=player.playerId,
                        season="2024-25",
                        season_type_playoffs="Regular Season",
                        per_mode_detailed=measure_type
                    )
                    data_frame = tvp.get_data_frames()[0]

                    if not data_frame.empty:
                        # Extract numeric stats and calculate averages
                        numeric_data = data_frame.select_dtypes(include=["number"])
                        performance_data[measure_type] = numeric_data.mean().to_dict()
                    else:
                        print(f"No data available for {player.name} vs {opponent_team} ({measure_type})")

                # Add game and performance data
                player_schedules[player.name].append({
                    "game": game,
                    "performance": performance_data
                })

                time.sleep(REQUEST_DELAY)  # Respect rate-limiting

            except Exception as e:
                print(f"Error fetching data for Player ID {player.playerId} against Team ID {opponent_team_id}: {e}")
                player_schedules[player.name].append({
                    "game": game,
                    "performance": "Error fetching data"
                })

    return player_schedules

# Function to fetch player health status
def get_player_health_status(player):
    try:
        # Assuming player.injury_status provides health info in the espn_api library
        return player.injury_status if hasattr(player, 'injury_status') else "Active"
    except Exception as e:
        print(f"Error fetching health status for {player.name}: {e}")
        return "Unknown"

def calculate_player_projected_points(player, player_schedule, scoring_rules):
    """
    Calculate total projected points for a player based on their schedule and scoring rules.
    """
    total_points = 0
    for game in player_schedule:
        performance = game.get("performance", {})
        if not performance:
            continue  # Skip if no performance data available

        # Apply scoring rules to performance stats
        points = (
            performance.get("PTS", 0) * scoring_rules.get("PTS", 1) +
            performance.get("REB", 0) * scoring_rules.get("REB", 1) +
            performance.get("AST", 0) * scoring_rules.get("AST", 1) +
            performance.get("STL", 0) * scoring_rules.get("STL", 3) +
            performance.get("BLK", 0) * scoring_rules.get("BLK", 3) -
            performance.get("TOV", 0) * scoring_rules.get("TO", -1) +
            performance.get("3PM", 0) * scoring_rules.get("3PM", 1)
        )

        total_points += points

    return total_points


def format_data_for_gpt(player_schedules, roster):
    """
    Formats player schedules, average points, and other relevant details for GPT processing.
    Args:
        player_schedules (dict): Player schedules with games and performance data.
        roster (list): List of player objects from the user's team.
    Returns:
        str: Formatted data ready to be sent to GPT.
    """
    # Debugging: Check the type and contents of roster
    if not roster or not isinstance(roster, list):
        raise ValueError(f"Invalid roster provided. Expected a list of player objects, got: {type(roster)}")
    
    # Ensure roster contains player objects with a 'name' attribute
    if not all(hasattr(player, 'name') for player in roster):
        raise ValueError("Roster contains elements without 'name' attributes. Ensure you pass player objects.")

    output = []
    player_map = {player.name: player for player in roster}  # Map player names to player objects

    for player_name, games in player_schedules.items():
        player = player_map.get(player_name)
        if not player:
            print(f"Player object not found for {player_name}.")
            continue
        avg_points = player.avg_points if hasattr(player, 'avg_points') else "N/A"
        health_status = get_player_health_status(player)
        output.append(f"\n{player_name}:")
        output.append(f"  - Avg Points: {avg_points}")
        output.append(f"  - Health Status: {health_status}")

        for item in games:
            game = item["game"]
            performance = item.get("performance", {})
            game_date = game["date"]
            opponent_team = game["opponent_team"]
            output.append(f"  - Game: {game_date}, Opponent: {opponent_team}")

            if isinstance(performance, dict):  # Ensure performance is a dictionary
                output.append("    Performance Stats:")
                for stat, value in performance.items():
                    output.append(f"      - {stat}: {value}")
            else:
                output.append(f"    Performance Data: {performance}")

    return "\n".join(output)

def chunk_data(data, chunk_size=8192):
    """
    Split data into smaller chunks to stay within token limits.
    Args:
        data (str): The input data string to chunk.
        chunk_size (int): Maximum size of each chunk in characters.
    Returns:
        list: A list of data chunks.
    """
    lines = data.split("\n")
    chunks = []
    current_chunk = []
    current_size = 0

    for line in lines:
        line_length = len(line)
        if current_size + line_length > chunk_size:
            chunks.append("\n".join(current_chunk))
            current_chunk = []
            current_size = 0
        current_chunk.append(line)
        current_size += line_length + 1  # Add 1 for the newline character

    if current_chunk:
        chunks.append("\n".join(current_chunk))

    return chunks

# Fetch GPT Recommendations
def get_gpt_recommendations(player_data):
    """
    Get recommendations from GPT based on player schedules and scoring rules.
    """
    chunks = chunk_data(player_data, chunk_size=8192)  # Adjust chunk size as necessary
    recommendations = []
    for i, chunk in enumerate(chunks):
        print(f"Analyzing Chunk {i + 1}:\n{chunk[:500]}")  # Log chunk content for debugging
        prompt = f"""
        You are an expert fantasy basketball coach. 
        Based on the following player schedules, scoring rules, and expected game performances, recommend the optimal lineup to maximize fantasy points while adhering to the weekly game limit.

        **Scoring Rules**:
        {SCORING_RULES}

        **Key Considerations**:
        1. Players with highest projected points for a game should be prioritized, even if they have multiple games per week.
        2. Matchups matter. Players tend to perform better or worse depending on their opponent's defensive statistics and how they historically perform against a given team Per100Possesions.
        3. Weekly game limits must be considered; if a player has fewer games but a significantly higher average, they should still be prioritized.
        4. Provide clear reasons for each recommendation.

        **Player Data**:
        {chunk}

        Format your recommendations as follows:
        1. **Create a list of player plus the specific game in descending order of projected points:**
        3. **Reasoning and Key Insights:**
        """
        try:
            response = openai.chat.completions.create(
                model=GPT_MODEL,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1500,
                temperature=0.7
            )
            recommendations.append(response.choices[0].message.content)
        except Exception as e:
            print(f"Error fetching recommendations from GPT: {e}")
            recommendations.append(f"Error: {str(e)}")

    return "\n".join(recommendations)

# Main Function
def main():
    schedule_data = fetch_nba_schedule()
    if not schedule_data:
        return
    current_week = league.currentMatchupPeriod
    week_schedule = get_week_schedule(schedule_data, current_week)
    roster = my_team.roster  # Ensure roster is fetched correctly

    # Fetch player schedules
    player_schedules = get_player_schedules(roster, week_schedule, pro_team_to_tricode)

    # Format schedules for GPT
    formatted_data = format_data_for_gpt(player_schedules, roster=roster)
    print("\nFormatted data to be sent to GPT:")
    print(formatted_data)  # Debugging formatted data

    # Fetch GPT recommendations
    recommendations = get_gpt_recommendations(formatted_data)
    print("\nGPT Recommendations:")
    print(recommendations)

if __name__ == "__main__":
    main()