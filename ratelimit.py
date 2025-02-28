import httpx
import asyncio
from config import TOKEN, TESTING_CHANNEL_ID
from discord.http import Route
import time

async def get_rate_limits():
    url = "https://discord.com/api/v10/users/@me"
    headers = {
        "Authorization": f"Bot {TOKEN}",
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)

    # Extract Rate Limit Headers
    ratelimit_limit = response.headers.get("X-RateLimit-Limit")
    ratelimit_remaining = response.headers.get("X-RateLimit-Remaining")
    ratelimit_reset = response.headers.get("X-RateLimit-Reset")
    ratelimit_reset_after = response.headers.get("X-RateLimit-Reset-After")
    ratelimit_global = response.headers.get("X-RateLimit-Global")

    print(f"Rate Limit Headers: {response.headers.keys()}")
    print("🔹 Discord Rate Limit Info:")
    print(f"🔹 Limit: {ratelimit_limit}")
    print(f"🔹 Remaining: {ratelimit_remaining}")
    print(f"🔹 Reset Timestamp: {ratelimit_reset}")
    print(f"🔹 Reset After: {ratelimit_reset_after} seconds")
    print(f"🔹 Global Limit: {ratelimit_global}")

async def send_message_to_channel():
    """Send a message to a specific Discord channel via HTTP request."""
    url = f"https://discord.com/api/v10/channels/{TESTING_CHANNEL_ID}/messages"
    headers = {
        "Authorization": f"Bot {TOKEN}",
        "Content-Type": "application/json"
    }

    # Message content
    payload = {
        "content": "📢 **Hello, this is a test message sent via HTTP API request!**"
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload)

    if response.status_code == 200 or response.status_code == 201:
        # Extract Rate Limit Headers
        ratelimit_limit = response.headers.get("X-RateLimit-Limit")
        ratelimit_remaining = response.headers.get("X-RateLimit-Remaining")
        ratelimit_reset = response.headers.get("X-RateLimit-Reset")
        ratelimit_reset_after = response.headers.get("X-RateLimit-Reset-After")
        ratelimit_global = response.headers.get("X-RateLimit-Global")

        #print(f"Rate Limit Headers: {response.headers.keys()}")
        print("🔹 Discord Rate Limit Info:")
        print(f"🔹 Limit: {ratelimit_limit}")
        print(f"🔹 Remaining: {ratelimit_remaining}")
        print(f"🔹 Reset Timestamp: {ratelimit_reset}")
        print(f"🔹 Reset After: {ratelimit_reset_after} seconds")
        print(f"🔹 Global Limit: {ratelimit_global}")
        print("✅ Message sent successfully!")
    else:
        print(f"❌ Failed to send message! Status Code: {response.status_code}, Response: {response.text}")



async def create_private_thread():
    """Creates a private thread inside a channel."""
    url = f"https://discord.com/api/v10/channels/{TESTING_CHANNEL_ID}/threads"
    headers = {
        "Authorization": f"Bot {TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "name": "Private Thread Example",  # Thread name
        "type": 12,  # Type 12 = PRIVATE_THREAD (Must be in a GUILD_TEXT or FORUM channel)
        "auto_archive_duration": 1440,  # Archive after 24 hours (60, 1440, 4320, 10080)
        "invitable": False  # Only admins can invite others
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload)

    if response.status_code in [200, 201]:
        thread_data = response.json()
        # Extract Rate Limit Headers
        ratelimit_limit = response.headers.get("X-RateLimit-Limit")
        ratelimit_remaining = response.headers.get("X-RateLimit-Remaining")
        ratelimit_reset = response.headers.get("X-RateLimit-Reset")
        ratelimit_reset_after = response.headers.get("X-RateLimit-Reset-After")
        ratelimit_global = response.headers.get("X-RateLimit-Global")

        print(f"Rate Limit Headers: {response.headers.keys()}")
        print("🔹 Discord Rate Limit Info:")
        print(f"🔹 Limit: {ratelimit_limit}")
        print(f"🔹 Remaining: {ratelimit_remaining}")
        print(f"🔹 Reset Timestamp: {ratelimit_reset}")
        print(f"🔹 Reset After: {ratelimit_reset_after} seconds")
        print(f"🔹 Global Limit: {ratelimit_global}")
        print(f"✅ Private thread created: {thread_data['name']} (ID: {thread_data['id']})")
    else:
        print(f"❌ Failed to create thread! Status: {response.status_code}, Response: {response.text}")




