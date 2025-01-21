NBA Fantasy Waiver Wire Analyzer with GPT Integration

**Overview**

This project is a Python application designed to analyze NBA fantasy basketball free agents and provide actionable insights. Leveraging ESPN's Fantasy Basketball API, the NBA Stats API, and OpenAI's GPT, this tool suggests top-performing free agents based on:
- 7-day and 15-day averages
- Season-long averages
- Player health and trends

**Key Features**
- Free Agent Analysis: Retrieves and ranks free agents using performance metrics.
- Health Status Tracking: Integrates injury data from ESPN's Fantasy Basketball API.
- GPT-Powered Insights: Provides actionable recommendations for your fantasy roster.
- Recent Trends: Evaluates recent player performance to help you make informed decisions.

**Installation**
Prerequisites
- Python 3.9+
- An ESPN Fantasy Basketball account
- OpenAI API key
- NBA Stats API access

**Setup**
1. Clone the repository:

git clone https://github.com/your_username/nba-fantasy-waiver-gpt.git
cd nba-fantasy-waiver-gpt

2. Create a virtual environment:
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

3. Install dependencies:
pip install -r requirements.txt

4. Set up environment variables:
- Create a .env file based on .env.example:
LEAGUE_ID=your_league_id
ESPN_S2=your_espn_s2_key
SWID=your_swid_key
OPENAI_API_KEY=your_openai_key

**Usage**
Running the Application
1. Activate the virtual environment:
source venv/bin/activate

2. Run the application:
python nba_fantasy_waiver_wire.py

**Sample Output**
Top 10 Free Agents - 7-Day Average:
- Scoot Henderson - 7 Day Avg: 27.50 | Health: Active
- Stephon Castle - 7 Day Avg: 23.00 | Health: Active

**GPT Recommendations:**
1. Pick up Scoot Henderson immediately for scoring consistency.
2. Keep an eye on Stephon Castle as a rising star.

**Technologies Used**
- Python
- ESPN Fantasy Basketball API
- NBA Stats API
- OpenAI GPT
- dotenv for secure environment variable management
- pandas for data manipulation

**File Structure**
.
|-- nba_fantasy_waiver_wire.py     # Main application file
|-- .env.example                  # Environment variable template
|-- requirements.txt              # Python dependencies
|-- README.md                     # Project documentation
|-- assets/                       # (Optional) Screenshots and examples
|-- examples/                     # (Optional) Sample outputs

**Contributing**
Contributions are welcome! To get started:
1. Fork the repository.
2. Create a new branch (git checkout -b feature/your-feature).
3. Commit your changes (git commit -m 'Add a new feature').
4. Push to the branch (git push origin feature/your-feature).
5. Open a Pull Request.

**License**
This project is licensed under the MIT License.

**Acknowledgments**
- ESPN API
- NBA Stats API
- OpenAI

**Contact**
For questions or suggestions, please contact me at [pvwloomis@gmail.com].

