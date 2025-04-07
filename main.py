
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import yfinance as yf
import smtplib
from email.mime.text import MIMEText
from datetime import datetime

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

EMAIL = "ankitp666280@gmail.com"
EMAIL_PASS = "egjheilvkqgqtjqm"
TO_EMAIL = "ankitp666280@gmail.com"

class SignalResponse(BaseModel):
    chartData: dict
    alerts: list

def send_email(subject, body):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = EMAIL
    msg["To"] = TO_EMAIL
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL, EMAIL_PASS)
            server.sendmail(EMAIL, TO_EMAIL, msg.as_string())
    except Exception as e:
        print("Email error:", e)

def get_data(symbol):
    try:
        df = yf.download(symbol, period="1d", interval="1m")
        df.reset_index(inplace=True)
        df.rename(columns={"Datetime": "time"}, inplace=True)
        return df
    except Exception as e:
        print("Yahoo Finance Error:", e)
        return pd.DataFrame()

def generate_signals(df):
    df["SMA10"] = df["close"].rolling(10).mean()
    df["SMA50"] = df["close"].rolling(50).mean()
    df["RSI"] = 100 - (100 / (1 + df["close"].pct_change().rolling(14).mean()))

    signals = []
    last_signal = None

    for i in range(1, len(df)):
        row = df.iloc[i]
        prev = df.iloc[i - 1]

        if row.SMA10 > row.SMA50 and prev.SMA10 <= prev.SMA50 and row.RSI < 70:
            signal = {
                "type": "BUY",
                "message": "SMA crossover + RSI confirm",
                "price": round(row.close, 4),
                "time": row.time.strftime("%Y-%m-%d %H:%M")
            }
            signals.append(signal)
            if last_signal != "BUY":
                send_email("BUY Signal", str(signal))
                last_signal = "BUY"

        elif row.SMA10 < row.SMA50 and prev.SMA10 >= prev.SMA50 and row.RSI > 30:
            signal = {
                "type": "SELL",
                "message": "SMA cross down + RSI confirm",
                "price": round(row.close, 4),
                "time": row.time.strftime("%Y-%m-%d %H:%M")
            }
            signals.append(signal)
            if last_signal != "SELL":
                send_email("SELL Signal", str(signal))
                last_signal = "SELL"

    chart_data = {
        "labels": df["time"].dt.strftime("%H:%M").tolist(),
        "datasets": [
            {"label": "Close", "data": df["close"].tolist(), "borderWidth": 2},
            {"label": "SMA10", "data": df["SMA10"].tolist(), "borderWidth": 1},
            {"label": "SMA50", "data": df["SMA50"].tolist(), "borderWidth": 1},
        ]
    }

    return {"chartData": chart_data, "alerts": signals[-5:]}

@app.get("/signals/{symbol}", response_model=SignalResponse)
async def get_signals(symbol: str):
    try:
        df = get_data(symbol)
        if df.empty:
            raise Exception("No data returned")
        result = generate_signals(df)
        return result
    except Exception as e:
        print("Error generating signals:", e)
        return {"chartData": {}, "alerts": []}