async def send_dm(user_id, message):
    """Sends a DM to a user."""
    headers = {
        "Authorization": f"Bot {TOKEN}",
        "Content-Type": "application/json"
    }

    # Step 1: Create a DM Channel
    dm_url = "https://discord.com/api/v10/users/@me/channels"
    payload = {"recipient_id": user_id}

    async with httpx.AsyncClient() as client:
        dm_response = await client.post(dm_url, headers=headers, json=payload)
        if 1:
            # Extract Rate Limit Headers
            ratelimit_limit = dm_response.headers.get("X-RateLimit-Limit")
            ratelimit_remaining = dm_response.headers.get("X-RateLimit-Remaining")
            ratelimit_reset = dm_response.headers.get("X-RateLimit-Reset")
            ratelimit_reset_after = dm_response.headers.get("X-RateLimit-Reset-After")
            ratelimit_global = dm_response.headers.get("X-RateLimit-Global")

            #print(f"Rate Limit Headers: {message_response.headers.keys()}")
            print("🔹 Discord Rate Limit Info:")
            print(f"🔹 Limit: {ratelimit_limit}")
            print(f"🔹 Remaining: {ratelimit_remaining}")
            print(f"🔹 Reset Timestamp: {ratelimit_reset}")
            print(f"🔹 Reset After: {ratelimit_reset_after} seconds")
            print(f"🔹 Global Limit: {ratelimit_global}")
            print(f"✅ Message sent successfully to {user_id}!")

    if dm_response.status_code != 200:
        print(f"❌ Failed to create DM channel! Status: {dm_response.status_code}, Response: {dm_response.text}")
        return

    dm_channel_id = dm_response.json()["id"]
    print(f"✅ DM channel created! ID: {dm_channel_id}")

    # Step 2: Send a Message
    if 0:
        message_url = f"https://discord.com/api/v10/channels/{dm_channel_id}/messages"
        message_payload = {"content": message}

        async with httpx.AsyncClient() as client:
            message_response = await client.post(message_url, headers=headers, json=message_payload)

        if message_response.status_code in [200, 201]:
            # Extract Rate Limit Headers
            ratelimit_limit = message_response.headers.get("X-RateLimit-Limit")
            ratelimit_remaining = message_response.headers.get("X-RateLimit-Remaining")
            ratelimit_reset = message_response.headers.get("X-RateLimit-Reset")
            ratelimit_reset_after = message_response.headers.get("X-RateLimit-Reset-After")
            ratelimit_global = message_response.headers.get("X-RateLimit-Global")
            
            #print(f"Rate Limit Headers: {message_response.headers.keys()}")
            print("🔹 Discord Rate Limit Info:")
            print(f"🔹 Limit: {ratelimit_limit}")
            print(f"🔹 Remaining: {ratelimit_remaining}")
            print(f"🔹 Reset Timestamp: {ratelimit_reset}")
            print(f"🔹 Reset After: {ratelimit_reset_after} seconds")
            print(f"🔹 Global Limit: {ratelimit_global}")
            print(f"✅ Message sent successfully to {user_id}!")
        else:
            print(f"❌ Failed to send message! Status: {message_response.status_code}, Response: {message_response.text}")


