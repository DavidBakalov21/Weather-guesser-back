from pymongo import MongoClient
from consts import MONGO_STRING
import certifi
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
client = AsyncIOMotorClient(MONGO_STRING, tlsCAFile=certifi.where())
#client = AsyncIOMotorClient("mongodb://host.docker.internal:27017/")
db = client['weather_bot']
collection = db['users']
collection.create_index("user_id")
async def get_all_users_data():
    try:
        # Fetch all documents from the collection
        users = await list(collection.find({}))
        return users
    except Exception as e:
        print(f"An error occurred while retrieving users data: {e}")
        return []

async def check_user(user_id):
    existing_user = await collection.find_one({'user_id': user_id}, {'_id': 1})
    if existing_user:
        return True
    else:
        return False

async def register_user(user_id, name, inviter_id, link):
    if not await check_user(user_id):
        user_data = {
            'user_name': name,
            'user_id': user_id,
            "points":0,
            "last_visit": None,
            "days_visited":0,
            "last_play":None,
            "invited":[],
            "invited_by":inviter_id,
            "ref_link":link
        }
        await collection.insert_one(user_data)
        if inviter_id:
            await reward_inviter(inviter_id, user_id)

async def update_last_visit(user_id):
    print("Update last visit")
    print(datetime.now())
    await collection.update_one(
        {'user_id': user_id},
        {'$set': {'last_visit': datetime.now()}}
    )

async def reward_inviter(inviter_id, invited_id):
    await update_user_points(inviter_id,40)
    await update_inviter_list(inviter_id, invited_id)

async def update_inviter_list(inviter_id, invited_id):
    await collection.update_one(
        {'user_id': inviter_id},
        {"$push": {"invited": invited_id}}
    )

async def update_user_points(user_id, points):
    await collection.update_one(
        {'user_id': user_id},
        {'$inc': {'points': points}},
        #upsert=True
    )

async def update_days(user_id, days):
    await collection.update_one(
        {'user_id': user_id},
        {'$inc': {'days_visited': days}}, 
        #upsert=True
    )
    
async def set_last_play(user_id):
    print("Update last visit")
    print(datetime.now())
    await collection.update_one(
        {'user_id': user_id},
        {'$set': {'last_play': datetime.now()}}
    )

async def update_inviter_points(player_id, points):
    user_data = await collection.find_one(
        {'user_id': player_id}, 
        {'invited_by': 1, '_id': 0}
    )
    if user_data and user_data.get('invited_by'):
        inviter_id=user_data['invited_by']
        await update_user_points(inviter_id, points)

async def get_friends(user_id):
    user_data = await collection.find_one(
        {'user_id': user_id}, 
        {'invited': 1, '_id': 0}
    )
    if user_data and 'invited' in user_data:
        friend_ids = user_data['invited']
        friends_data = await collection.find(
            {'user_id': {'$in': friend_ids}}, 
            {'user_name': 1, '_id': 0}
        ).to_list(length=len(friend_ids))
        friends = [friend['user_name'] for friend in friends_data if 'user_name' in friend]
        return friends
    else:
        return None

async def get_user_field(user_id, field):
    try:
        user_data = await collection.find_one(
            {'user_id': user_id},
            {field: 1, '_id': 0}
        )
        if user_data and field in user_data:
            return user_data[field]
        else:
            return None
    except Exception as e:
        return None