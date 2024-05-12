from flask import Flask, jsonify
import pyodbc
import pandas as pd
import numpy as np

app = Flask(__name__)

# Define database connection function
def connect_to_database():
    connection_string = "Server=tcp:ballbookingserver.database.windows.net,1433;Initial Catalog=BallBooking;Persist Security Info=False;User ID=ballbookingadmin;Password=bbadmin@123;MultipleActiveResultSets=False;Encrypt=True;TrustServerCertificate=False;Connection Timeout=30;"
    connection_params = {}
    for param in connection_string.split(';'):
        if '=' in param:
            key, value = param.split('=')
            connection_params[key.strip()] = value.strip()
    server = connection_params.get('Server')
    database = connection_params.get('Initial Catalog')
    username = connection_params.get('User ID')
    password = connection_params.get('Password')
    driver = '{ODBC Driver 17 for SQL Server}'
    conn = pyodbc.connect('DRIVER=' + driver + ';SERVER=' + server + ';DATABASE=' + database + ';UID=' + username + ';PWD=' + password)
    return conn

# Define function to calculate rankings
def calculate_rankings():
    conn = connect_to_database()  # Assuming this function connects to your database
    ranking_query = "SELECT team1_id, team2_id, result FROM tbl_club_ranking"
    club_ranking = pd.read_sql(ranking_query, conn)
    
    # Get unique team IDs
    team_ids = set(club_ranking['team1_id'].tolist() + club_ranking['team2_id'].tolist())
    teams = list(team_ids)
    num_of_teams = len(teams)
    
    # Create a dictionary to map team IDs to indices
    team_indices = {team: i for i, team in enumerate(teams)}
    
    # Initialize matrices
    c = np.zeros((num_of_teams, num_of_teams))
    b = np.zeros(num_of_teams)
    
    # Populate matrices
    for _, row in club_ranking.iterrows():
        t1_id = row['team1_id']
        t2_id = row['team2_id']
        result = row['result']
        
        t1_index = team_indices[t1_id]
        t2_index = team_indices[t2_id]
        
        c[t1_index, t1_index] += 1
        c[t2_index, t2_index] += 1
        
        if result == 1:
            c[t1_index, t2_index] -= 1
            c[t2_index, t1_index] -= 1
            b[t1_index] += 2  # Adjust the score for winning team
            b[t2_index] -= 2  # Adjust the score for losing team
        elif result == 2:
            c[t1_index, t2_index] -= 1
            c[t2_index, t1_index] -= 1
            b[t1_index] -= 2  # Adjust the score for losing team
            b[t2_index] += 2  # Adjust the score for winning team
    
    # Diagonal adjustment
    np.fill_diagonal(c, c.diagonal() + 2 * num_of_teams)
    
    # Solve linear equations
    r = np.linalg.solve(c, b)
    
    # Calculate ranks
    ranks = np.argsort(r)[::-1] + 1
    
    # Create rankings dictionary
    rankings = {team: rank for team, rank in zip(teams, ranks)}
    
    return rankings



# Define API endpoint for getting rankings
@app.route('/rankings', methods=['GET'])
def get_rankings():
    rankings = calculate_rankings()
    print('I am hit')
    return "Ok"

# Define API endpoint for updating rankings
@app.route('/update-rankings', methods=['POST'])
def update_rankings():
    rankings = calculate_rankings()
    print(rankings,'Ranking of team is')
    conn = connect_to_database()
    cursor = conn.cursor()
    update_query = "UPDATE tbl_clubs SET rank = ? WHERE clubID = ?"
    for team_id, rank in rankings.items():
        rank = int(rank)
        cursor.execute(update_query, (rank, team_id))
    conn.commit()
    cursor.close()
    return "Rankings updated successfully."

if __name__ == '__main__':
    app.run(debug=True)