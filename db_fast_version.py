from consts import MONGO_STRING
import certifi
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
client = AsyncIOMotorClient(MONGO_STRING, tlsCAFile=certifi.where())
#client = AsyncIOMotorClient("mongodb://host.docker.internal:27017/")
db = client['weather_bot']
collection = db['users']
collection.create_index("user_id")
#OK
async def check_user(user_id, redis):
    if redis is not None:
        cached_user_status = await redis.get(f"user:{user_id}:registered")
        if cached_user_status is not None:
            print("redis worked for check_user")
            return cached_user_status == "True"
    existing_user = await collection.find_one({'user_id': user_id}, {'_id': 1})
    if existing_user:
        if redis is not None:
            await redis.set(f"user:{user_id}:registered", "True",ex=604800)
            print("redis set for check_user")
        return True
    else:
        if redis is not None:
            await redis.set(f"user:{user_id}:registered", "False",ex=604800)
            print("redis set for check_user")
        return False
#OK
async def register_user(user_id, name, inviter_id, link, redis):
    if not await check_user(user_id, redis):
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
        if redis is not None:
            await redis.set(f"user:{user_id}:registered", "True",ex=604800)
            await redis.set(f"user:{user_id}:ref_link", link,ex=604800)
        if inviter_id:
            await reward_inviter(inviter_id, user_id, redis)

async def update_last_visit(user_id):
    print("Update last visit")
    print(datetime.now())
    await collection.update_one(
        {'user_id': user_id},
        {'$set': {'last_visit': datetime.now()}}
    )

async def get_user_last_visit(user_id):
    user_data = await collection.find_one(
        {'user_id': user_id}, 
        {'last_visit': 1, '_id': 0}  # Project only 'last_visit' field
    )
    #print("User data"+str(user_data))
    if user_data and 'last_visit' in user_data:
        #print("Returned last visit"+user_data['last_visit'])
        return user_data['last_visit']
        
    else:
        print("Returned none")
        return None
    
async def get_user_points(user_id, redis):
    if redis is not None:
        cached_user_points = await redis.get(f"user:{user_id}:points")
        if cached_user_points is not None:
            print("redis worked for get points")
            return int(cached_user_points)
    user_data = await collection.find_one(
        {'user_id': user_id}, 
        {'points': 1, '_id': 0}
    )
    if user_data and 'points' in user_data:
        if redis is not None:
            await redis.set(f"user:{user_id}:points", user_data['points'],ex=304800)
            print("redis set for get points")
        return user_data['points']
    else:
        return None

async def reward_inviter(inviter_id, invited_id,redis):
    await update_user_points(inviter_id,40,redis)
    await update_inviter_list(inviter_id, invited_id, redis)

async def update_inviter_list(inviter_id, invited_id, redis):
    await collection.update_one(
        {'user_id': inviter_id},
        {"$push": {"invited": invited_id}}
    )
    user_data = await collection.find_one({'user_id': inviter_id}, {'invited': 1, '_id': 0})
    if user_data and 'invited' in user_data:
        print("redis set for get update_invite")
        if redis is not None:
            await redis.set(f"user:{inviter_id}:invited", user_data['invited'],ex=404800) 


async def update_user_points(user_id, points, redis):
    updated_points = None
    if redis is not None:
        try:
            # Try incrementing the points in Redis
            updated_points = await redis.incrby(f"user:{user_id}:points", points)
        except Exception as e:
            print(f"Redis is unavailable, error: {str(e)}. Falling back to MongoDB.")
            updated_points = None
    
    if updated_points is None:
        # Fetch the current points from MongoDB
        user_data = await collection.find_one({'user_id': user_id}, {'points': 1, '_id': 0})
        
        if user_data and 'points' in user_data:
            # Manually increment the points
            updated_points = user_data['points'] + points
            
            # Update MongoDB with the new points
            await collection.update_one(
                {'user_id': user_id},
                {'$inc': {'points': points}},
            )
    else:
        await collection.update_one(
            {'user_id': user_id},
            {'$set': {'points': updated_points}},
        )

    return updated_points

async def update_days(user_id, days, redis):
    await collection.update_one(
        {'user_id': user_id},
        {'$inc': {'days_visited': days}}, 
    )
    user_data = await collection.find_one({'user_id': user_id}, {'days_visited': 1, '_id': 0})
    if user_data and 'days_visited' in user_data:
        print("redis set for get update_days")
        if redis is not None:
            await redis.set(f"user:{user_id}:days_visited", user_data['days_visited'], ex=300400) 

async def get_user_days(user_id, redis):
    if redis is not None:
        cached_user_days = await redis.get(f"user:{user_id}:days_visited")
        if cached_user_days is not None:
            print("redis worked for get days")
            return int(cached_user_days)
    user_data = await collection.find_one(
        {'user_id': user_id}, 
        {'days_visited': 1, '_id': 0}
    )
    if user_data and 'days_visited' in user_data:
        if redis is not None:
            print("redis set for get points")
            await redis.set(f"user:{user_id}:days_visited", user_data['days_visited'],ex=300400)
        return user_data['days_visited']
    else:
        return None
    
async def set_last_play(user_id):
    print("Update last visit")
    print(datetime.now())
    await collection.update_one(
        {'user_id': user_id},
        {'$set': {'last_play': datetime.now()}}
    )

async def get_last_play(user_id):
    user_data = await collection.find_one(
        {'user_id': user_id}, 
        {'last_play': 1, '_id': 0}
    )
    if user_data and 'last_play' in user_data:
        return user_data['last_play']
        
    else:
        print("Returned none")
        return None
#OK
async def get_ref_link(user_id, redis):
    if redis is not None:
        cached_ref_link = await redis.get(f"user:{user_id}:ref_link")
        if cached_ref_link is not None:
            print("redis works for get ref_link")
            # If cached ref_link exists, return it
            return cached_ref_link
    user_data = await collection.find_one(
        {'user_id': user_id}, 
        {'ref_link': 1, '_id': 0}
    )
    if user_data and 'ref_link' in user_data:
        if redis is not None:
            await redis.set(f"user:{user_id}:ref_link", user_data['ref_link'], ex=600800)
            print("redis set for ref link")
        return user_data['ref_link']
    else:
        return None

    
async def update_inviter_points(player_id, points,redis):
    user_data = await collection.find_one(
        {'user_id': player_id}, 
        {'invited_by': 1, '_id': 0}
    )
    if user_data and user_data.get('invited_by'):
        inviter_id=user_data['invited_by']
        await update_user_points(inviter_id, points, redis)

async def get_friends(user_id, redis):
    if redis is not None:
        cached_friends = await redis.get(f"user:{user_id}:friends")
        if cached_friends is not None:
            print("redis worked for get_friends")
            return eval(cached_friends)  
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
        if redis is not None:
            await redis.set(f"user:{user_id}:friends", str(friends),ex=600800)
            print("redis set for get friends")
        return friends
    else:
        return None