import threading, random, requests, time, datetime, sys

# USER_COUNT = 100
SIM_TIME = 6.7 * 60
# PORTS = [3006, 3007, 3008]
PORTS = [3006, 3007, 3008, 3009]
GPU_WORKERS = None
threads_active = 0


def create_random_request(_json):

    server = random.choice(PORTS)
    np = PORTS[:]
    np.remove(server)

    client_num = random.randrange(GPU_WORKERS)
    route = random.choice(['execute_task', 'make_federated_request'])

    url = f"http://localhost:{server}/{route}/{client_num}"

    if route == "make_federated_request":
        secondary = random.choice(np)
        url = f"http://localhost:{server}/{route}/{secondary}/{client_num}"
        # return #for now


    response = requests.post(url, json=_json)
    return response.json()




def user_thread(user_count):
    _json = {"user_id" : f"{random.randrange(0,9999)}__{random.randrange(0,9999)}",
             "last_update_time": datetime.datetime.utcnow().timestamp(),
             "trust_score": random.randrange(1000), "user_count": user_count, "task_count": 0}
    while True:
        time.sleep(random.randrange(10, 16))
        resp = create_random_request(_json)
        # print(resp)
        # _json['trust_score'] = resp['data']['trust_score']
        _json['task_count'] += 1



if __name__ == "__main__":
    USER_COUNT = int(sys.argv[1]) 
    GPU_WORKERS = int(sys.argv[2])

    for i in range(USER_COUNT*4):
        threads_active += 1
        thread = threading.Thread(target=user_thread, args=(USER_COUNT,))
        thread.start()
        #spawn random worker thread


    time.sleep(SIM_TIME)
    sys.exit()