async def check_global_rate_limit():
    url = "https://discord.com/api/v10/users/@me"
    headers = {
        "Authorization": f"Bot {TOKEN}",
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
    # Check if we hit the global rate limit
    if response.status_code == 429:  # 429 = Too Many Requests
        data = response.json()
        retry_after = data.get("retry_after", "Unknown")
        global_limit = data.get("global", False)

        print("🚨 You hit the global rate limit!")
        print(f"⏳ Cooldown time: {retry_after} seconds")
        print(f"🌍 Global limit active: {global_limit}")
    else:
        #print("✅ No global rate limit reached!")
        pass


async def edit_message(channel_id, message_id, new_content):
    """Edits an existing message in a channel."""
    url = f"https://discord.com/api/v10/channels/{channel_id}/messages/{message_id}"
    headers = {
        "Authorization": f"Bot {TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {"content": new_content}

    async with httpx.AsyncClient() as client:
        response = await client.patch(url, headers=headers, json=payload)

        if response.status_code == 200:
            print(f"✅ Successfully edited message {message_id} in channel {channel_id}!")
        else:
            print(f"❌ Failed to edit message {message_id}! Status: {response.status_code}, Response: {response.text}")

        # Extract Rate Limit Headers
        ratelimit_limit = response.headers.get("X-RateLimit-Limit")
        ratelimit_remaining = response.headers.get("X-RateLimit-Remaining")
        ratelimit_reset = response.headers.get("X-RateLimit-Reset")
        ratelimit_reset_after = response.headers.get("X-RateLimit-Reset-After")
        ratelimit_global = response.headers.get("X-RateLimit-Global")

        print("🔹 Discord Rate Limit Info:")
        print(f"🔹 Limit: {ratelimit_limit}")
        print(f"🔹 Remaining: {ratelimit_remaining}")
        print(f"🔹 Reset Timestamp: {ratelimit_reset}")
        print(f"🔹 Reset After: {ratelimit_reset_after} seconds")
        print(f"🔹 Global Limit: {ratelimit_global}")

async def fetch_user(user_id):
    """Fetches a user from Discord API and prints rate limit headers."""
    url = f"https://discord.com/api/v10/users/{user_id}"
    headers = {
        "Authorization": f"Bot {TOKEN}",
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)

        if response.status_code == 200:
            user_data = response.json()
            print(f"✅ Successfully fetched user: {user_data['username']}#{user_data['discriminator']} ({user_id})")
        else:
            print(f"❌ Failed to fetch user {user_id}! Status: {response.status_code}, Response: {response.text}")

        # Extract Rate Limit Headers
        ratelimit_limit = response.headers.get("X-RateLimit-Limit")
        ratelimit_remaining = response.headers.get("X-RateLimit-Remaining")
        ratelimit_reset = response.headers.get("X-RateLimit-Reset")
        ratelimit_reset_after = response.headers.get("X-RateLimit-Reset-After")
        ratelimit_global = response.headers.get("X-RateLimit-Global")

        print("🔹 Discord Rate Limit Info:")
        print(f"🔹 Limit: {ratelimit_limit}")
        print(f"🔹 Remaining: {ratelimit_remaining}")
        print(f"🔹 Reset Timestamp: {ratelimit_reset}")
        print(f"🔹 Reset After: {ratelimit_reset_after} seconds")
        print(f"🔹 Global Limit: {ratelimit_global}")

GUILD_ID = "375691427444817932"

async def get_guild_members():
    """Fetches 100 random members from the guild."""
    url = f"https://discord.com/api/v10/guilds/{GUILD_ID}/members?limit=100"
    headers = {"Authorization": f"Bot {TOKEN}"}

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)

        if response.status_code == 200:
            return [member["user"]["id"] for member in response.json()]
        else:
            print(f"❌ Failed to fetch guild members! Status: {response.status_code}")
            return []

async def create_dm(user_id):
    """Creates a DM with a user and handles rate limits."""
    url = "https://discord.com/api/v10/users/@me/channels"
    headers = {
        "Authorization": f"Bot {TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {"recipient_id": user_id}

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload)

        if response.status_code == 200:
            dm_data = response.json()
            print(f"✅ DM created with {user_id}. Channel ID: {dm_data['id']}")
        elif response.status_code == 429:
            retry_after = float(response.json().get("retry_after", 1))
            print(f"❌ Rate limited! Sleeping for {retry_after:.2f} seconds...")
            await asyncio.sleep(retry_after + 0.1)
            return await create_dm(user_id)
        else:
            print(f"❌ Failed to create DM with {user_id}. Status: {response.status_code}")

        # Extract Rate Limit Headers
        ratelimit_limit = response.headers.get("X-RateLimit-Limit")
        ratelimit_remaining = response.headers.get("X-RateLimit-Remaining")
        ratelimit_reset_after = response.headers.get("X-RateLimit-Reset-After")

        print("🔹 Discord Rate Limit Info:")
        print(f"🔹 Limit: {ratelimit_limit}")
        print(f"🔹 Remaining: {ratelimit_remaining}")
        print(f"🔹 Reset After: {ratelimit_reset_after} seconds\n")



class RateLimitHandlerhttpx:
    def __init__(self):
        self.global_limited = False
        self.route_limits = {}

    async def check_rate_limit(self, route: str):
        """Check the rate limit for a given route and wait if necessary."""
        if self.global_limited:
            print("🌐 Global rate limit reached. Waiting...")
            await asyncio.sleep(self.global_limited)

        if route in self.route_limits:
            reset_time = self.route_limits[route]["reset"]
            remaining = self.route_limits[route]["remaining"]

            if remaining <= 0:
                sleep_time = max(0, reset_time - asyncio.get_event_loop().time())
                print(f"⏳ Route rate limit reached for {route}. Waiting {sleep_time:.2f}s...")
                await asyncio.sleep(sleep_time)

    async def update_rate_limit(self, headers, route: str):
        """Update rate limit info based on response headers."""
        global_remaining = headers.get("X-RateLimit-Global")
        if global_remaining:
            self.global_limited = float(headers.get("X-RateLimit-Reset-After", 0))
        else:
            limit = int(headers.get("X-RateLimit-Limit", 0))
            remaining = int(headers.get("X-RateLimit-Remaining", 0))
            reset_after = float(headers.get("X-RateLimit-Reset-After", 0))

            self.route_limits[route] = {
                "limit": limit,
                "remaining": remaining,
                "reset": asyncio.get_event_loop().time() + reset_after
            }

    async def request(self, method, url, **kwargs):
        """Send a request while respecting rate limits."""
        route = url.split("/api/v10/")[-1]
        await self.check_rate_limit(route)

        async with httpx.AsyncClient() as client:
            response = await client.request(method, url, headers={"Authorization": f"Bot {TOKEN}"}, **kwargs)
            print(f"🔹 Discord Rate Limit Info: {response.headers}")

            await self.update_rate_limit(response.headers, route)

            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After", 1)
                print(f"🚦 Rate limited! Retrying after {retry_after}s...")
                await asyncio.sleep(float(retry_after))
                return await self.request(method, url, **kwargs)

            return response


# MONKEY PATCHING DISCORD.PY TO PREVENT RATE LIMITING
class RateLimitHandlerDiscordpy:
    def __init__(self):
        self.global_limited = False
        self.route_limits = {}

    async def check_rate_limit(self, route: Route):
        """Check and enforce rate limits before making a request."""
        if self.global_limited:
            print("🌐 Global rate limit reached. Waiting...")
            await asyncio.sleep(self.global_limited)

        route_key = route.path  # Use route.path as a unique key

        if route_key in self.route_limits:
            reset_time = self.route_limits[route_key]["reset"]
            remaining = self.route_limits[route_key]["remaining"]

            if remaining <= 0:
                sleep_time = max(0, reset_time - asyncio.get_event_loop().time())
                print(f"⏳ Route rate limit reached for {route_key}. Waiting {sleep_time:.2f}s...")
                await asyncio.sleep(sleep_time)

    async def update_rate_limit(self, headers, route: Route):
        """Update rate limit info based on response headers."""
        route_key = route.path  # Unique identifier for the route

        if "X-RateLimit-Global" in headers:
            self.global_limited = float(headers.get("X-RateLimit-Reset-After", 0))
        else:
            limit = int(headers.get("X-RateLimit-Limit", 0))
            remaining = int(headers.get("X-RateLimit-Remaining", 0))
            reset_after = float(headers.get("X-RateLimit-Reset-After", 0))

            self.route_limits[route_key] = {
                "limit": limit,
                "remaining": remaining,
                "reset": asyncio.get_event_loop().time() + reset_after
            }

    async def request_with_rate_limit(self, original_request, route: Route, **kwargs):
        """Rate-limited version of Discord API request."""
        await self.check_rate_limit(route)

        response = await original_request(route, **kwargs)  # Original request call

        # We need to extract headers separately
        headers = getattr(response, 'headers', None)  # Ensure headers exist


        if headers is not None:  # Only update rate limit if headers are present
            await self.update_rate_limit(headers, route)  

            if response.status == 429:  # Rate limited
                retry_after = float(response.headers.get("Retry-After", 1))
                print(f"🚦 Rate limited! Retrying after {retry_after}s...")
                await asyncio.sleep(retry_after)
                return await self.request_with_rate_limit(original_request, route, **kwargs)

        return response
# --- END OF MONKEY PATCHING DISCORD.PY---

async def patch_discord_http(bot):
    """Monkey patches discord.py's HTTP client to add rate limit handling."""
    rate_limiter = RateLimitHandlerDiscordpy()
    original_request = bot.http.request  # Save original method

    async def patched_request(route: Route, **kwargs):
        """Intercept Discord.py's HTTP request and apply rate limiting."""
        return await rate_limiter.request_with_rate_limit(original_request, route, **kwargs)

    bot.http.request = patched_request  # Apply the patch


# RATE LIMIT QUEUE SYSTEM

class RateLimitQueue:
    """
    This class implements a rate limit queue for handling rate limits. You can use "await rate_limiter.add_request(func, args, kwargs)"
    in order to run it in the queue. If you only want to run it once (e.g. in on_ready()), you can also use "await func(*args, **kwargs)" thats no problem.
    """
    def __init__(self, max_requests_per_second):
        self.queue = asyncio.Queue()
        self.max_requests_per_second = max_requests_per_second
        self.requests_this_second = 0
        self.current_second = int(time.time())
        self.lock = asyncio.Lock()
        print(f"Queue items: {self.queue.qsize()}")

    async def add_request(self, func, args, kwargs):
        future = asyncio.get_event_loop().create_future()
        await self.queue.put((func, args, kwargs, future))
        return await future  # Wartet auf das Ergebnis


    async def worker(self, process_request):
        while True:
            request_method, args, kwargs, future = await self.queue.get()  # Future mit aus der Queue holen
            async with self.lock:
                now = int(time.time())
                if now != self.current_second:
                    self.current_second = now
                    self.requests_this_second = 0

                if self.requests_this_second >= self.max_requests_per_second:
                    await asyncio.sleep(1 - (time.time() % 1))
                    self.current_second = int(time.time())
                    self.requests_this_second = 0

                self.requests_this_second += 1

            # Erstelle Task und setze das Future-Ergebnis
            asyncio.create_task(process_request(request_method, args, kwargs, self.current_second, self.requests_this_second, future))
            await asyncio.sleep(1 / self.max_requests_per_second) 
            self.queue.task_done()
            print(f"Queue items: {self.queue.qsize()}")

async def request_handler(request_method, args, kwargs, current_sec, requests_this_second, future):
    try:
        if request_method == print:
            result = f"Processing request: {args}, {round(time.time()%10,2)}, {round(current_sec%10,3)}, {requests_this_second}"
            print(result)
        else:
            result = f"🚦 Processing request: {request_method.__name__}, {kwargs['content'] if 'content' in kwargs else ''}, {round(time.time()%10,2)}, {round(current_sec%10,3)}, {requests_this_second}"
            print(result)
            response = await request_method(*args, **kwargs)
            future.set_result(response)  # Setze das Future-Ergebnis
            
    except Exception as e:
        future.set_exception(e)

# --- END OF RATE LIMIT QUEUE SYSTEM ---

        
async def main():

    #rate_limiter = RateLimitHandlerhttpx()
    #url = f"https://discord.com/api/v10/channels/{TESTING_CHANNEL_ID}/messages"
    #payload = {"content": "Test message!"}
    #response = await rate_limiter.request("POST", url, json=payload)
    #print(response.status_code)
    #print(response.text)

    
    print(int(time.time()))
    t = time.time()
    print(t, 1 - t%1)
    print()
    rate_limiter = RateLimitQueue(50)
    #asyncio.create_task(rate_limiter._reset_rate_limit())
    asyncio.create_task(rate_limiter.worker(request_handler))

    tasks = [rate_limiter.add_request(print, str(i)) for i in range(30000)]
    await asyncio.gather(*tasks)
    await asyncio.sleep(4)
    
    tasks = [rate_limiter.add_request(print,str(i)) for i in range(30000)]
    await asyncio.gather(*tasks)
    await asyncio.sleep(4)
    
    tasks = [rate_limiter.add_request(print,str(i)) for i in range(30000)]
    await asyncio.gather(*tasks)
    await asyncio.sleep(4)
    
    
    while True:
        await asyncio.sleep(1)# dont terminate: give the worker some time to process the requests


    
    """Main function to execute both requests."""
    #time = 6
    #for i in range(time):
    #    await send_message_to_channel()  # Send a message
    #await asyncio.sleep(time)
    #print("🔹 Slept for 2 seconds...XXXXXXXXXXXXXXXX")
    #for i in range(time):
    #    await send_message_to_channel()  # Send a message
    #await asyncio.sleep(time)
    #print("🔹 Slept for 2 seconds...XXXXXXXXXXXXXXXXXX")
    #for i in range(time):
    #    await send_message_to_channel()  # Send a message
    #await asyncio.sleep(time)

    
    #await create_private_thread()

    #message_id=1339395631579402251
    #for i in range(10):  # Try editing 10 times to check rate limits
    #    new_content = f"Edited message test #{i+1}"
    #    await edit_message(TESTING_CHANNEL_ID, message_id, new_content)
        #await asyncio.sleep(1)  # Slight delay to observe rate limits

    if 0:
        #tasks = [send_dm(USER_ID, f"Hello! This is test DM #{i+1} 🚀") for i in range(5)]
        #await asyncio.gather(*tasks)  # Run all requests at once
        userlist = ["508609806811004938","462734130560499723","772908239062564885","565931754515333141","607371005081550859","485415851030347776",
                   "847433819312095292","780888488026832926","1037729819074510919","455076692365410340","277069670828343298","471644609374584844","438345806798651392"]
        #for _ in range(10):
        #    for i in range(13):
        #        await create_dm(userlist[i])

        tasks = [create_dm(userlist[i]) for i in range(13) for _ in range(5)]
        await asyncio.gather(*tasks)  # Run all requests at once

        #for _ in range(28):
        #    await fetch_user(userlist[0])
        #
        #for user_id in userlist:
        #    await fetch_user(user_id)
        
        #tasks = [send_message_to_channel() for i in range(60)]
        #await asyncio.gather(*tasks)  # Run all requests at once

        #tasks = [check_global_rate_limit() for i in range(51)]
        #await asyncio.gather(*tasks)  # Run all requests at once

        #user_ids = await get_guild_members()
        #if not user_ids:
        #    print("❌ No users found. Exiting test.")
        #    return
#
#        #print(f"🔹 Testing DM creation for {len(user_ids)} users...")
#
#        #for user_id in user_ids:
#        #    await create_dm(user_id)
        #    #await asyncio.sleep(0.5)  # Short delay to avoid instant rate limiting

    #await check_global_rate_limit()

# Run the functions
if __name__ == "__main__":
    asyncio.run(main())