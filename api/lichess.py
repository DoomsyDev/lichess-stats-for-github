import io
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import json
import pandas as pd
import requests
import re
import pytz
from datetime import datetime, time, timedelta


def start_end_today():
    tz = pytz.timezone("Europe/Lisbon")
    today = datetime.now(tz).date()
    start = tz.localize(datetime.combine(today, time(0,0,0)))
    end = start + timedelta(days=1)
    return int(start.timestamp()*1000), int(end.timestamp()*1000)

def fetch_games(username, since, until):
    url = f"https://lichess.org/api/games/user/{username}"
    params = {"since": since, "until": until, "max": 500}
    headers = {"Accept": "application/x-ndjson"}
    r = requests.get(url, params=params, headers=headers, stream=True, timeout=30)
    r.raise_for_status()
    games = []
    for line in r.iter_lines(decode_unicode=True):
        if line:
            try:
                games.append(json.loads(line))  # NDJSON → dict, safer than eval
            except Exception:
                # skip malformed lines but continue processing
                continue
    return games

def process_games(games, username):
    rows = []
    uname = username.lower()
    for g in games:
        ts = g.get("createdAt")
        if not ts:
            continue
        dt = datetime.utcfromtimestamp(ts/1000).astimezone(pytz.timezone("Europe/Lisbon"))
        hour = dt.hour
        winner = g.get("winner")
        players = g.get("players", {})
        white_user = players.get("white", {}).get("user", {}).get("name", "").lower()
        black_user = players.get("black", {}).get("user", {}).get("name", "").lower()

        result = "other"
        if winner is None:
            result = "draw"
        elif (winner == "white" and white_user == uname) or (winner == "black" and black_user == uname):
            result = "win"
        elif (white_user == uname) or (black_user == uname):
            result = "loss"

        rows.append({"hour": hour, "result": result})

    return pd.DataFrame(rows)

def build_plot(df, username):
    fig, axs = plt.subplots(1, 2, figsize=(12, 4))

    # Gráfico 1: jogos por hora
    if not df.empty:
        counts = df.groupby("hour").size().reindex(range(24), fill_value=0)
        counts.plot(kind="bar", ax=axs[0], color="skyblue")
        axs[0].set_title(f"Jogos por hora — {username}")
        axs[0].set_xlabel("Hora")
        axs[0].set_ylabel("Número de jogos")
    else:
        axs[0].text(0.5, 0.5, "Sem jogos hoje", ha="center", va="center")
        axs[0].axis("off")

    # Gráfico 2: resultados
    if not df.empty:
        results = df["result"].value_counts()
        results.plot(kind="pie", autopct="%1.1f%%", startangle=90, ax=axs[1])
        axs[1].set_ylabel("")
        axs[1].set_title("Resultados")
    else:
        axs[1].text(0.5, 0.5, "-", ha="center", va="center")
        axs[1].axis("off")

    plt.tight_layout()
    return fig

def main(request):
    # Recebe query string
    username = request.query.get("user")
    if not username:
        return ("Missing ?user=USERNAME", 400)

    # Normalize and validate username
    username = username.strip()
    if username.startswith('@'):
        username = username[1:]

    if not re.match(r'^[A-Za-z0-9_-]{1,50}$', username):
        return ("Invalid username format", 400)

    try:
        since, until = start_end_today()
        games = fetch_games(username, since, until)
        df = process_games(games, username)
        fig = build_plot(df, username)

        buf = io.BytesIO()
        plt.savefig(buf, format="png")
        plt.close(fig)
        buf.seek(0)

        headers = {
            "Content-Type": "image/png",
            "Cache-Control": "public, max-age=60, s-maxage=300, stale-while-revalidate=30"
        }
        return buf.read(), 200, headers
    except Exception as e:
        # Log the error server-side (Vercel will capture stdout)
        print("Error in function:", str(e))
        return (f"Error: {str(e)}", 500, {"Content-Type": "text/plain"})
