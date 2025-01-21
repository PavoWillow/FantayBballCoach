import os, time, unicodedata
from espn_api.basketball import League
from nba_api.stats.endpoints import playercareerstats, playergamelog
from nba_api.stats.static import players
from dotenv import load_dotenv
import pandas as pd
import openai # GPT integration

# Load API keys and credentials
load_dotenv()

LEAGUE_ID = os.getenv("LEAGUE_ID")
SEASON_YEAR = 2025
ESPN_S2 = os.getenv("ESPN_S2")
SWID = os.getenv("SWID")
OPEN_AI_KEY = os.getenv("OPENAI_API_KEY")
REQUEST_DELAY = 2

# OpenAI Configuration
openai.api_key = os.getenv("OPENAI_API_KEY")
GPT_MODEL = "gpt-4o"

# Initialize the league
league = League(league_id=LEAGUE_ID, year=SEASON_YEAR, espn_s2=ESPN_S2, swid=SWID, debug=True)

# Function to normalize player names
def normalize_name(name):
    return unicodedata.normalize('NFKD', name).encode('ASCII', 'ignore').decode('utf-8')

# Fetch free agents and calculate trends
def get_free_agents_with_trends(league):
    free_agents = league.free_agents()
    free_agents_data = []

    for player in free_agents:
        try:
            player_name = player.name
            avg_points = player.avg_points
            health_status = get_player_health_status(player)

            # Fetch recent performance stats
            recent_performance = get_recent_performance(player_name)
            time.sleep(REQUEST_DELAY) # Sleep to avoid overloading the NBA API

            free_agents_data.append({
                "name": player_name,
                "team": player.proTeam,
                "position": player.position,
                "health_status": health_status,
                "season_avg_points": avg_points,
                "7_day_avg": recent_performance.get("7_day_avg", "N/A"),
                "15_day_avg": recent_performance.get("15_day_avg", "N/A"),
                "trend": recent_performance.get("trend", "N/A"),
            })
        except Exception as e:
            print(f"Error processing player {player.name}: {e}")
    
    return free_agents_data

# Function to fetch player health status
def get_player_health_status(player):
    try:
        return player.injuryStatus if hasattr(player, 'injuryStatus') else "Active"
    except Exception as e:
        print(f"Error fetching health status for {player.name}: {e}")
        return "Unknown"

# Fetch recent performance stats
def get_recent_performance(player_name):
    normalized_name = normalize_name(player_name)
    player = next((p for p in players.get_players() if normalize_name(p["full_name"]) == normalized_name), None)
    if not player:
        print(f"Player {player_name} not found in NBA database.")
        return {}
    
    try:
        # Fetch game logs for the current season
        game_log = playergamelog.PlayerGameLog(player_id=player["id"], season="2024-25").get_data_frames()[0]
        game_log["GAME_DATE"] = pd.to_datetime(game_log["GAME_DATE"], format="%b %d, %Y", errors="coerce")
        time.sleep(REQUEST_DELAY) # Sleep to avoid overloading the NBA API

        # Filter for last 7 and 15 days
        last_7_days = game_log[game_log["GAME_DATE"] >= pd.Timestamp.now() - pd.Timedelta(days=7)]
        last_15_days = game_log[game_log["GAME_DATE"] >= pd.Timestamp.now() - pd.Timedelta(days=15)]

        return {
            "7_day_avg": last_7_days["PTS"].mean() if not last_7_days.empty else 0,
            "15_day_avg": last_15_days["PTS"].mean() if not last_15_days.empty else 0,
            "trend": "Up" if last_7_days["PTS"].mean() > last_15_days["PTS"].mean() else "Down",
        }
    except Exception as e:
        print(f"Error fetching performance stats for {player_name}: {e}")
        return {"7_day_avg": 0, "15_day_avg": 0, "trend": "N/A"}

# Filter top 10 free agents
def get_top_free_agents(players, key):
    # Ensure all values for the key are numeric
    for player in players:
        try:
            player[key] = float(player.get(key, 0)) # Convert to float, default to 0 if missing
        except ValueError:
            print(f"Invalid value for {key} in player {player['name']}: {player.get(key)}")
            player[key] = 0 # Set to 0 if conversion fails
    return sorted(players, key=lambda x: x.get(key, 0), reverse=True)[:10]

# Send data to GPT and get recommendations
def format_data_for_gpt(free_agents_data):
    formatted_data = "Free Agent Analysis:\n\n"
    for player in free_agents_data:
        formatted_data += (
            f"- Name: {player['name']}, Team: {player['team']}, Position: {player['position']}, "
            f"Health: {player['health_status']}, 7-day: Avg: {player['7_day_avg']:.2f}, "
            f"15-day Avg: {player['15_day_avg']:.2f}, Season Avg: {player['season_avg_points']:.2f}, "
            f"Trend: {player['trend']}\n"
        )
    return formatted_data


# Send data to GPT and get recommendations
def get_gpt_commendations(data):
    try:
        response = openai.chat.completions.create(
            model=GPT_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert in fantasy basketbal advisor. Provide actionable insights and recommendations based on the given player data."
                },
                {
                    "role": "user",
                    "content": data
                }
            ],
            max_tokens=1500,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error fetching recommendations for GPT: {e}")
        return "Error: Unable to fetch recommendations."

# Main application logic
def main():
    print("Analyzing free agents...")
    free_agents_data = get_free_agents_with_trends(league)

    # Filter top 10 players by 7-day, 15-day, and season average
    top_7_day = get_top_free_agents(free_agents_data, key="7_day_avg")
    top_15_day = get_top_free_agents(free_agents_data, key="15_day_avg")
    top_season_avg = get_top_free_agents(
        [player for player in free_agents_data if player["season_avg_points"] is not None],
        key="season_avg_points",
    )

    if not free_agents_data:
        print("No free agents data found. Please check the league settings or API.")
        return

    # Format data for GPT
    formatted_data = format_data_for_gpt(free_agents_data)
    print("\nFormatted Data for GPT:")
    print(formatted_data)

    # Get GPT recommendations
    recommendations = get_gpt_commendations(formatted_data)
    print("\nGPT Recommendations:")
    print(recommendations)

'''    # Print results
    print("\nTop 10 Free Agents - 7-Day Average:")
    for player in top_7_day:
        print(f"{player['name']} - 7 Day Avg: {player['7_day_avg']:.2f} | Health: {player['health_status']}")

    print("\nTop 10 Free Agents - 15-Day Average:")
    for player in top_15_day:
        print(f"{player['name']} - 15 Day Avg: {player['15_day_avg']:.2f} | Health: {player['health_status']}")

    print("\nTop 10 Free Agents - Season Average:")
    for player in top_season_avg:
        print(f"{player['name']} - Season Avg: {player['season_avg_points']:.2f} | Health: {player['health_status']}")
'''

if __name__ == "__main__":
    main()