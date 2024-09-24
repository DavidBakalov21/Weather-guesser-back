from fastapi import FastAPI, HTTPException
from helpers.ref_helper import generate_referral_link, decode_user_id_from_token
from db_fast_version import update_user_points, update_last_visit, get_user_last_visit, get_user_points, check_user, update_days, get_user_days, register_user, get_last_play, set_last_play
from db_fast_version import get_ref_link,update_inviter_points, get_friends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
import math
import redis.asyncio as redis
from contextlib import asynccontextmanager
from aiogram.utils.web_app import safe_parse_webapp_init_data
from const import TOKEN

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        # Create the Redis client and assign it to the app's state
        redis_client = redis.Redis(host='red-crn916m8ii6s73emn12g', port=6379, decode_responses=True) #for render
        #redis_client = redis.Redis(host='redis',port=6379, decode_responses=True) #for docker
        #redis_client = redis.Redis(host='localhost',port=6379, decode_responses=True)
        await redis_client.ping()
        app.state.redis = redis_client
    except redis.ConnectionError as e:
        print("Redis is unavailable. Error: %s", e)
        app.state.redis = None

    
    yield  # Yield control to allow the app to run

    # Close the Redis client after the app is done
    await app.state.redis.close()
# Initialize FastAPI app
app = FastAPI(lifespan=lifespan)


# Set up CORS
origins = [
    "http://localhost:3000",
    "https://davidbakalov21.github.io",
    "https://renderweatherapp.onrender.com",
    "https://renderweatherapp2.onrender.com"
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
#OK
@app.post("/update_user_data")
async def points_endpoint(data: UserData):
    try:
        redis = app.state.redis
        id = data.telegram_id
        last_visit = await get_user_last_visit(id)
        today = datetime.now().date()

        # Check if it's the user's first visit or a new day
        if last_visit is None or last_visit.date() != today:
            await update_user_points(id, 1, redis)
            await update_days(id, 1, redis)

        # Update last visit
        await update_last_visit(id)

        return {
            'points': await get_user_points(id, redis),
            'days': await get_user_days(id, redis),
            'last_played_date': await get_last_play(id),
            'friends': await get_friends(id, redis)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
#OK
@app.post("/start")
async def starter(data: UserData):
    try:
        redis = app.state.redis
        id = data.telegram_id
        user_Data=safe_parse_webapp_init_data(TOKEN, data.u_data) #tg
        is_registered = await check_user(id, redis)
        return {
            'registered': is_registered,
            "userData":user_Data #tg
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

#OK
@app.post("/get_ref_link")
async def get_link(data:UserData):
    id=data.telegram_id
    redis = app.state.redis
    return {
        "link": await get_ref_link(id, redis)
    }
#OK
@app.post("/register")
async def register(data: RegisterUser):
    try:
        redis = app.state.redis
        id = data.telegram_id
        name = data.username
        invited_by=data.invited_by
        if invited_by:
            invited_by=int(decode_user_id_from_token(invited_by))
        link=generate_referral_link(id)
        await register_user(id, name,invited_by,link, redis)
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
        redis = app.state.redis
        points_for_inviter = math.ceil(points * 0.05)
        last_play = await get_last_play(id)
        today = datetime.now().date()

        # Check if it's the user's first play or a new day
        if last_play is None or last_play.date() != today:
            await update_user_points(id, points, redis)
            await update_inviter_points(id, points_for_inviter, redis)

        # Set last play date to today
        await set_last_play(id)
        return {
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/")
async def test():
    return "works"

# To run the FastAPI app
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)

#uvicorn fastapi_backend:app --host 127.0.0.1 --port 8000 --workers 4