from fastapi import FastAPI, HTTPException
from helpers.ref_helper import generate_referral_link, decode_user_id_from_token
from db_fast_version import update_user_points, update_last_visit, check_user, update_days, register_user, set_last_play
from db_fast_version import update_inviter_points, get_friends, get_user_field
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
import math
# Initialize FastAPI app
app = FastAPI()

# Set up CORS
origins = [
    "http://localhost:3000",
    "https://davidbakalov21.github.io",
    "https://renderweatherapp.onrender.com"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define request body models
class UserData(BaseModel):
    telegram_id: int

class RegisterUser(BaseModel):
    telegram_id: int
    username: str
    invited_by:Optional[str] = None

class RecordGame(BaseModel):
    telegram_id: int
    points: int

# Define routes

@app.post("/update_user_data")
async def points_endpoint(data: UserData):
    try:
        id = data.telegram_id
        last_visit = await get_user_field(id, "last_visit")
        today = datetime.now().date()

        # Check if it's the user's first visit or a new day
        if last_visit is None or last_visit.date() != today:
            await update_user_points(id, 1)
            await update_days(id, 1)

        # Update last visit
        await update_last_visit(id)

        return {
            'points': await get_user_field(id,"points"),
            'days': await get_user_field(id,"days_visited"),
            'last_played_date': await get_user_field(id,"last_play"),
            'friends': await get_friends(id)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/start")
async def starter(data: UserData):
    id = data.telegram_id
    return {
        'registered': await check_user(id)
    }

@app.post("/get_ref_link")
async def get_link(data:UserData):
    id=data.telegram_id
    return {
        "link": await get_user_field(id, "ref_link")
    }

@app.post("/register")
async def register(data: RegisterUser):
    try:
        id = data.telegram_id
        name = data.username
        invited_by=data.invited_by
        if invited_by:
            invited_by=int(decode_user_id_from_token(invited_by))
        link=generate_referral_link(id)
        await register_user(id, name,invited_by,link)
        return {
            'status': "success"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/record_game")
async def record_game(data: RecordGame):
    try:
        id = data.telegram_id
        points = data.points
        points_for_inviter = math.ceil(points * 0.05)
        last_play = await get_user_field(id, "last_play")
        today = datetime.now().date()

        # Check if it's the user's first play or a new day
        if last_play is None or last_play.date() != today:
            await update_user_points(id, points)
            await update_inviter_points(id, points_for_inviter)

        # Set last play date to today
        await set_last_play(id)
        return {
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/")
async def test():
    return "fs"

# To run the FastAPI app
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)

#uvicorn fastapi_backend:app --host 127.0.0.1 --port 8000 --workers 4